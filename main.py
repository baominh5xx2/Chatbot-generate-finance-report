from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
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
from latex_generator import LatexGenerator

# Load environment variables
load_dotenv()

# Set up API keys and tokens
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Telegram app
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
flask_app = Flask(__name__)

# Initialize conversation storage
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

async def report_help_command(update: Update, context: CallbackContext):
    """Show report help"""
    help_text = (
        "🔍 *Các lệnh báo cáo:*\n\n"
        "• `/report` - Báo cáo kinh tế tổng quan\n"
        "• `/report_economic` - Báo cáo phân tích kinh tế\n"
        "• `/report_market` - Báo cáo phân tích thị trường\n"
        "• `/report_forecast` - Báo cáo dự báo kinh tế\n"
        "• `/report_custom` - Báo cáo kinh tế tùy chỉnh\n\n"
        "Hoặc bạn có thể nhập: 'báo cáo kinh tế', 'báo cáo thị trường', 'báo cáo dự báo'"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def baocao_help_command(update: Update, context: CallbackContext):
    """Show report help in Vietnamese"""
    help_text = (
        "📊 *Hướng dẫn tạo báo cáo:*\n\n"
        "Bạn có thể yêu cầu các loại báo cáo sau:\n\n"
        "• 'báo cáo kinh tế' - Báo cáo tổng quan kinh tế\n"
        "• 'báo cáo thị trường' - Phân tích thị trường chứng khoán\n"
        "• 'báo cáo dự báo' - Dự báo xu hướng kinh tế\n"
        "• 'báo cáo tùy chỉnh' - Báo cáo theo yêu cầu\n\n"
        "Cách sử dụng: Chỉ cần nhắn tin với nội dung 'báo cáo kinh tế', 'tạo báo cáo thị trường', v.v."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def latex_command(update: Update, context: CallbackContext):
    """Handle /latex command to generate LaTeX"""
    if not context.args:
        await update.message.reply_text(
            "Vui lòng cung cấp mô tả cho mã LaTeX. Ví dụ: /latex phương trình bậc hai"
        )
        return
    
    prompt = " ".join(context.args)
    await gemini_bot.latex_generator.generate_latex(update, context, prompt)

async def latex_list_command(update: Update, context: CallbackContext):
    """List all LaTeX files created by the user"""
    await gemini_bot.latex_generator.list_latex_files(update, context)

async def latex_get_command(update: Update, context: CallbackContext):
    """Get a specific LaTeX file"""
    await gemini_bot.latex_generator.get_latex_file(update, context)

async def latex_help_command(update: Update, context: CallbackContext):
    """Show LaTeX help"""
    help_text = (
        "📝 *Hướng dẫn tạo tài liệu PDF:*\n\n"
        "Bạn có thể tạo các tài liệu PDF sử dụng LaTeX với các cách sau:\n\n"
        "• `/latex [mô tả]` - Tạo tài liệu từ mô tả của bạn\n"
        "• Nhắn tin với từ khóa 'tạo pdf' hoặc 'pdf' + mô tả\n\n"
        "Ví dụ: \n"
        "- `/latex báo cáo kinh tế với 2 bảng và 1 biểu đồ`\n"
        "- `tạo pdf phương trình kinh tế vĩ mô`\n\n"
        "Các lệnh khác:\n"
        "• `/latex_list` - Xem danh sách tài liệu đã tạo\n"
        "• `/latex_get [số]` - Tải lại tài liệu đã tạo\n"
        "• `/latex_help` - Hiển thị hướng dẫn này"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def company_report_command(update: Update, context: CallbackContext):
    """Handle /company_report command to generate company analysis PDF"""
    if not context.args:
        await update.message.reply_text(
            "Vui lòng cung cấp tên công ty để phân tích. Ví dụ: /company_report Apple Inc"
        )
        return
    
    company_name = " ".join(context.args)
    prompt = f"báo cáo phân tích công ty {company_name} chi tiết, bao gồm tổng quan về doanh nghiệp, phân tích tài chính, SWOT, và dự báo"
    await gemini_bot.latex_generator.generate_latex(update, context, prompt)

async def clear_history_command(update: Update, context: CallbackContext):
    """Clear conversation history"""
    await gemini_bot.clear_history(update, context)

def run_flask():
    """Chạy Flask để xử lý Webhook"""
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Initialize Gemini bot
    gemini_bot = Gemini_api()
    
    # Initialize LaTeX generator and attach it to the Gemini bot
    latex_generator = LatexGenerator(gemini_bot)
    gemini_bot.latex_generator = latex_generator

    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gemini_bot.handle_message))
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("latex", latex_command))
    app.add_handler(CommandHandler("latex_list", latex_list_command))
    app.add_handler(CommandHandler("latex_get", latex_get_command))
    app.add_handler(CommandHandler("latex_help", latex_help_command))
    app.add_handler(CommandHandler("company_report", company_report_command))
    app.add_handler(CommandHandler("clear_history", clear_history_command))
    
    # Add document handler to handle CSV uploads
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), gemini_bot.handle_message))
    
    # Start the bot
    app.run_polling()
