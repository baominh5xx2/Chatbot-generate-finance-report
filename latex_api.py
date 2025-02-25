import os
import requests
import pandas as pd
from jinja2 import Template
from telegram import Update, Document
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# Token Telegram Bot (thay bằng token thật của bạn)
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# URL API của Overleaf
OVERLEAF_UPLOAD_URL = "https://www.overleaf.com/docs"

# Mẫu LaTeX tự động sinh từ dữ liệu CSV
LATEX_TEMPLATE = r"""
\documentclass{article}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{a4paper, margin=1in}
\usepackage{longtable}

\begin{document}

\title{Báo Cáo Tự Động từ CSV}
\author{Chatbot Telegram}
\date{\today}
\maketitle

\section{Giới thiệu}
Dưới đây là báo cáo sinh tự động từ dữ liệu CSV.

\section{Dữ liệu từ CSV}
\begin{longtable}{|c|c|c|}
\hline
\textbf{STT} & \textbf{Tên Sản Phẩm} & \textbf{Doanh Thu (VNĐ)} \\
\hline
{% for row in data %}
{{ row.index }} & {{ row.name }} & {{ row.revenue }} \\
\hline
{% endfor %}
\end{longtable}

\end{document}
"""

# Hàm tải mã LaTeX lên Overleaf
def upload_to_overleaf(latex_code):
    """Tải LaTeX lên Overleaf và lấy link mở project"""
    # Lưu mã LaTeX vào file tạm
    tex_file = "report.tex"
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(latex_code)

    # Tạo link để mở trực tiếp trên Overleaf
    overleaf_link = f"https://www.overleaf.com/docs?snip_uri={os.path.abspath(tex_file)}"

    return overleaf_link

# Hàm xử lý file CSV từ Telegram
def handle_csv(update: Update, context: CallbackContext) -> None:
    file = update.message.document  # Lấy file từ người dùng
    file_path = f"received_{file.file_name}"
    
    # Tải file CSV về server
    new_file = context.bot.get_file(file.file_id)
    new_file.download(file_path)

    # Đọc dữ liệu từ CSV
    df = pd.read_csv(file_path)
    df = df.rename(columns={df.columns[0]: "index", df.columns[1]: "name", df.columns[2]: "revenue"})

    # Tạo nội dung LaTeX từ mẫu
    latex_code = Template(LATEX_TEMPLATE).render(data=df.to_dict(orient="records"))

    # Gửi mã LaTeX lên Overleaf
    overleaf_link = upload_to_overleaf(latex_code)

    # Gửi link Overleaf cho người dùng
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=f"Báo cáo đã được tạo! Mở trên Overleaf: {overleaf_link}")

    # Xóa file tạm
    os.remove(file_path)

# Hàm khởi động bot
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Lắng nghe file CSV từ người dùng
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/csv"), handle_csv))

    # Chạy bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
