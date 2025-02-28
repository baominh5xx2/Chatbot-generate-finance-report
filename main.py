from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from flask import Flask, request
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import io
import threading

import re
from dotenv import load_dotenv
import os
from generate_plot import GeneratePlot
from gemini_api import Gemini_api
from latex_generator import LatexGenerator
from vnstockk import VNStockService

# Load environment variables
load_dotenv()

# Set up API keys and tokens
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # Default if not set
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Telegram app
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
flask_app = Flask(__name__)

# Initialize VNStock service
vnstock_service = VNStockService()

# Initialize Gemini bot
gemini_bot = Gemini_api()

async def start_command(update: Update, context: CallbackContext):
    """Lệnh /start"""
    user_id = str(update.message.chat_id)
    
    welcome_message = (
        "👋 Xin chào! Tôi là chatbot trợ lý kinh tế tài chính.\n\n"
        "Tôi có thể giúp bạn:\n"
        "• Trả lời các câu hỏi về kinh tế, tài chính\n"
        "• Tra cứu thông tin chứng khoán với lệnh /search [mã CP]\n"
        "• Tạo biểu đồ từ dữ liệu của bạn\n"
        "• Tạo tài liệu PDF với lệnh /latex\n\n"
        "Hãy đặt câu hỏi hoặc sử dụng các lệnh để bắt đầu!"
    )
    
    await update.message.reply_text(welcome_message)
    await gemini_bot.start_command(update, context)
    
async def help_command(update: Update, context: CallbackContext):
    """Hiển thị trợ giúp"""
    help_text = (
        "🤖 *Hướng dẫn sử dụng bot*\n\n"
        "*Các lệnh cơ bản:*\n"
        "• /start - Khởi động bot\n"
        "• /help - Hiển thị trợ giúp này\n"
        "• /clear_history - Xóa lịch sử trò chuyện\n\n"
        
        "*Tra cứu chứng khoán:*\n"
        "• /search [mã CP] - Tra cứu thông tin cổ phiếu\n"
        "• /search_get [số] - Xem chỉ số tài chính cụ thể\n"
        "• /search_chart - Xem biểu đồ giá cổ phiếu\n"
        "• /search_help - Hướng dẫn sử dụng tìm kiếm\n\n"
        
        "*Tạo tài liệu PDF:*\n"
        "• /latex [mô tả] - Tạo tài liệu từ mô tả\n"
        "• /latex_list - Xem danh sách tài liệu\n"
        "• /latex_get [số] - Tải lại tài liệu\n"
        "• /latex_help - Hướng dẫn sử dụng LaTeX\n\n"
        
        "*Tạo biểu đồ:*\n"
        "Nhắn tin \"vẽ biểu đồ [mô tả]\" để tạo biểu đồ\n"
        "Ví dụ: vẽ biểu đồ GDP Việt Nam từ 2010-2023"
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

async def clear_history_command(update: Update, context: CallbackContext):
    """Clear conversation history"""
    await gemini_bot.clear_history(update, context)

async def search_command(update: Update, context: CallbackContext):
    """Handle /search command to start VNStock service"""
    await vnstock_service.search_stock(update, context)  # Changed from start_vnstock to search_stock

async def search_get_command(update: Update, context: CallbackContext):
    """Handle /search_get command to get financial indicators"""
    await vnstock_service.get_financial_data(update, context)
    
async def search_chart_command(update: Update, context: CallbackContext):
    """Handle /search_chart command to get stock charts"""
    await vnstock_service.get_stock_chart(update, context)

async def search_help_command(update: Update, context: CallbackContext):
    """Handle /search_help command to show search help"""
    await vnstock_service.vnstock_help_command(update, context)

async def search_info_command(update: Update, context: CallbackContext):
    """Handle command to get company information"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "Vui lòng sử dụng lệnh: /search_info [mã cổ phiếu]\n"
            "Ví dụ: /search_info VNM"
        )
        return
        
    symbol = context.args[0].upper()
    await update.message.reply_text(f"Đang tải thông tin về công ty {symbol}...")
    
    # Call VNStockService to get company info
    try:
        # First set the current symbol
        vnstock_service.current_symbol = symbol
        
        # Then get company information using existing method
        time_period = datetime.datetime.now().strftime("%Y%m%d")
        await vnstock_service.get_company_information(update, context)
    except Exception as e:
        await update.message.reply_text(f"Lỗi khi lấy thông tin công ty: {str(e)}")

def register_commands():
    """Register all command handlers"""
    # Add message handler for regular text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gemini_bot.handle_message))
    
    # Add command handlers for basic bot functions
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear_history", clear_history_command))
    
    # Add LaTeX command handlers
    app.add_handler(CommandHandler("latex", latex_command))
    app.add_handler(CommandHandler("latex_list", latex_list_command))
    app.add_handler(CommandHandler("latex_get", latex_get_command))
    app.add_handler(CommandHandler("latex_help", latex_help_command))
    
    # Add search command handlers - updated from vnstock
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("search_get", search_get_command))
    app.add_handler(CommandHandler("search_chart", search_chart_command))
    app.add_handler(CommandHandler("search_help", search_help_command))
    app.add_handler(CommandHandler("search_info", search_info_command))
    app.add_handler(CallbackQueryHandler(vnstock_service.handle_callback, pattern="^vnstock_"))
    
    # Add new handler for the shortened format "vn_ind_" callbacks
    app.add_handler(CallbackQueryHandler(vnstock_service.handle_callback, pattern="^vn_ind_"))
    
    # Add callback handler for plot-related buttons
    app.add_handler(CallbackQueryHandler(gemini_bot.handle_plot_callback, pattern="^plot_"))
    # Make sure you have this handler properly registered
    app.add_handler(CallbackQueryHandler(vnstock_service.handle_callback, pattern="^company_section_"))
    print("✅ All commands registered!")

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

def run_flask():
    """Chạy Flask để xử lý Webhook"""
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    print("🚀 Khởi động bot...")
    
    # Initialize Gemini bot and LaTeX generator
    gemini_bot = Gemini_api()
    latex_generator = LatexGenerator(gemini_bot)
    gemini_bot.latex_generator = latex_generator
    
    # Register all command handlers
    register_commands()
    
    # Start the Flask server in a separate thread if webhook mode is used
    if os.getenv("USE_WEBHOOK", "False").lower() == "true":
        threading.Thread(target=run_flask, daemon=True).start()
        print("🌐 Webhook server started!")
    
    # Start the bot
    print("✅ Bot started successfully! Press Ctrl+C to stop.")
    app.run_polling()
