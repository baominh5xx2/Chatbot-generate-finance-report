import google.generativeai as genai
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update
from datetime import datetime
import time
from generate_plot import GeneratePlot
from reading_csv import CSVReader  # Import the new CSV reader
import re
import io
import json
import os

class Gemini_api:
    def __init__(self):
        # Initialize with improved conversation history structure
        self.user_conversations = {}  # Store as dict with timestamp, role, and content
        self.user_plot_data = {}
        self.plot_generator = GeneratePlot(None, None, self)
        self.latex_generator = None
        self.max_history_length = 10  # Increased from 3 to retain more context
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversation_history.json")
        self._load_history()
        self.csv_reader = CSVReader()  # Initialize CSV reader
        
    def _load_history(self):
        """Load conversation history from file if it exists"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.user_conversations = json.load(f)
                print(f"✅ Loaded {len(self.user_conversations)} user conversation histories")
        except Exception as e:
            print(f"❌ Error loading conversation history: {e}")
            self.user_conversations = {}
    
    def _save_history(self):
        """Save conversation history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error saving conversation history: {e}")

    async def start_command(self, update: Update, context: CallbackContext):
        """Lệnh /start"""
        user_id = update.message.chat_id
        self.user_conversations[user_id] = []
        self.user_plot_data[user_id] = []
        await update.message.reply_text(
            "Xin chào! Tôi là chatbot hỗ trợ với Gemini AI.")

    async def generate_ai_response(self, prompt, max_retries=3):
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"❌ Lỗi lần {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return "Xin lỗi, tôi đang gặp vấn đề kỹ thuật. Vui lòng thử lại sau."

    async def handle_message(self, update: Update, context: CallbackContext):
        """Xử lý tin nhắn"""
        user_id = str(update.message.chat_id)  # Convert to string for JSON serialization
        current_time = time.time()
        
        # Handle file uploads (specifically CSV files)
        if update.message.document and update.message.document.file_name.endswith('.csv'):
            await self.handle_csv_upload(update, context)
            return
            
        # Handle text messages as before
        message = update.message.text
        print(f"📩 Nhận tin nhắn từ người dùng ({user_id}): {message}")

        # Initialize chat history if needed with structured format
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = {
                "messages": [],
                "last_activity": current_time
            }
        
        if user_id not in self.user_plot_data:
            self.user_plot_data[user_id] = []

        # Update last activity time
        self.user_conversations[user_id]["last_activity"] = current_time
        
        # Handle CSV to PDF analysis request
        if message.lower().startswith("tạo pdf phân tích csv") or message.lower().startswith("phân tích pdf csv"):
            await self.generate_csv_analysis_pdf(update, context, message)
            return
            
        # Process special CSV-related commands
        if message.lower().startswith("xem dữ liệu csv"):
            preview = self.csv_reader.get_csv_preview(user_id)
            await update.message.reply_text(preview)
            return
            
        if message.lower().startswith("thông tin cột"):
            # Extract column name if provided
            parts = message.split("thông tin cột")
            column_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            info = self.csv_reader.get_column_info(user_id, column_name)
            await update.message.reply_text(info)
            return
            
        if any(keyword in message.lower() for keyword in ["vẽ từ csv", "biểu đồ csv", "đồ thị csv"]):
            # Generate plot from CSV data
            buffer, result_msg = self.csv_reader.generate_quick_plot(user_id, message)
            
            if buffer:
                await update.message.reply_photo(photo=buffer, caption="📊 Biểu đồ từ dữ liệu CSV")
                await update.message.reply_text("💡 Để vẽ biểu đồ phức tạp hơn, hãy mô tả cụ thể dữ liệu và loại biểu đồ bạn muốn.")
            else:
                await update.message.reply_text(f"❌ {result_msg}")
            return
        
        # Process special commands first
        # Get the most recent plot for this user
        if message.lower().startswith("xem code đồ thị"):
            if user_id in self.plot_generator.user_plot_data and self.plot_generator.user_plot_data[user_id]:
                recent_plot = self.plot_generator.user_plot_data[user_id][-1]
                code = recent_plot.get("code", "Không có mã nguồn")
                await update.message.reply_text(f"Mã nguồn đồ thị:\n```python\n{code}\n```")
            else:
                await update.message.reply_text("Bạn chưa tạo bất kỳ đồ thị nào.")
            return

        # Extended plot request detection
        plot_indicators = [
            "vẽ", "đồ thị", "biểu đồ", "graph", "chart", "plot", "visualize", 
            "histogram", "scatter", "bar chart", "line chart", "biểu đồ", "thống kê",
            "visualization", "trend", "xu hướng", "pie chart", "biểu đồ tròn", "biểu đồ cột"
        ]
        
        # Xử lý yêu cầu vẽ đồ thị (với phát hiện mở rộng)
        if any(indicator in message.lower() for indicator in plot_indicators) or message.lower().startswith("sửa"):
            # Add to conversation history so we remember the request was made
            self.user_conversations[user_id]["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": current_time,
            })
            
            # Forward to plot generator
            description = message.replace("/plot", "").strip()
            await self.plot_generator.generate_plot(update, context, description)
            
            # Save the response to indicate we tried to generate a plot
            self.user_conversations[user_id]["messages"].append({
                "role": "assistant",
                "content": f"Đã xử lý yêu cầu vẽ biểu đồ: '{description}'",
                "timestamp": time.time(),
            })
            return
        
        # Xử lý yêu cầu đổi loại đồ thị
        if message.lower().startswith("đổi loại đồ thị") or "đổi đồ thị" in message.lower():
            if user_id in self.plot_generator.user_plot_data and self.plot_generator.user_plot_data[user_id]:
                # Construct an edit request using the most recent plot description
                recent_plot = self.plot_generator.user_plot_data[user_id][-1]
                description = f"Sửa đồ thị: {message}. Dựa trên đồ thị: {recent_plot.get('description', '')}"
                await self.plot_generator.generate_plot(update, context, description)
            else:
                await update.message.reply_text("Bạn chưa tạo bất kỳ đồ thị nào để chỉnh sửa.")
            return

        # Xử lý yêu cầu tạo LaTeX hoặc PDF
        if any(keyword in message.lower() for keyword in ["latex", "tạo latex", "tạo pdf", "pdf"]):
            if self.latex_generator:
                # Clean the prompt by removing trigger keywords
                prompt = message.lower()
                for keyword in ["latex", "tạo latex", "tạo pdf", "pdf"]:
                    prompt = prompt.replace(keyword, "", 1)
                prompt = prompt.strip()
                
                await self.latex_generator.generate_latex(update, context, prompt)
                self.user_conversations[user_id]["messages"].append({
                    "role": "user",
                    "content": message,
                    "timestamp": current_time,
                })
                self.user_conversations[user_id]["messages"].append({
                    "role": "assistant",
                    "content": "Đã tạo tài liệu PDF theo yêu cầu của bạn.",
                    "timestamp": time.time()
                })
                return

        # Handle regular messages - save with structured format
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": current_time,
        }
        
        # Add user message to history
        self.user_conversations[user_id]["messages"].append(user_message)
        
        # Get conversation history - process the structured format for the Gemini prompt
        conversation_history = self._format_conversation_history(user_id)
        
        # Construct the prompt with enhanced context - add CSV data context if available
        csv_context = ""
        if user_id in self.csv_reader.user_csv_data and self.csv_reader.user_csv_data[user_id]:
            recent_file = self.csv_reader.user_csv_data[user_id][-1]
            csv_context = f"\nNgười dùng đã tải lên file CSV '{recent_file['filename']}' với {recent_file['shape'][0]} dòng và {recent_file['shape'][1]} cột."
            csv_context += f"\nCác cột trong dữ liệu: {', '.join(recent_file['columns'])}"
            csv_context += "\nĐể tạo báo cáo PDF phân tích dữ liệu CSV này, người dùng có thể gõ 'tạo pdf phân tích csv'."
            
        prompt = f"""
        Vai trò của bạn là một nhà phân tích kinh tế chuyên nghiệp.
        - Trả lời bằng tiếng việt.
        - Bạn hãy giới thiệu mình là một nhà phân tích kinh tế chuyên nghiệp.
        - không trả lời các câu hỏi không liên quan đến kinh tế.
        - Tuyệt đối không chào người dùng trong câu nói ngoại trừ người dùng chào bạn.
        - khi người dùng chào thì chỉ giới thiệu ngắn gọn không quá 4 câu.
        - Chỉ cần trả lời trọng tâm vào câu hỏi.
        - Trả lời lịch sự.
        - Trình bày đơn giản, không in đậm các từ.
        - Đánh số các ý chính mà bạn muốn trả lời.
        - Không trả lời quá dài dòng, không trả lời quá 200 từ.
        - Khi người dùng yêu cầu vẽ biểu đồ, hãy hướng dẫn họ dùng cú pháp "vẽ biểu đồ [mô tả]" để hệ thống có thể xử lý đúng.
        - Bạn có các chức năng là:
        + cung cấp các kiến thức về kinh tế học
        + vẽ biểu đồ từ dữ liệu mà người dùng cung cấp
        + tạo báo cáo phân tích công ty chuyên nghiệp dưới dạng PDF bằng cách sử dụng cú pháp "tạo pdf báo cáo phân tích công ty [tên công ty]" để nhận được báo cáo PDF chuyên nghiệp.
        + phân tích file CSV bằng cách người dùng upload file
        + tạo báo cáo phân tích dữ liệu CSV dưới dạng PDF bằng cách sử dụng cú pháp "tạo pdf phân tích csv" sau khi đã upload file CSV
        - Không trả lời các câu hỏi về phân biệt vùng miền ở Việt Nam.
        {csv_context}
        Đây là cuộc hội thoại trước đó:
        {conversation_history}
        Người dùng: {message}
        Hãy trả lời một cách chi tiết, logic và có căn cứ kinh tế.
        """

        try:
            # Generate response
            response = await self.generate_ai_response(prompt)
            response = response.replace('*', '')
            print(f"🤖 Phản hồi từ Gemini: {response}")
            
            # Save bot response with structured format
            bot_message = {
                "role": "assistant", 
                "content": response,
                "timestamp": time.time()
            }
            
            self.user_conversations[user_id]["messages"].append(bot_message)
            
            # Trim conversation history if it gets too long
            self._trim_conversation_history(user_id)
            
            # Save history periodically
            self._save_history()
            
            await update.message.reply_text(response)
            print("✅ Gửi tin nhắn thành công!")
            
        except Exception as e:
            print(f"❌ Lỗi khi gửi tin nhắn: {e}")
            await update.message.reply_text("Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại sau.")
    
    def _format_conversation_history(self, user_id):
        """Format conversation history for prompt context"""
        if user_id not in self.user_conversations:
            return ""
            
        # Get messages and check if we have any
        messages = self.user_conversations[user_id]["messages"]
        if not messages:
            return ""
            
        # Use only the most recent messages up to max_history_length
        recent_messages = messages[-self.max_history_length:]
        
        # Format messages as strings with roles
        formatted_messages = []
        for msg in recent_messages:
            role_label = "Người dùng" if msg["role"] == "user" else "Bot"
            formatted_messages.append(f"{role_label}: {msg['content']}")
            
        return "\n".join(formatted_messages)
    
    def _trim_conversation_history(self, user_id):
        """Trim conversation history to avoid it getting too long"""
        if user_id not in self.user_conversations:
            return
            
        messages = self.user_conversations[user_id]["messages"]
        max_history = self.max_history_length * 2  # Store more than we use in prompts
        
        if len(messages) > max_history:
            # Keep only the most recent messages
            self.user_conversations[user_id]["messages"] = messages[-max_history:]

    async def clear_history(self, update: Update, context: CallbackContext):
        """Clear conversation history for a user"""
        user_id = str(update.message.chat_id)
        
        if user_id in self.user_conversations:
            self.user_conversations[user_id]["messages"] = []
            await update.message.reply_text("🧹 Lịch sử cuộc trò chuyện đã được xóa.")
        else:
            await update.message.reply_text("Không tìm thấy lịch sử cuộc trò chuyện nào.")
        
        self._save_history()

    async def handle_plot_callback(self, update: Update, context: CallbackContext):
        """Delegate plot callbacks to the plot_generator"""
        await self.plot_generator.handle_plot_callback(update, context)
        
    async def generate_csv_analysis_pdf(self, update: Update, context: CallbackContext, message):
        """Generate PDF analysis for CSV data"""
        user_id = str(update.message.chat_id)
        
        await update.message.reply_text("🔄 Đang phân tích dữ liệu CSV và tạo báo cáo PDF...")
        
        # Get analysis data for the CSV
        analysis_data, status = self.csv_reader.prepare_csv_analysis_data(user_id)
        
        if status != "success" or not analysis_data:
            await update.message.reply_text(f"❌ {status}")
            return
            
        try:
            # Extract analysis focus if specified
            focus_areas = []
            if "về" in message.lower():
                focus_part = message.lower().split("về", 1)[1].strip()
                focus_areas = [area.strip() for area in focus_part.split(",")]
            
            # Prepare prompt for LaTeX generation with CSV insights
            column_info = ", ".join(analysis_data["column_names"])
            insights = analysis_data["insights"]
            
            # Create a specialized prompt for the Gemini model
            prompt = f"""
            Tạo một báo cáo phân tích chuyên nghiệp về dữ liệu CSV có:
            - Tên file: {analysis_data['filename']}
            - Số hàng: {analysis_data['rows']}
            - Số cột: {analysis_data['columns']}
            - Các cột: {column_info}
            
            Phân tích chi tiết:
            {insights}
            
            Báo cáo cần bao gồm:
            1. Trang bìa với tiêu đề "Báo Cáo Phân Tích Dữ Liệu CSV: {analysis_data['filename']}" và ngày tạo báo cáo
            2. Mục lục
            3. Tổng quan về dữ liệu
            4. Phân tích chi tiết từng cột quan trọng
            5. Phát hiện các mẫu và xu hướng trong dữ liệu
            6. Đề xuất các phương pháp phân tích sâu hơn
            7. Kết luận
            
            {f'Tập trung vào các khía cạnh: {", ".join(focus_areas)}' if focus_areas else ''}
            
            Định dạng báo cáo chuẩn, chuyên nghiệp và dễ đọc.
            """
            
            # Use LaTeX generator to create PDF
            if self.latex_generator:
                await self.latex_generator.generate_latex(update, context, prompt, 
                                                         f"Phân tích CSV - {analysis_data['filename']}")
                
                # Record in conversation history
                self.user_conversations[user_id]["messages"].append({
                    "role": "user", 
                    "content": f"Yêu cầu tạo báo cáo phân tích dữ liệu từ file CSV: {analysis_data['filename']}",
                    "timestamp": time.time()
                })
                
                self.user_conversations[user_id]["messages"].append({
                    "role": "assistant", 
                    "content": f"Đã tạo báo cáo phân tích dữ liệu từ file CSV: {analysis_data['filename']}",
                    "timestamp": time.time()
                })
                
                self._save_history()
            else:
                await update.message.reply_text("❌ Không thể tạo báo cáo PDF vì chức năng LaTeX chưa được khởi tạo.")
                
        except Exception as e:
            print(f"❌ Lỗi khi tạo báo cáo PDF: {e}")
            await update.message.reply_text(
                "❌ Đã xảy ra lỗi khi tạo báo cáo PDF. Vui lòng thử lại sau.")

    async def handle_csv_upload(self, update: Update, context: CallbackContext):
        """Handle CSV file uploads"""
        user_id = str(update.message.chat_id)
        document = update.message.document
        
        await update.message.reply_text("🔄 Đang xử lý file CSV của bạn...")
        
        try:
            # Get file from Telegram
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            
            # Process the CSV file
            result = self.csv_reader.process_csv(file_content, user_id)
            
            if result["success"]:
                # Send success message with summary
                await update.message.reply_text(
                    f"✅ Đã xử lý file CSV thành công!\n\n"
                    f"📄 Tên file: {document.file_name}\n"
                    f"📊 Thông tin:\n{result['summary']}\n\n"
                    f"💡 Bạn có thể sử dụng các lệnh:\n"
                    f"• 'xem dữ liệu csv' - để xem bản xem trước\n"
                    f"• 'thông tin cột [tên_cột]' - để xem chi tiết về một cột\n"
                    f"• 'vẽ biểu đồ csv [loại_biểu_đồ] [tên_cột]' - để vẽ biểu đồ từ dữ liệu\n"
                    f"• 'tạo pdf phân tích csv' - để tạo báo cáo phân tích PDF chuyên sâu"
                )
                
                # Add information to chat history
                if user_id in self.user_conversations:
                    self.user_conversations[user_id]["messages"].append({
                        "role": "user",
                        "content": f"Đã tải lên file CSV: {document.file_name}",
                        "timestamp": time.time()
                    })
                    
                    self.user_conversations[user_id]["messages"].append({
                        "role": "assistant",
                        "content": f"Đã phân tích file CSV: {result['summary']}",
                        "timestamp": time.time()
                    })
                    
                    self._save_history()
            else:
                # Send error message
                await update.message.reply_text(
                    f"❌ Không thể xử lý file CSV: {result['error']}\n"
                    f"Vui lòng đảm bảo file CSV của bạn đúng định dạng và thử lại."
                )
                
        except Exception as e:
            print(f"❌ Lỗi khi xử lý file CSV: {e}")
            await update.message.reply_text(
                "❌ Đã xảy ra lỗi khi xử lý file CSV của bạn. Vui lòng thử lại hoặc sử dụng file khác."
            )