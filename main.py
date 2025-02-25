from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask, request
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import io
import re
from dotenv import load_dotenv
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# Cấu hình bot Telegram
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Flask để chạy Webhook
flask_app = Flask(__name__)

# Bộ nhớ hội thoại và dữ liệu đồ thị
user_conversations = {}
user_plot_data = {}  # Lưu trữ dữ liệu đồ thị của từng người dùng


def generate_ai_response(prompt, max_retries=3):
    """Tạo phản hồi từ Gemini AI với retry"""
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Lỗi lần {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return "Xin lỗi, tôi đang gặp vấn đề kỹ thuật. Vui lòng thử lại sau."


@flask_app.route("/")
def home():
    return "Bot is running!"


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Xử lý Webhook từ Telegram"""
    update_json = request.get_json(force=True)
    print("📩 Nhận tin nhắn từ Telegram:", update_json)
    update = Update.de_json(update_json, app)
    app.update_queue.put(update)
    return "ok"


async def start_command(update: Update, context: CallbackContext):
    """Lệnh /start"""
    user_id = update.message.chat_id
    user_conversations[user_id] = []
    user_plot_data[user_id] = []  # Khởi tạo bộ nhớ đồ thị
    await update.message.reply_text(
        "Xin chào! Tôi là chatbot hỗ trợ với Gemini AI.")


def clean_generated_code(code: str):
    """Làm sạch code Python từ Gemini"""
    patterns = [
        r'```python\s*',  # Xóa markdown
        r'```\s*',
        r'plt\.show\(\)',  # Xóa lệnh hiển thị
        r'#.*\n',  # Xóa comment
        r'print\(.*\)\n'  # Xóa lệnh print
    ]
    for pattern in patterns:
        code = re.sub(pattern, '', code)
    return code.strip()


async def generate_plot_code(description, last_data=None):
    """Tạo code Python vẽ đồ thị"""
    prompt = f"""
    - Trả về nguyên code Python, không giải thích
    - Dữ liệu bịa ra để vẽ đồ thị
    - Mỗi lệnh matplotlib PHẢI xuống dòng riêng
    - TUYỆT ĐỐI KHÔNG viết nhiều lệnh plt trên cùng 1 dòng
    - Chỉ viết mỗi lệnh một dòng duy nhất
    - Nếu có dữ liệu cũ, sử dụng lại: {last_data}
    Yêu cầu: {description}
    Code phải bao gồm:
    - import matplotlib.pyplot as plt
    - import numpy as np
    - Vẽ đồ thị với plt.plot(), plt.scatter() hoặc plt.bar()
    - plt.title() với tiêu đề phù hợp
    - plt.savefig() để lưu hình ảnh
    - Code phải hợp lệ và có thể chạy trực tiếp mà không bị lỗi
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    raw_code = response.text if response else ""
    cleaned_code = clean_generated_code(raw_code)

    return cleaned_code or """
    import matplotlib.pyplot as plt
    import numpy as np
    plt.plot([1,2,3],[4,5,6])
    plt.title('Biểu đồ mặc định')
    plt.savefig('plot.png')
    """


async def generate_plot(update: Update, context: CallbackContext,
                        description: str):
    user_id = update.message.chat_id

    try:
        if not description.strip():
            await update.message.reply_text("⚠️ Vui lòng nhập mô tả chi tiết")
            return

        # Lấy dữ liệu cũ nếu có yêu cầu sửa đồ thị
        last_data = None
        if "sửa" in description and user_id in user_plot_data and user_plot_data[
                user_id]:
            last_data = user_plot_data[user_id][-1].get("data", {})

        # Tạo code vẽ đồ thị
        plot_code = await generate_plot_code(description, last_data)

        # Thực thi code
        plt.clf()
        exec_globals = {"plt": plt, "np": np, "io": io}
        exec_locals = {}
        try:
            exec(plot_code, exec_globals, exec_locals)
        except Exception as e:
            error_msg = f"🚨 LỖI CODE:\n{plot_code}\nLỖI: {str(e)}"
            print(error_msg)
            await update.message.reply_text(
                "Hệ thống gặp lỗi xử lý code vẽ đồ thị 😢")
            return

        # Lưu đồ thị vào buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)

        # Gửi ảnh qua Telegram
        await update.message.reply_photo(photo=buffer)

        # Lưu dữ liệu đồ thị
        if user_id not in user_plot_data:
            user_plot_data[user_id] = []
        user_plot_data[user_id].append({
            "description": description,
            "code": plot_code,
            "data": exec_locals  # Lưu các biến data
        })

        # Đóng figure
        plt.close()

    except Exception as e:
        print(f"❌ Lỗi khi tạo đồ thị: {e}")
        await update.message.reply_text(
            "Xin lỗi, đã xảy ra lỗi khi tạo đồ thị. Vui lòng thử lại.")


async def handle_message(update: Update, context: CallbackContext):
    """Xử lý tin nhắn"""
    user_id = update.message.chat_id
    message = update.message.text
    print(f"📩 Nhận tin nhắn từ người dùng ({user_id}): {message}")

    # Khởi tạo bộ nhớ nếu chưa có
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    if user_id not in user_plot_data:
        user_plot_data[user_id] = []

    # Xử lý yêu cầu vẽ đồ thị
    if "vẽ" in message or "đồ thị" in message:
        user_conversations[user_id].append(f"Người dùng: {message}")
        await generate_plot(update, context,
                            message.replace("/plot", "").strip())
        return

    # Xử lý tin nhắn thông thường
    user_conversations[user_id].append(f"Người dùng: {message}")
    if len(user_conversations[user_id]) > 3:
        user_conversations[user_id].pop(0)

    conversation_history = "\n".join(user_conversations[user_id])
    prompt = f"""
    Vai trò của bạn là một nhà phân tích kinh tế chuyên nghiệp.
    - không trả lời các câu hỏi không liên quan đến kinh tế.
    - Tuyệt đối không chào người dùng trong câu nói ngoại trừ người dùng chào bạn.
    - khi người dùng chào thì chỉ giới thiệu ngắn gọn không quá 4 câu.
    - Chỉ cần trả lời trọng tâm vào câu hỏi.
    - Trả lời lịch sự.
    - Trình bày đơn giản, không in đậm các từ.
    - Đánh số các ý chính mà bạn muốn trả lời.
    - Không trả lời quá dài dòng, không trả lời quá 200 từ.
    - viết câu tóm tắt trước khi phân tích các ý chính
    Đây là cuộc hội thoại trước đó:
    {conversation_history}
    Người dùng: {message}
    Hãy trả lời một cách chi tiết, logic và có căn cứ kinh tế.
    """

    response = generate_ai_response(prompt)
    response = response.replace('*', '')
    print(f"🤖 Phản hồi từ Gemini: {response}")

    user_conversations[user_id].append(f"Bot: {response}")

    try:
        await update.message.reply_text(response)
        print("✅ Gửi tin nhắn thành công!")
    except Exception as e:
        print(f"❌ Lỗi khi gửi tin nhắn: {e}")


def run_flask():
    """Chạy Flask để xử lý Webhook"""
    flask_app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()