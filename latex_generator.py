import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import CallbackContext
import re
from compile_latex import compile_latex_to_pdf, clean_latex_auxiliary_files

class LatexGenerator:
    def __init__(self, gemini_api):
        self.gemini_api = gemini_api
        self.user_latex_files = {}  # Store latex data by user
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latex_files")
        self.pdf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_files")
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)
    
    async def generate_latex(self, update: Update, context: CallbackContext, prompt: str, title=None):
        """Generate LaTeX code based on user's prompt and compile to PDF"""
        user_id = update.effective_user.id
        
        # Inform user that processing has started
        is_company_report = any(keyword in prompt.lower() for keyword in 
                               ["báo cáo công ty", "phân tích công ty", "company report"])
        
        if is_company_report:
            await update.message.reply_text("Đang tạo báo cáo phân tích công ty, vui lòng đợi...")
            # Enhanced prompt for company reports
            gemini_prompt = f"""
            Hãy tạo mã LaTeX cho một báo cáo phân tích công ty chuyên nghiệp với yêu cầu: {prompt}
            - dùng các thư viện đơn giản để tránh lỗi khi biên dịch với xelatex
            Tạo một báo cáo phân tích công ty hoàn chỉnh với các phần:
            - Tuyệt đối không bỏ trống nội dung phần nào.
            - Bài báo cáo phải thật hoàn chỉnh và chuyên nghiệp.
            - Viết chi tiết nhất có thể.
            - Không cần bỏ logo công ty.
            - Không viết mỗi phần một trang, viết dồn lại để tiết kiệm giấy.
            1. Trang bìa chuyên nghiệp với tiêu đề, logo (nếu có), ngày tháng
            2. Mục lục
            3. Tóm tắt điểm nhấn đầu tư (Executive Summary)
            4. Tổng quan về doanh nghiệp
            5. Phân tích ngành và môi trường kinh doanh
            6. Phân tích tài chính chi tiết (doanh thu, lợi nhuận, biên lợi nhuận, ROE, ROA, v.v.)
            7. Phân tích SWOT
            8. Định giá và dự báo
            9. Khuyến nghị đầu tư
            10. Các rủi ro chính
            11. Kết luận
            
            Mã LaTeX cần bao gồm:
            - Sử dụng gói beamer hoặc report/article với định dạng chuyên nghiệp
            - Tạo các bảng dữ liệu tài chính giả định hợp lý
            - Tạo các biểu đồ (dùng tikz hoặc pgfplots) minh họa cho phân tích
            - Định dạng chuyên nghiệp, tổ chức rõ ràng
            
            Chỉ trả về mã LaTeX hoàn chỉnh, không có giải thích. Bắt đầu với \documentclass và kết thúc với \end{{document}}.
            Sử dụng các gói cần thiết và tạo ra một tài liệu hoàn chỉnh.
            """
        else:
            await update.message.reply_text("Đang tạo tài liệu PDF từ yêu cầu của bạn...")
            # Standard prompt for other LaTeX documents
            gemini_prompt = f"""
            Hãy tạo mã LaTeX cho yêu cầu sau: {prompt}
            
            Chỉ trả về mã LaTeX hoàn chỉnh, không có giải thích. Bắt đầu với \documentclass và kết thúc với \end{{document}}.
            Mã LaTeX cần phải hoạt động được và không chứa lỗi cú pháp.
            Bao gồm các gói cần thiết và tạo ra một tài liệu hoàn chỉnh.
            Sử dụng các gói cơ bản như amsmath, graphicx, và hyperref.
            """
        
        try:
            # Generate LaTeX code using Gemini API
            latex_code = await self.gemini_api.generate_ai_response(gemini_prompt)
            
            # Clean up and extract the LaTeX code
            latex_code = self._clean_latex_code(latex_code)
            
            # Generate filenames
            base_filename = f"latex_{user_id}_{len(self.user_latex_files.get(user_id, []))+1}"
            if title:
                # Sanitize title for filename
                sanitized_title = re.sub(r'[^\w\s-]', '', title)
                sanitized_title = re.sub(r'[-\s]+', '_', sanitized_title)
                base_filename = f"{base_filename}_{sanitized_title}"
                
            tex_filename = f"{base_filename}.tex"
            tex_filepath = os.path.join(self.output_dir, tex_filename)
            
            # Save the LaTeX code to file
            with open(tex_filepath, "w", encoding="utf-8") as f:
                f.write(latex_code)
            
            # Let the user know compilation is starting
            await update.message.reply_text("Đang biên dịch LaTeX thành PDF...")
            
            # Compile to PDF
            success, result = compile_latex_to_pdf(tex_filepath, self.pdf_dir)
            
            # Store reference to files
            if user_id not in self.user_latex_files:
                self.user_latex_files[user_id] = []
            
            file_data = {
                "tex_filename": tex_filename,
                "tex_filepath": tex_filepath,
                "prompt": prompt,
            }
            
            if success:
                file_data["pdf_filepath"] = result
                file_data["pdf_filename"] = os.path.basename(result)
                
                # Create a shortened caption to avoid Telegram's caption length limit
                shortened_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
                caption = f"Tài liệu PDF đã được tạo thành công"
                
                # Send PDF to user
                try:
                    await update.message.reply_document(
                        document=open(result, "rb"),
                        filename=file_data["pdf_filename"],
                        caption=caption
                    )                    
                except Exception as e:
                    print(f"Error sending document: {e}")
                    # Try again with an even shorter caption
                    await update.message.reply_document(
                        document=open(result, "rb"),
                        filename=file_data["pdf_filename"]
                    )
                    await update.message.reply_text("PDF đã được tạo. Lưu ý: Không thể hiển thị toàn bộ mô tả do giới hạn của Telegram.")
                
                # Clean up auxiliary files
                filename_no_ext = os.path.splitext(os.path.basename(tex_filepath))[0]
                clean_latex_auxiliary_files(self.pdf_dir, filename_no_ext)
                
                await update.message.reply_text(
                    "✅ Tài liệu PDF đã được tạo thành công!"
                )
            else:
                # If compilation failed, send the LaTeX code instead
                await update.message.reply_text(
                    f"❌ Không thể biên dịch thành PDF: {result}\n\n"
                    f"Tuy nhiên, bạn vẫn có thể tải xuống mã LaTeX để tự biên dịch."
                )
                
                await update.message.reply_document(
                    document=open(tex_filepath, "rb"),
                    filename=tex_filename,
                    caption=f"Mã LaTeX (chưa biên dịch)"
                )
            
            # Add to user's files
            self.user_latex_files[user_id].append(file_data)
            
        except Exception as e:
            await update.message.reply_text(f"Xin lỗi, có lỗi khi tạo tài liệu LaTeX: {str(e)}")
            print(f"Lỗi khi tạo LaTeX: {e}")
    
    def _clean_latex_code(self, latex_code):
        """Clean up the generated LaTeX code"""
        # Remove code block formatting if present
        latex_code = re.sub(r'```latex\s*', '', latex_code)
        latex_code = re.sub(r'```\s*$', '', latex_code)
        
        # Ensure proper document structure
        if r'\documentclass' not in latex_code:
            latex_code = r'\documentclass{article}' + '\n' + latex_code
        
        if r'\begin{document}' not in latex_code:
            latex_code = latex_code.replace(r'\documentclass', 
                                          r'\documentclass{article}' + '\n' + 
                                          r'\usepackage{amsmath}' + '\n' +
                                          r'\usepackage{graphicx}' + '\n' +
                                          r'\usepackage[utf8]{inputenc}' + '\n' +
                                          r'\usepackage{hyperref}' + '\n' +
                                          r'\begin{document}' + '\n')
        
        if r'\end{document}' not in latex_code:
            latex_code += '\n' + r'\end{document}'
            
        return latex_code
    
    async def list_latex_files(self, update: Update, context: CallbackContext):
        """List all LaTeX files created by the user"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_latex_files or not self.user_latex_files[user_id]:
            await update.message.reply_text("Bạn chưa tạo tệp LaTeX nào.")
            return
        
        files_list = "Danh sách tài liệu LaTeX của bạn:\n\n"
        for i, file_data in enumerate(self.user_latex_files[user_id], 1):
            file_type = "PDF" if "pdf_filepath" in file_data else "LaTeX"
            files_list += f"{i}. [{file_type}] {file_data['prompt']}\n"
        
        files_list += "\nĐể tải lại một tài liệu, gõ: /latex_get [số thứ tự]"
        await update.message.reply_text(files_list)
    
    async def get_latex_file(self, update: Update, context: CallbackContext):
        """Send a specific LaTeX file to the user"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text("Vui lòng cung cấp số thứ tự tệp. Ví dụ: /latex_get 1")
            return
        
        try:
            index = int(context.args[0]) - 1
            if user_id not in self.user_latex_files or index < 0 or index >= len(self.user_latex_files[user_id]):
                await update.message.reply_text("Số thứ tự tệp không hợp lệ.")
                return
            
            file_data = self.user_latex_files[user_id][index]
            
            # Prefer to send PDF if available
            if "pdf_filepath" in file_data and os.path.exists(file_data["pdf_filepath"]):
                await update.message.reply_document(
                    document=open(file_data["pdf_filepath"], "rb"),
                    filename=file_data["pdf_filename"],
                    caption=f"Tài liệu PDF: {file_data['prompt']}"
                )
            else:
                # Fall back to LaTeX file if PDF not available
                await update.message.reply_document(
                    document=open(file_data["tex_filepath"], "rb"),
                    filename=file_data["tex_filename"],
                    caption=f"Mã LaTeX: {file_data['prompt']}"
                )
        
        except ValueError:
            await update.message.reply_text("Số thứ tự phải là một số nguyên.")
        except Exception as e:
            await update.message.reply_text(f"Lỗi: {str(e)}")
