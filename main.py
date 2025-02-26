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
from generate_plot import GeneratePlot
from gemini_api import Gemini_api

# Add this line to load variables from .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
flask_app = Flask(__name__)
user_conversations = {}
user_plot_data = {}  

# Initialize Gemini API
gemini_bot = Gemini_api()

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
        await GeneratePlot.generate_plot(update, context,
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
    app.add_handler(CommandHandler("start", gemini_bot.start_command))
    app.add_handler(CommandHandler("report", gemini_bot.generate_report_command))  # Add this line
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, gemini_bot.handle_message))
    app.run_polling()