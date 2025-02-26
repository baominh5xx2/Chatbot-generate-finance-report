import matplotlib.pyplot as plt
import numpy as np
import re
import io
from telegram import Update
from telegram.ext import CallbackContext

class GeneratePlot:
    def __init__(self, x, y, gemini_api=None):
        self.x = x
        self.y = y
        self.user_plot_data = {}
        self.gemini_api = gemini_api

    def clean_generated_code(self, code: str):
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

    async def generate_plot_code(self, description, last_data=None):
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

        try:
            code = self.gemini_api.generate_ai_response(prompt) if self.gemini_api else None
            cleaned_code = self.clean_generated_code(code) if code else None
            return cleaned_code or self.get_default_plot_code()
        except Exception as e:
            print(f"Error generating plot code: {e}")
            return self.get_default_plot_code()

    def get_default_plot_code(self):
        return """
        import matplotlib.pyplot as plt
        import numpy as np
        plt.plot([1,2,3],[4,5,6])
        plt.title('Biểu đồ mặc định')
        plt.savefig('plot.png')
        """

    async def generate_plot(self, update: Update, context: CallbackContext, description: str):
        """Changed from static method to instance method"""
        user_id = update.message.chat_id
        try:
            if not description.strip():
                await update.message.reply_text("⚠️ Vui lòng nhập mô tả chi tiết")
                return

            # Lấy dữ liệu cũ nếu có yêu cầu sửa đồ thị
            last_data = None
            if "sửa" in description and user_id in self.user_plot_data and self.user_plot_data[
                    user_id]:
                last_data = self.user_plot_data[user_id][-1].get("data", {})

            # Tạo code vẽ đồ thị
            plot_code = await self.generate_plot_code(description, last_data)

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
            if user_id not in self.user_plot_data:
                self.user_plot_data[user_id] = []
            self.user_plot_data[user_id].append({
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