import matplotlib.pyplot as plt
import numpy as np
import re
import io
import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext

class GeneratePlot:
    def __init__(self, x, y, gemini_api=None):
        self.x = x
        self.y = y
        self.user_plot_data = {}  # Format: {user_id: [plot_entries]}
        self.gemini_api = gemini_api
        self.MAX_HISTORY = 10  # Maximum number of plots to store per user

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

    def get_default_plot_code(self):
        """Return a safe default plot when everything else fails"""
        return """
        import matplotlib.pyplot as plt
        import numpy as np

        # Tạo dữ liệu mẫu
        categories = ['Sản phẩm A', 'Sản phẩm B', 'Sản phẩm C', 'Sản phẩm D']
        values = [25, 40, 30, 55]
        
        # Tạo biểu đồ
        plt.figure(figsize=(10, 6))
        plt.bar(categories, values, color='skyblue')
        plt.title('Biểu đồ mẫu - Doanh số sản phẩm')
        plt.ylabel('Doanh số (triệu đồng)')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        """

    async def generate_plot_code(self, description, last_data=None, plot_type=None):
        """Generate plot code using AI with better context about previous data"""
        # Format the previous data for easier use by the AI
        last_data_str = "None"
        if last_data:
            try:
                # Format data context for the AI to better understand
                data_vars = []
                for var_name, var_value in last_data.items():
                    if isinstance(var_value, (list, np.ndarray)):
                        data_vars.append(f"{var_name} = {var_value}")
                
                if data_vars:
                    last_data_str = "\n".join(data_vars)
            except Exception as e:
                print(f"Error formatting previous plot data: {e}")
                last_data_str = "Error accessing previous data"

        prompt = f"""
        - BẮT BUỘC bịa ra dữ liệu nếu người dùng không cung cấp
        - LUÔN LUÔN tạo biểu đồ dù thế nào - tạo dữ liệu mẫu phù hợp nếu cần
        - Không từ chối vẽ đồ thị, đảm bảo luôn có đồ thị để trả về
        - Trả về nguyên code Python, không giải thích
        - Mỗi lệnh matplotlib PHẢI xuống dòng riêng
        - TUYỆT ĐỐI KHÔNG viết nhiều lệnh plt trên cùng 1 dòng
        - Chỉ viết mỗi lệnh một dòng duy nhất
        - Yêu cầu: {description}

        {'' if plot_type is None else f'- Kiểu đồ thị được yêu cầu: {plot_type}'}
        
        - Dữ liệu từ đồ thị trước đó (sử dụng lại nếu phù hợp):
        {last_data_str}

        Code phải bao gồm:
        - Viết code làm sao để tránh lỗi khi chạy.
        - import matplotlib.pyplot as plt
        - import numpy as np
        - Vẽ đồ thị với plt.plot(), plt.scatter() hoặc plt.bar()
        - plt.title() với tiêu đề phù hợp
        - KHÔNG SỬ DỤNG plt.savefig(), ĐỪNG LƯU FILE
        - Code phải hợp lệ và có thể chạy trực tiếp mà không bị lỗi
        """

        try:
            code = await self.gemini_api.generate_ai_response(prompt) if self.gemini_api else None
            cleaned_code = self.clean_generated_code(code) if code else None
            return cleaned_code or self.get_default_plot_code()
        except Exception as e:
            print(f"Error generating plot code: {e}")
            return self.get_default_plot_code()

    def _detect_plot_type(self, description):
        """Detect what type of plot the user wants based on their description"""
        description = description.lower()
        
        if any(term in description for term in ["đường", "line", "trend", "xu hướng"]):
            return "line"
        elif any(term in description for term in ["cột", "bar", "biểu đồ cột", "histogram"]):
            return "bar"
        elif any(term in description for term in ["tròn", "pie", "bánh", "circle"]):
            return "pie"
        elif any(term in description for term in ["scatter", "điểm", "chấm", "phân tán"]):
            return "scatter"
        elif any(term in description for term in ["area", "vùng", "diện tích"]):
            return "area"
        elif any(term in description for term in ["box", "hộp"]):
            return "box"
            
        return None  # Let the AI decide

    def _is_edit_request(self, description):
        """Detect if the user is asking to edit/modify a previous plot"""
        edit_keywords = ["sửa", "thay đổi", "chỉnh", "cập nhật", "edit", "update", "modify", 
                         "thay", "điều chỉnh", "hiệu chỉnh"]
        return any(keyword in description.lower() for keyword in edit_keywords)

    def _store_plot_data(self, user_id, description, code, data_vars):
        """Store plot data with enhanced metadata"""
        if user_id not in self.user_plot_data:
            self.user_plot_data[user_id] = []
            
        # Create plot entry with metadata
        plot_entry = {
            "description": description,
            "code": code,
            "data": data_vars,
            "timestamp": datetime.now().isoformat(),
            "plot_type": self._detect_plot_type(description)
        }
        
        # Add to user's plot history
        self.user_plot_data[user_id].append(plot_entry)
        
        # Trim history if needed
        if len(self.user_plot_data[user_id]) > self.MAX_HISTORY:
            self.user_plot_data[user_id].pop(0)

    def _get_previous_plot(self, user_id, description=None):
        """Get the most relevant previous plot data based on description or most recent"""
        if user_id not in self.user_plot_data or not self.user_plot_data[user_id]:
            return None
            
        if description:
            # Try to find most relevant plot by description similarity
            # Simple implementation - can be enhanced with NLP techniques
            for plot in reversed(self.user_plot_data[user_id]):
                plot_desc = plot.get("description", "")
                if any(word in plot_desc.lower() for word in description.lower().split()):
                    return plot
                    
        # Default to most recent plot
        return self.user_plot_data[user_id][-1]

    async def generate_plot(self, update: Update, context: CallbackContext, description: str):
        user_id = update.message.chat_id
        try:
            if not description.strip():
                await update.message.reply_text("⚠️ Vui lòng nhập mô tả chi tiết cho biểu đồ.")
                return

            await update.message.reply_text("🔄 Đang tạo biểu đồ...")

            # Check if this is an edit request and get relevant previous plot data
            last_data = None
            plot_type = self._detect_plot_type(description)
            
            if self._is_edit_request(description):
                prev_plot = self._get_previous_plot(user_id, description)
                if prev_plot:
                    last_data = prev_plot.get("data", {})
                    if not plot_type and "plot_type" in prev_plot:
                        plot_type = prev_plot.get("plot_type")
                    await update.message.reply_text("🔄 Đang chỉnh sửa biểu đồ trước đó...")

            # Tạo code vẽ đồ thị
            plot_code = await self.generate_plot_code(description, last_data, plot_type)

            # Thực thi code
            plt.clf()
            exec_globals = {"plt": plt, "np": np, "io": io}
            exec_locals = {}
            try:
                # Fix any code that might try to save files
                modified_code = plot_code.replace("plt.savefig", "# plt.savefig")
                exec(modified_code, exec_globals, exec_locals)
            except Exception as e:
                error_msg = f"🚨 LỖI CODE:\n{plot_code}\nLỖI: {str(e)}"
                print(error_msg)
                # Ask user to try again instead of using a default plot
                await update.message.reply_text("⚠️ Không thể tạo biểu đồ với yêu cầu này. Vui lòng mô tả lại với yêu cầu cụ thể hơn.")
                plt.close()  # Make sure to close any partial figure
                return  # Exit the function early

            # Lưu đồ thị vào buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)

            # Extract variable data for storage
            data_to_store = {}
            for var_name, var_value in exec_locals.items():
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) > 0:
                    # Convert numpy arrays to lists for easier storage
                    if isinstance(var_value, np.ndarray):
                        data_to_store[var_name] = var_value.tolist()
                    else:
                        data_to_store[var_name] = var_value

            # Store plot data with enhanced metadata
            self._store_plot_data(user_id, description, plot_code, data_to_store)

            # Gửi ảnh qua Telegram
            await update.message.reply_photo(photo=buffer, caption=f"📊 {description}")
            
            # Send text-based instructions instead of buttons
            help_message = (
                "📝 Lệnh hữu ích:\n"
                "• Gõ 'sửa đồ thị [mô tả]' để chỉnh sửa đồ thị này\n"
                "• Gõ 'xem code đồ thị' để xem mã nguồn\n"
                "• Gõ 'đổi loại đồ thị thành [kiểu]' để đổi kiểu đồ thị"
            )
            await update.message.reply_text(help_message)

            # Đóng figure
            plt.close()
            
            # Clean up any potential temporary files in the current directory
            for file in os.listdir('.'):
                if file.endswith('.png') and (file == 'plot.png' or file.startswith('plt_')):
                    try:
                        os.remove(file)
                        print(f"✅ Đã xóa file tạm: {file}")
                    except Exception as e:
                        print(f"❌ Không thể xóa file {file}: {e}")

        except Exception as e:
            print(f"❌ Lỗi khi tạo đồ thị: {e}")
            # Ask the user to try again with a different request instead of creating a fallback plot
            plt.close()  # Make sure to close any partial figure
            await update.message.reply_text("❌ Xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại với cách mô tả khác.")