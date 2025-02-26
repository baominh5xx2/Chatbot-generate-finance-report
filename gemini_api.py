import google.generativeai as genai
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update
from generate_plot import GeneratePlot
from latex_api import LatexAPI

class Gemini_api:
    def __init__(self):
        self.user_conversations = {}
        self.user_plot_data = {}
        self.plot_generator = GeneratePlot(None, None, self)  # Pass self as gemini_api
        self.latex_api = LatexAPI()

    async def start_command(self, update: Update, context: CallbackContext):
        """Lệnh /start"""
        user_id = update.message.chat_id
        self.user_conversations[user_id] = []
        self.user_plot_data[user_id] = []
        await update.message.reply_text(
            "Xin chào! Tôi là chatbot hỗ trợ với Gemini AI.")

    @staticmethod
    def generate_ai_response(prompt, max_retries=3):
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text

    async def handle_message(self, update: Update, context: CallbackContext):
        """Xử lý tin nhắn"""
        user_id = update.message.chat_id
        message = update.message.text
        print(f"📩 Nhận tin nhắn từ người dùng ({user_id}): {message}")

        # Khởi tạo bộ nhớ nếu chưa có
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        if user_id not in self.user_plot_data:
            self.user_plot_data[user_id] = []

        # Xử lý yêu cầu vẽ đồ thị
        if "vẽ" in message.lower() or "đồ thị" in message.lower():
            self.user_conversations[user_id].append(f"Người dùng: {message}")
            description = message.replace("/plot", "").strip()
            await self.plot_generator.generate_plot(update, context, description)
            return
        
        # Xử lý yêu cầu tạo báo cáo
        if "vẽ report" in message.lower() or "vẽ báo cáo" in message.lower():
            await self.generate_report_command(update, context)
            return

        # Xử lý tin nhắn thông thường
        self.user_conversations[user_id].append(f"Người dùng: {message}")
        if len(self.user_conversations[user_id]) > 3:
            self.user_conversations[user_id].pop(0)

        conversation_history = "\n".join(self.user_conversations[user_id])
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
        - bạn có thể vẽ được, nếu vì một lý do nào đó mà không vẽ được, thì hãy yêu cầu người dùng yêu cầu vẽ lại.
        - Bạn có các chức năng là:
        + cung cấp các kiến thức về kinh tế học
        + vẽ biểu đồ từ dữ liệu mà người dùng cung cấp
        + tạo một báo cáo tài chính đơn giản
        - Không trả lời các câu hỏi về phân biệt vùng miền ở Việt Nam.
        Đây là cuộc hội thoại trước đó:
        {conversation_history}
        Người dùng: {message}
        Hãy trả lời một cách chi tiết, logic và có căn cứ kinh tế.
        """

        response = await self.generate_ai_response(prompt)
        response = response.replace('*', '')
        print(f"🤖 Phản hồi từ Gemini: {response}")

        self.user_conversations[user_id].append(f"Bot: {response}")

        try:
            await update.message.reply_text(response)
            print("✅ Gửi tin nhắn thành công!")
        except Exception as e:
            print(f"❌ Lỗi khi gửi tin nhắn: {e}")

    async def generate_report_command(self, update: Update, context: CallbackContext):
        """Generate and send PDF report"""
        user_id = update.message.chat_id
        await update.message.reply_text("Đang tạo báo cáo kinh tế. Vui lòng chờ...")  # Added confirmation message

        await update.message.reply_text("📊 Đang tạo báo cáo kinh tế...")

        prompt = """
        Tạo một báo cáo kinh tế chi tiết với các mục:
        1. Tổng quan kinh tế vĩ mô
        2. Các chỉ số kinh tế quan trọng
        3. Phân tích thị trường
        4. Dự báo và khuyến nghị
        
        Format báo cáo theo cấu trúc LaTeX.
        """
        
        report_content = self.generate_ai_response(prompt)
        pdf_buffer = await self.latex_api.generate_report(report_content)
        
        if pdf_buffer:
            await update.message.reply_document(
                document=pdf_buffer,
                filename=f'economic_report_{user_id}.pdf',
                caption="🎯 Báo cáo kinh tế của bạn đã sẵn sàng!"
            )
        else:
            await update.message.reply_text("❌ Xin lỗi, có lỗi khi tạo báo cáo PDF.")