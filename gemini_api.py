import google.generativeai as genai
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update
from datetime import datetime
import time
from generate_plot import GeneratePlot
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
        user_id = str(update.message.chat_id)
        current_time = time.time()
        message = update.message.text
        
        # Check if we're expecting specific input for vnstock functions
        if context.user_data.get("expecting_input"):
            expected_input = context.user_data.pop("expecting_input")  # Remove after handling
            
            if expected_input == "stock_code_current":
                # Handle getting current price for the stock code
                stock_code = message.strip().upper()
                await update.message.reply_text(f"Đang lấy giá hiện tại cho mã {stock_code}...")
                
                # Implement code to fetch current stock price
                # For example:
                # from vnstock import get_stock_price
                # price_data = get_stock_price(stock_code)
                # await update.message.reply_text(f"Giá hiện tại của {stock_code}: {price_data}")
                return
                
            # Add other handlers for different expected inputs
        
        # Handle text messages as before
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
        
        # Handle VNStock related queries - redirect appropriate queries
        stock_keywords = ["chỉ số tài chính", "cổ phiếu", "chứng khoán", "thị trường"]
        if any(keyword in message.lower() for keyword in stock_keywords) and not message.startswith('/'):
            # Save the message in history for context
            self.user_conversations[user_id]["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": current_time,
            })
            
            # Generate a response about using search commands
            response = (
                "📊 Để truy vấn thông tin chứng khoán, bạn có thể sử dụng các lệnh sau:\n\n"
                "• /search [mã cổ phiếu] - Xem thông tin tài chính (VD: /search VNM)\n"
                "• /search_get [số] - Xem chỉ số cụ thể (sau khi chọn mã cổ phiếu)\n"
                "• /search_chart - Xem biểu đồ giá cổ phiếu\n"
                "• /search_help - Xem hướng dẫn sử dụng chi tiết\n\n"
                "Bạn cũng có thể tìm hiểu thêm thông tin kinh tế và thị trường chứng khoán bằng cách hỏi trực tiếp."
            )
            
            # Save the response
            self.user_conversations[user_id]["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": time.time()
            })
            
            await update.message.reply_text(response)
            return

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
        
        prompt = f"""
        Vai trò của bạn là một nhà phân tích kinh tế chuyên nghiệp.
        - nếu người dùng yêu cầu cung cấp dữ liệu, chỉ số chứng khoán thì yêu cầu người dùng gõ '/search'.
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
        - Không trả lời các câu hỏi về phân biệt vùng miền ở Việt Nam.
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