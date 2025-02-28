import json
import os
import pandas as pd
from vnstock import Vnstock
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
import datetime

# Define the Vnstockk class first
class Vnstockk:
    def get_data_info(self, symbol, time):
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        data = stock.finance.ratio(period=time, lang='vi', dropna=True)
        
        # Create a dedicated folder for storing data
        data_folder = "financial_data"
        os.makedirs(data_folder, exist_ok=True)
        
        # Create filename using symbol and time period
        filename = f"{symbol}_{time}_financial_ratio.json"
        filepath = os.path.join(data_folder, filename)
        
        data_flat = data.copy()
        if isinstance(data_flat.columns, pd.MultiIndex):
            # Convert tuple column names to strings
            data_flat.columns = [str(col) for col in data_flat.columns]
        
        # Convert data to JSON and save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_flat.to_dict(orient='records'), f, ensure_ascii=False, indent=4)
        
        # Print the output
        print(f"Financial data for {symbol} ({time}):")
        print(data)
        
        return data

    def process_df(self, df):
        # Implementation from your code
        if isinstance(df, pd.DataFrame):
            for col in df.select_dtypes(include=['datetime64', 'datetime64[ns]']).columns:
                df[col] = df[col].astype(str)
        return df
    
    def save_company_data(self, data, symbol, time, data_type):
        # Implementation from your code
        data_folder = "financial_data"
        os.makedirs(data_folder, exist_ok=True)
        filename = f"{symbol}_{time}_{data_type}.json"
        filepath = os.path.join(data_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return filepath
    
    # Add all the other methods from your Vnstockk class
    def get_company_overview(self, symbol, time):
        # Implementation
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        overview = company.overview()
        data = overview.to_dict(orient='records') if hasattr(overview, 'to_dict') else overview
        self.save_company_data(data, symbol, time, "company_overview")
        return data
    
    def get_company_profile(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        profile = company.profile()
        data = profile.to_dict(orient='records') if hasattr(profile, 'to_dict') else profile
        self.save_company_data(data, symbol, time, "company_profile")
        return data
    
    def get_company_shareholders(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        shareholders = company.shareholders()
        data = shareholders.to_dict(orient='records') if hasattr(shareholders, 'to_dict') else shareholders
        self.save_company_data(data, symbol, time, "company_shareholders")
        return data
    
    def get_company_insider_deals(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        insider_deals = company.insider_deals()
        insider_deals = self.process_df(insider_deals)
        data = insider_deals.to_dict(orient='records') if hasattr(insider_deals, 'to_dict') else insider_deals
        self.save_company_data(data, symbol, time, "company_insider_deals")
        return data
    
    def get_company_subsidiaries(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        subsidiaries = company.subsidiaries()
        subsidiaries = self.process_df(subsidiaries)
        data = subsidiaries.to_dict(orient='records') if hasattr(subsidiaries, 'to_dict') else subsidiaries
        self.save_company_data(data, symbol, time, "company_subsidiaries")
        return data
    
    def get_company_officers(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        officers = company.officers()
        officers = self.process_df(officers)
        data = officers.to_dict(orient='records') if hasattr(officers, 'to_dict') else officers
        self.save_company_data(data, symbol, time, "company_officers")
        return data
    
    def get_company_news(self, symbol, time):
        company = Vnstock().stock(symbol=symbol, source='TCBS').company
        news = company.news()
        news = self.process_df(news)
        data = news.to_dict(orient='records') if hasattr(news, 'to_dict') else news
        self.save_company_data(data, symbol, time, "company_news")
        return data

    def company_info(self, symbol, time):
        # Implementation
        company_overview = self.get_company_overview(symbol, time)
        company_profile = self.get_company_profile(symbol, time)
        company_shareholders = self.get_company_shareholders(symbol, time)
        company_insider_deals = self.get_company_insider_deals(symbol, time)
        company_subsidiaries = self.get_company_subsidiaries(symbol, time)
        company_officers = self.get_company_officers(symbol, time)
        company_news = self.get_company_news(symbol, time)
        
        all_company_data = {
            "overview": company_overview,
            "profile": company_profile,
            "shareholders": company_shareholders,
            "insider_deals": company_insider_deals,
            "subsidiaries": company_subsidiaries,
            "officers": company_officers,
            "news": company_news
        }
        
        self.save_company_data(all_company_data, symbol, time, "company_info")
        return all_company_data

    def load_financial_data(self, symbol, time_period, data_type="financial_ratio"):
        """
        Load financial data from saved JSON files
        
        Args:
            symbol (str): Stock symbol
            time_period (str): 'quarter' or 'yearly'
            data_type (str): Type of data to load (default: 'financial_ratio')
            
        Returns:
            dict/DataFrame: The loaded data or None if file doesn't exist
        """
        data_folder = "financial_data"
        filename = f"{symbol}_{time_period}_{data_type}.json"
        filepath = os.path.join(data_folder, filename)
        
        if os.path.exists(filepath):
            try:
                print(f"Loading data from {filepath}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # If data is for financial ratios, convert to DataFrame for easier processing
                if data_type == "financial_ratio" and isinstance(data, list):
                    df = pd.DataFrame(data)
                    
                    # Convert column names to MultiIndex if they are string representations of tuples
                    if df.columns.str.contains(r'^\(.*\)$').any():
                        # Extract tuples from string representation
                        tuples = [eval(col) if col.startswith('(') else ('Other', col) for col in df.columns]
                        df.columns = pd.MultiIndex.from_tuples(tuples)
                    
                    return df
                    
                return data
            except Exception as e:
                print(f"Error loading data from {filepath}: {str(e)}")
                return None
        else:
            print(f"File not found: {filepath}")
            return None

    def load_company_data(self, symbol, time_period):
        """Load company information from saved JSON files"""
        data_type = "company_info"
        return self.load_financial_data(symbol, time_period, data_type)

# Then define your VNStockService class as before
class VNStockService(Vnstockk):
    """Enhanced VNStock service that utilizes Vnstockk functionality"""
    
    def __init__(self):
        # Initialize Vnstockk parent class
        super().__init__()
        
        try:
            with open('labels.json', 'r', encoding='utf-8') as f:
                self.labels = json.load(f)
        except Exception as e:
            print(f"Error loading labels.json: {e}")
            self.labels = {}
            
        self.current_symbol = None
        self.vnstock_instance = None
        self.stock_data = None
        self.time_period = "quarter"  # Default to quarterly data
        
        # Create directory for financial data if it doesn't exist
        os.makedirs("financial_data", exist_ok=True)

    async def search_stock(self, update: Update, context: CallbackContext):
        """Handle the /search command"""
        if not context.args or len(context.args) != 1:
            # Show interactive menu for stock selection
            keyboard = [
                [
                    InlineKeyboardButton("Nhập mã cổ phiếu", callback_data="vnstock_input_symbol"),
                    InlineKeyboardButton("Xem danh sách", callback_data="vnstock_list_symbols")
                ],
                [
                    InlineKeyboardButton("Thông tin sử dụng", callback_data="vnstock_help")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Vui lòng sử dụng lệnh: /search [mã cổ phiếu] hoặc chọn một tùy chọn bên dưới:",
                reply_markup=reply_markup
            )
            return
            
        symbol = context.args[0].upper()
        self.current_symbol = symbol  # Guardar el símbolo actual
        
        # Mostrar directamente el menú principal sin preguntar por el período
        keyboard = [
            [
                InlineKeyboardButton("Thông tin tài chính", callback_data=f"vnstock_financial_info_{symbol}"),
                InlineKeyboardButton("Thông tin công ty", callback_data=f"vnstock_company_info_{symbol}")
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Chọn loại thông tin về {symbol} bạn muốn xem:",
            reply_markup=reply_markup
        )

    async def get_financial_data(self, update: Update, context: CallbackContext):
        """Handle the /search_get command to retrieve financial data"""
        if not self.current_symbol:
            await update.message.reply_text("Vui lòng sử dụng /search [mã cổ phiếu] trước!")
            return
            
        if not context.args:
            await update.message.reply_text(self.get_categories_menu())
            return
            
        category = context.args[0]
        result = self.get_indicators(category)
        await update.message.reply_text(result)
        
    async def get_stock_chart(self, update: Update, context: CallbackContext):
        """Handle the /search_chart command to get stock charts"""
        if not self.current_symbol:
            await update.message.reply_text("Vui lòng sử dụng /search [mã cổ phiếu] trước!")
            return
        
        # This would normally fetch and display a chart
        await update.message.reply_text(
            f"📊 Biểu đồ cho {self.current_symbol}:\n\n"
            "Tính năng đang được phát triển. Sẽ có trong bản cập nhật tiếp theo!"
        )
        
        
    async def handle_callback(self, update: Update, context: CallbackContext):
        """Handle callback queries for VNStock interactions"""
        query = update.callback_query
        await query.answer()
        
        # Handle period selection
        if query.data.startswith("vnstock_period_"):
            parts = query.data.split("_")
            if len(parts) >= 4:
                self.time_period = parts[2]  # quarter or yearly
                symbol = parts[3]
                self.current_symbol = symbol
                
                await query.edit_message_text(f"Đã tải dữ liệu thành công cho {symbol}!")
                
                # Create two main option buttons instead of showing all categories directly
                keyboard = [
                    [
                        InlineKeyboardButton("Thông tin tài chính", callback_data=f"vnstock_financial_info_{symbol}"),
                        InlineKeyboardButton("Thông tin công ty", callback_data=f"vnstock_company_info_{symbol}"),
                    ],
                    [
                        InlineKeyboardButton("Biểu đồ", callback_data="vnstock_chart")
                    ],
                    [
                        InlineKeyboardButton("Đổi loại dữ liệu", callback_data=f"vnstock_change_period_{symbol}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"Chọn loại thông tin về {symbol} bạn muốn xem:", reply_markup=reply_markup)
                return
                
        elif query.data.startswith("vnstock_change_period_"):
            # Handle changing data period after initial selection
            symbol = query.data.replace("vnstock_change_period_", "")
            keyboard = [
                [
                    InlineKeyboardButton("Dữ liệu Quý (Quarterly)", callback_data=f"vnstock_period_quarter_{symbol}"),
                    InlineKeyboardButton("Dữ liệu Năm (Yearly)", callback_data=f"vnstock_period_yearly_{symbol}")
                ],
                [
                    InlineKeyboardButton("← Quay lại", callback_data="vnstock_back_to_main")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Chọn loại dữ liệu tài chính cho mã {symbol}:",
                reply_markup=reply_markup
            )
            return
        # 2. Thêm xử lý callback khi nút "Thông tin công ty" được nhấn (sau phần xử lý vnstock_financial_info_)
        elif query.data.startswith("vnstock_company_info_"):
            # Extract symbol from callback data
            symbol = query.data.replace("vnstock_company_info_", "")
            
            await query.edit_message_text(f"Đang tải thông tin công ty {symbol}...")
            
            try:
                # Kiểm tra và tải dữ liệu công ty
                file_path = os.path.join("financial_data", f"{symbol}_{self.time_period}_company_info.json")
                print(f"Tìm file: {file_path}")
                
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        company_data = json.load(f)
                        print(f"Đã tìm thấy dữ liệu công ty với các mục: {list(company_data.keys())}")
                else:
                    # Tải dữ liệu mới
                    print(f"Không tìm thấy file. Đang tải dữ liệu mới...")
                    company_data = self.company_info(symbol, self.time_period)
                    print(f"Đã tải xong dữ liệu công ty")
                
                # Tạo các nút thông tin chi tiết
                keyboard = [
                    [
                        InlineKeyboardButton("Tổng quan", callback_data=f"company_section_{symbol}_overview"),
                        InlineKeyboardButton("Hồ sơ", callback_data=f"company_section_{symbol}_profile")
                    ],
                    [
                        InlineKeyboardButton("Cổ đông", callback_data=f"company_section_{symbol}_shareholders"),
                        InlineKeyboardButton("Giao dịch nội bộ", callback_data=f"company_section_{symbol}_insider_deals")
                    ],
                    [
                        InlineKeyboardButton("Công ty con", callback_data=f"company_section_{symbol}_subsidiaries"),
                        InlineKeyboardButton("Ban lãnh đạo", callback_data=f"company_section_{symbol}_officers")
                    ],
                    [
                        InlineKeyboardButton("Tin tức", callback_data=f"company_section_{symbol}_news"),
                    ],
                    [
                        InlineKeyboardButton("← Quay lại", callback_data="vnstock_back_to_main")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"Thông tin công ty {symbol}:", reply_markup=reply_markup)
            except Exception as e:
                import traceback
                traceback.print_exc()
                await query.edit_message_text(f"Lỗi khi tải thông tin công ty: {str(e)}")
        elif query.data.startswith("vnstock_category_"):
            # Generic handler for all category buttons
            category = query.data.replace("vnstock_category_", "")
            
            # Handle "all" as a special case
            if category == "all":
                result = self.get_indicators("all")
                await query.edit_message_text(text=result)
                return
            
            try:
                # Convert category string to index
                category_idx = int(category)
                
                # Get the category name
                categories = [cat for cat in self.stock_data.columns.get_level_values(0).unique() 
                             if cat != "Meta"]
                
                if category_idx < 1 or category_idx > len(categories):
                    await query.edit_message_text("Danh mục không hợp lệ.")
                    return
                    
                category_name = categories[category_idx - 1]
                
                # Get indicators for this category
                indicators = [col[1] for col in self.stock_data.columns if col[0] == category_name]
                
                # Create buttons for each indicator
                keyboard = []
                # Add buttons with 2 indicators per row
                for i in range(0, len(indicators), 2):
                    row = []
                    row.append(InlineKeyboardButton(
                        indicators[i], 
                        callback_data=f"vn_ind_{category_idx}_{i}"
                    ))
                    
                    if i+1 < len(indicators):
                        row.append(InlineKeyboardButton(
                            indicators[i+1], 
                            callback_data=f"vn_ind_{category_idx}_{i+1}"
                        ))
                        
                    keyboard.append(row)
                    
                # Add "Show All" button
                keyboard.append([
                    InlineKeyboardButton(
                        "Hiển thị tất cả chỉ số", 
                        callback_data=f"vn_ind_{category_idx}_all"
                    )
                ])
                
                # Add back button
                keyboard.append([
                    InlineKeyboardButton("← Quay lại", callback_data="vnstock_back_to_main")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"Chọn chỉ số {category_name} bạn muốn xem ({self.time_period}):",
                    reply_markup=reply_markup
                )
            except Exception as e:
                await query.edit_message_text(f"Lỗi xử lý yêu cầu: {str(e)}")
            
        elif query.data.startswith("vn_ind_"):
            # New shortened format handler for indicators
            # Format: vn_ind_categoryIdx_indicatorIdx
            parts = query.data.split("_")
            if len(parts) == 4:
                category_idx = int(parts[2])  # Category index
                indicator_idx = parts[3]      # Indicator index or "all"
                
                # Get the category name
                categories = [cat for cat in self.stock_data.columns.get_level_values(0).unique() 
                            if cat != "Meta"]
                if not categories or category_idx > len(categories):
                    await query.edit_message_text("Dữ liệu không hợp lệ.")
                    return
                    
                category_name = categories[category_idx - 1]  # Fix: use 1-indexed like elsewhere
                
                if indicator_idx == "all":
                    # Show all indicators in this category
                    result = self._get_specific_category_indicators(category_name)
                    await query.edit_message_text(text=result)
                else:
                    # Show the specific indicator based on index
                    try:
                        indicator_idx = int(indicator_idx)
                        indicators = [col[1] for col in self.stock_data.columns if col[0] == category_name]
                        
                        if indicator_idx >= len(indicators):
                            await query.edit_message_text("Chỉ số không hợp lệ.")
                            return
                            
                        indicator_name = indicators[indicator_idx]
                        result = self._get_specific_indicator(category_name, indicator_name)
                        
                        # Add a back button - use shortened callback data
                        keyboard = [[InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_category_{category_idx}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await query.edit_message_text(text=result, reply_markup=reply_markup)
                    except (ValueError, IndexError) as e:
                        await query.edit_message_text(f"Lỗi khi xử lý yêu cầu: {str(e)}")
            else:
                await query.edit_message_text("Định dạng dữ liệu không hợp lệ.")
        
        # Keep handling the old format but we'll remove it later when all clients are updated
        elif query.data.startswith("vnstock_indicator_"):
            # Handle individual indicator selection - old format
            # Format: vnstock_indicator_CATEGORY_NAME_INDICATOR_NAME
            parts = query.data.replace("vnstock_indicator_", "").split("_", 1)
            if len(parts) == 2:
                category_name = parts[0]
                indicator_name = parts[1]
                
                if indicator_name == "all":
                    # Show all indicators in this category
                    result = self._get_specific_category_indicators(category_name)
                    await query.edit_message_text(text=result)
                else:
                    # Show specific indicator
                    result = self._get_specific_indicator(category_name, indicator_name)
                    
                    # Add a back button
                    keyboard = [[InlineKeyboardButton("← Quay lại", callback_data="vnstock_category_1")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(text=result, reply_markup=reply_markup)
            else:
                await query.edit_message_text("Có lỗi khi xử lý yêu cầu. Vui lòng thử lại.")
        
        elif query.data == "vnstock_chart":
            # Handle chart button
            try:
                await self.get_stock_chart(update, context)
            except Exception as e:
                await query.edit_message_text(f"Lỗi khi tạo biểu đồ: {str(e)}")
        elif query.data.startswith("vnstock_financial_info_"):
            # Extraer el símbolo
            symbol = query.data.replace("vnstock_financial_info_", "")
            
            # Solicitar el período
            keyboard = [
                [
                    InlineKeyboardButton("Dữ liệu Quý (Quarterly)", callback_data=f"vnstock_fin_period_quarter_{symbol}"),
                    InlineKeyboardButton("Dữ liệu Năm (Yearly)", callback_data=f"vnstock_fin_period_yearly_{symbol}")
                ],
                [
                    InlineKeyboardButton("← Quay lại", callback_data="vnstock_back_to_main")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Chọn loại dữ liệu tài chính cho mã {symbol}:",
                reply_markup=reply_markup
            )
        # 3. Thêm phần xử lý khi nhấn vào một mục thông tin công ty cụ thể
        # Truy xuất đúng dữ liệu từ các mục thông tin công ty
        elif query.data.startswith("company_section_"):
            parts = query.data.split("_")
            print(f"DEBUG: Nhận được callback company_section_ với data: {query.data}, parts: {parts}")
            
            if len(parts) >= 4:
                symbol = parts[2]
                section = parts[3]
                
                await query.answer()  # Xác nhận callback để tránh timeout
                await query.edit_message_text(f"Đang tải thông tin {section} cho {symbol}...")
                
                try:
                    print(f"DEBUG: Bắt đầu xử lý section {section} cho {symbol}")
                    
                    # Tìm dữ liệu từ các đường dẫn có thể có
                    file_paths = [
                        os.path.join("financial_data", f"{symbol}_{self.time_period}_company_info.json"),
                        os.path.join("financial_data", f"{symbol}_quarter_company_info.json"),
                        os.path.join("financial_data", f"{symbol}_yearly_company_info.json")
                    ]
                    
                    print(f"DEBUG: Tìm kiếm các file: {file_paths}")
                    
                    company_data = None
                    found_file = None
                    
                    for path in file_paths:
                        if os.path.exists(path):
                            found_file = path
                            print(f"DEBUG: Đã tìm thấy file {path}")
                            try:
                                with open(path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                    print(f"DEBUG: Đọc được {len(file_content)} bytes từ file")
                                    if not file_content.strip():
                                        print("DEBUG: File rỗng!")
                                        continue
                                        
                                    company_data = json.loads(file_content)
                                    print(f"DEBUG: Đã load dữ liệu thành công với các keys: {list(company_data.keys())}")
                                    break
                            except json.JSONDecodeError as je:
                                print(f"DEBUG: Lỗi định dạng JSON: {je}")
                            except Exception as read_err:
                                print(f"DEBUG: Lỗi đọc file {path}: {read_err}")
                    
                    if not company_data:
                        # Nếu không tìm thấy file hoặc file không đọc được, tải mới
                        print(f"DEBUG: Không tìm thấy dữ liệu hợp lệ, đang gọi API...")
                        try:
                            company_data = self.company_info(symbol, self.time_period)
                            print(f"DEBUG: API trả về dữ liệu với keys: {list(company_data.keys()) if company_data else 'None'}")
                            
                            # Kiểm tra file đã được lưu chưa
                            new_path = os.path.join("financial_data", f"{symbol}_{self.time_period}_company_info.json")
                            if os.path.exists(new_path):
                                print(f"DEBUG: File mới đã được tạo: {new_path}")
                            else:
                                print(f"DEBUG: CẢNH BÁO - File mới không được tạo: {new_path}")
                        except Exception as api_err:
                            print(f"DEBUG: Lỗi khi gọi API: {str(api_err)}")
                            import traceback
                            traceback.print_exc()
                    
                    if not company_data:
                        error_msg = f"Không thể tải dữ liệu công ty cho {symbol} sau nhiều lần thử"
                        print(f"DEBUG: {error_msg}")
                        await query.edit_message_text(
                            error_msg, 
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_company_info_{symbol}")
                            ]])
                        )
                        return
                        
                    if section not in company_data:
                        missing_msg = f"Không có dữ liệu {section} cho {symbol}. Các mục có sẵn: {list(company_data.keys())}"
                        print(f"DEBUG: {missing_msg}")
                        await query.edit_message_text(
                            f"Không có dữ liệu {section} cho {symbol}", 
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_company_info_{symbol}")
                            ]])
                        )
                        return
                    
                    print(f"DEBUG: Đã tìm thấy dữ liệu {section}, tiếp tục xử lý...")
                    # (tiếp tục code hiện tại)
                    
                    # Xử lý hiển thị thông tin theo từng mục
                    max_items = 20  # Giới hạn số lượng hiển thị
                    result = ""
                    data = company_data.get(section, [])
                    
                    if section == "overview":
                        result = f"📋 Tổng quan {symbol}:\n\n"
                        if isinstance(data, list) and data:
                            overview = data[0]
                            # Truy xuất đúng các trường theo file JSON
                            name = overview.get("short_name", symbol)
                            exchange = overview.get("exchange", "N/A")
                            industry = overview.get("industry", "N/A")
                            website = overview.get("website", "N/A")
                            established = overview.get("established_year", "N/A")
                            employees = overview.get("no_employees", "N/A")
                            foreign_percent = overview.get("foreign_percent", 0)
                            
                            result += f"Tên: {name}\n"
                            result += f"Sàn: {exchange}\n"
                            result += f"Ngành: {industry}\n"
                            result += f"Website: {website}\n"
                            result += f"Năm thành lập: {established}\n"
                            result += f"Số nhân viên: {employees}\n"
                            result += f"Tỷ lệ nước ngoài: {foreign_percent*100:.2f}%\n"
                        else:
                            result += "Không có thông tin tổng quan"
                    
                    elif section == "profile":
                        result = f"📝 Hồ sơ {symbol}:\n\n"
                        if isinstance(data, list) and data:
                            profile = data[0]
                            # Truy xuất đúng các trường theo file JSON
                            company_name = profile.get("company_name", "N/A")
                            company_profile = profile.get("company_profile", "Không có thông tin")
                            
                            result += f"Tên công ty: {company_name}\n\n"
                            result += f"{company_profile}\n"
                        else:
                            result += "Không có thông tin hồ sơ"
                    
                    elif section == "shareholders":
                        result = f"👥 Cổ đông chính của {symbol}:\n\n"
                        for i, item in enumerate(data[:max_items], 1):
                            # Truy xuất đúng các trường theo file JSON
                            name = item.get("share_holder", "N/A")
                            percent = item.get("share_own_percent", 0)
                            # Hiển thị phần trăm đúng
                            percent_display = percent*100 if percent < 1 else percent
                            result += f"{i}. {name}: {percent_display:.2f}%\n"
                    
                    elif section == "insider_deals":
                        result = f"🤝 Giao dịch nội bộ gần đây của {symbol}:\n\n"
                        for i, item in enumerate(data[:max_items], 1):
                            # Truy xuất đúng các trường theo file JSON
                            date = item.get("deal_announce_date", "N/A")
                            action = item.get("deal_action", "N/A")
                            quantity = item.get("deal_quantity", 0)
                            
                            result += f"{i}. Ngày: {date}\n"
                            result += f"   Hành động: {action}\n"
                            result += f"   Khối lượng: {quantity:,.0f}\n\n"
                    
                    elif section == "subsidiaries":
                        result = f"🏢 Công ty con của {symbol}:\n\n"
                        for i, item in enumerate(data[:max_items], 1):
                            # Truy xuất đúng các trường theo file JSON
                            name = item.get("sub_company_name", "N/A")
                            percent = item.get("sub_own_percent", 0)
                            percent_display = percent*100 if percent < 1 else percent
                            result += f"{i}. {name}: {percent_display:.2f}%\n"
                    
                    elif section == "officers":
                        result = f"👨‍💼 Ban lãnh đạo của {symbol}:\n\n"
                        for i, item in enumerate(data[:max_items], 1):
                            # Truy xuất đúng các trường theo file JSON
                            name = item.get("officer_name", "N/A")
                            position = item.get("officer_position", "N/A") or "N/A"
                            own_percent = item.get("officer_own_percent", 0)
                            percent_display = own_percent*100 if own_percent < 1 else own_percent
                            
                            result += f"{i}. {name}\n"
                            result += f"   Chức vụ: {position}\n"
                            result += f"   Tỷ lệ sở hữu: {percent_display:.4f}%\n\n"
                    
                    elif section == "news":
                        result = f"📰 Tin tức gần đây về {symbol}:\n\n"
                        for i, item in enumerate(data[:max_items], 1):
                            # Truy xuất đúng các trường theo file JSON
                            title = str(item.get("title", ""))
                            if title.startswith(f"{symbol}:"):
                                title = title.split(":", 1)[1].strip()
                            date = item.get("publish_date", "N/A")
                            
                            result += f"{i}. [{date}] {title}\n\n"
                    
                    else:
                        result = f"Không có dữ liệu {section} cho {symbol}"
                    
                    # Thêm nút quay lại
                    keyboard = [
                        [InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_company_info_{symbol}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(result, reply_markup=reply_markup)
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await query.edit_message_text(
                        f"Lỗi khi hiển thị thông tin {section} cho {symbol}: {str(e)}",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_company_info_{symbol}")
                        ]])
                    )
        elif query.data.startswith("vnstock_fin_period_"):
            # Procesar la selección del período para datos financieros
            parts = query.data.split("_")
            if len(parts) >= 4:
                self.time_period = parts[3]  # quarter o yearly
                symbol = parts[4]
                self.current_symbol = symbol
                
                # Cargar datos financieros
                await query.edit_message_text(f"Đang tải dữ liệu tài chính {self.time_period} cho {symbol}...")
                
                try:
                    success, message = self.get_stock_info(symbol)
                    if not success:
                        await query.edit_message_text(message)
                        return
                except Exception as e:
                    await query.edit_message_text(f"Lỗi khi tải dữ liệu tài chính: {str(e)}")
                    return
                
                # Mostrar categorías financieras
                categories = [cat for cat in self.stock_data.columns.get_level_values(0).unique() 
                            if cat != "Meta"]
                
                # Crear botones para cada categoría
                keyboard = []
                for idx, category in enumerate(categories, 1):
                    keyboard.append([
                        InlineKeyboardButton(category, callback_data=f"vnstock_category_{idx}")
                    ])
                
                # Añadir botón "Todos los indicadores"
                keyboard.append([
                    InlineKeyboardButton("Tất cả chỉ số", callback_data="vnstock_category_all")
                ])
                
                # Añadir botón para volver
                keyboard.append([
                    InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_financial_info_{symbol}")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"Chọn chỉ số tài chính của {symbol} bạn muốn xem ({self.time_period}):",
                    reply_markup=reply_markup
                )
                
        elif query.data.startswith("vnstock_comp_period_"):
            # Procesar la selección del período para datos de la empresa
            parts = query.data.split("_")
            if len(parts) >= 4:
                self.time_period = parts[3]  # quarter o yearly
                symbol = parts[4]
                self.current_symbol = symbol
                
                await query.edit_message_text(f"Đang tải thông tin công ty {symbol} ({self.time_period})...")
                
                try:
                    # Cargar o descargar datos de la empresa
                    file_path = os.path.join("financial_data", f"{symbol}_{self.time_period}_company_info.json")
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            company_data = json.load(f)
                    else:
                        company_data = self.company_info(symbol, self.time_period)
                    
                    # Mostrar secciones de información de la empresa
                    keyboard = [
                        [
                            InlineKeyboardButton("Tổng quan", callback_data=f"company_section_{symbol}_overview"),
                            InlineKeyboardButton("Hồ sơ", callback_data=f"company_section_{symbol}_profile")
                        ],
                        [
                            InlineKeyboardButton("Cổ đông", callback_data=f"company_section_{symbol}_shareholders"),
                            InlineKeyboardButton("Giao dịch nội bộ", callback_data=f"company_section_{symbol}_insider_deals")
                        ],
                        [
                            InlineKeyboardButton("Công ty con", callback_data=f"company_section_{symbol}_subsidiaries"),
                            InlineKeyboardButton("Ban lãnh đạo", callback_data=f"company_section_{symbol}_officers")
                        ],
                        [
                            InlineKeyboardButton("Tin tức", callback_data=f"company_section_{symbol}_news"),
                        ],
                        [
                            InlineKeyboardButton("← Quay lại", callback_data=f"vnstock_company_info_{symbol}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"Thông tin công ty {symbol} ({self.time_period}):", reply_markup=reply_markup)
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await query.edit_message_text(f"Lỗi khi tải thông tin công ty: {str(e)}")
        elif query.data == "vnstock_back_to_main":
            if self.current_symbol:
                keyboard = [
                    [
                        InlineKeyboardButton("Thông tin tài chính", callback_data=f"vnstock_financial_info_{self.current_symbol}"),
                        InlineKeyboardButton("Thông tin công ty", callback_data=f"vnstock_company_info_{self.current_symbol}")
                    ],
                    [
                        InlineKeyboardButton("Biểu đồ", callback_data="vnstock_chart")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"Chọn loại thông tin về {self.current_symbol} bạn muốn xem:", reply_markup=reply_markup)
            else:
                await query.edit_message_text("Vui lòng sử dụng /search [mã cổ phiếu] để bắt đầu.")
    def _get_specific_category_indicators(self, category_name):
        """Get all indicators for a specific category"""
        if not self.current_symbol or self.stock_data is None:
            return "Vui lòng nhập lệnh /search [mã cổ phiếu] trước!"
            
        try:
            result = f"📊 {category_name} cho {self.current_symbol}:\n\n"
            
            # Get indicators for this category
            indicators = [col[1] for col in self.stock_data.columns if col[0] == category_name]
            
            # Get years and quarters if available
            years = []
            quarters = []
            if ('Meta', 'Năm') in self.stock_data.columns:
                years = self.stock_data[('Meta', 'Năm')].tolist()
                if ('Meta', 'Kỳ') in self.stock_data.columns:
                    quarters = self.stock_data[('Meta', 'Kỳ')].tolist()
            
            # Show data by year for all categories if years data is available
            if years:
                # Find unique years and sort in descending order (newest first)
                unique_years = sorted(set(years), reverse=True)
                recent_years = unique_years[:3]  # Get 3 most recent years
                
                # Find indices of the most recent data for each year
                indices_to_show = []
                for year in recent_years:
                    year_indices = [i for i, y in enumerate(years) if y == year]
                    if year_indices:
                        indices_to_show.append(max(year_indices))
                        
                # Sort indices in reverse chronological order
                indices_to_show.sort(reverse=True)
                
                # Show each indicator with values for recent years
                for indicator in indicators:
                    if (category_name, indicator) in self.stock_data.columns:
                        result += f"\n{indicator}:\n"
                        values = self.stock_data[(category_name, indicator)].tolist()
                        
                        # Show each period's value
                        for i in indices_to_show:
                            if i < len(values):
                                # Format time period based on data type
                                if self.time_period == "yearly" or self.time_period == "year":
                                    time_period = f"{years[i]}"
                                else:
                                    time_period = f"Q{quarters[i]}/{years[i]}" if i < len(quarters) else f"{years[i]}"
                                    
                                if isinstance(values[i], (int, float)):
                                    result += f"{time_period}: {values[i]:.2f}\n"
                                else:
                                    result += f"{time_period}: {values[i]}\n"
            else:
                # Fallback when no year data is available
                for indicator in indicators:
                    if (category_name, indicator) in self.stock_data.columns:
                        values = self.stock_data[(category_name, indicator)].tolist()
                        if values and len(values) > 0:
                            latest_value = values[-1]
                            if isinstance(latest_value, (int, float)):
                                result += f"{indicator}: {latest_value:.2f}\n"
                            else:
                                result += f"{indicator}: {latest_value}\n"
                
            return result
        except Exception as e:
            print(f"Error getting indicators: {e}")
            return f"Lỗi khi truy xuất dữ liệu: {str(e)}"

    def _get_specific_indicator(self, category_name, indicator_name):
        """Get data for a specific indicator"""
        if not self.current_symbol or self.stock_data is None:
            return "Vui lòng nhập lệnh /search [mã cổ phiếu] trước!"
            
        try:
            result = f"📊 {category_name} - {indicator_name} cho {self.current_symbol}:\n\n"
            
            if (category_name, indicator_name) in self.stock_data.columns:
                values = self.stock_data[(category_name, indicator_name)].tolist()
                
                # Get metadata (years/quarters) if available
                years = []
                quarters = []
                if ('Meta', 'Năm') in self.stock_data.columns and ('Meta', 'Kỳ') in self.stock_data.columns:
                    years = self.stock_data[('Meta', 'Năm')].tolist()
                    quarters = self.stock_data[('Meta', 'Kỳ')].tolist()
                
                # Display first 5 values with timeframe if available (changed from last 5)
                first_n = min(5, len(values))
                for i in range(first_n):
                    if years and i < len(years):
                        # Check if we're using yearly or quarterly data
                        if self.time_period == "yearly" or self.time_period == "year":
                            time_period = f"{years[i]}"
                        else:
                            # For quarterly data, show quarter and year
                            time_period = f"Q{quarters[i]}/{years[i]}" if i < len(quarters) else f"{years[i]}"
                            
                        if isinstance(values[i], (int, float)):
                            result += f"{time_period}: {values[i]:.2f}\n"
                        else:
                            result += f"{time_period}: {values[i]}\n"
                    else:
                        if isinstance(values[i], (int, float)):
                            result += f"Giá trị {i+1}: {values[i]:.2f}\n"
                        else:
                            result += f"Giá trị {i+1}: {values[i]}\n"
                
                # Add trend analysis
                if len(values) > 1 and all(isinstance(v, (int, float)) for v in values[-3:]):
                    trend = "tăng" if values[-1] > values[-2] else "giảm"
                    change = abs(values[-1] - values[-2])
                    percent = (change / abs(values[-2])) * 100 if values[-2] != 0 else 0
                    result += f"\nChỉ số đang {trend} {percent:.2f}% so với kỳ trước."
                    
                    if len(values) > 2:
                        prev_change = values[-2] - values[-3]
                        current_change = values[-1] - values[-2]
                        if (prev_change > 0 and current_change > 0) or (prev_change < 0 and current_change < 0):
                            result += f"\nChỉ số duy trì xu hướng {trend} trong 2 kỳ liên tiếp."
                
            else:
                result += "Không có dữ liệu cho chỉ số này."
                
            return result
        except Exception as e:
            print(f"Error getting specific indicator: {e}")
            return f"Lỗi khi truy xuất dữ liệu chỉ số: {str(e)}"

    def get_stock_info(self, symbol):
        """Get stock information for a given symbol"""
        try:
            # Initialize current symbol
            self.current_symbol = symbol
            
            # First try to load existing data
            existing_data = self.load_financial_data(symbol, self.time_period)
            
            if existing_data is not None and not existing_data.empty:
                self.stock_data = existing_data
                print(f"Using existing data for {symbol}")
            else:
                # If no existing data, fetch new data
                print(f"Fetching fresh data for {symbol}")
                self.stock_data = self.get_data_info(symbol, self.time_period)
            
            if self.stock_data is None or (isinstance(self.stock_data, pd.DataFrame) and self.stock_data.empty):
                return False, f"Không thể lấy dữ liệu cho {symbol}. Vui lòng thử lại sau."
            
            period_text = "Quý" if self.time_period == "quarter" else "Năm"
            return True, f"Đã tải dữ liệu {period_text} thành công cho {symbol}!\nVui lòng chọn loại chỉ số để xem:"
        except Exception as e:
            print(f"Error getting stock info: {e}")
            return False, f"Lỗi khi tải dữ liệu cho {symbol}: {str(e)}"

    def get_categories_menu(self):
        """Generate menu of available categories"""
        # Get actual categories from the financial data if available
        categories = []
        if self.stock_data is not None and isinstance(self.stock_data.columns, pd.MultiIndex):
            # Extract unique level 0 values (categories) from MultiIndex columns
            categories = [cat for cat in self.stock_data.columns.get_level_values(0).unique() 
                         if cat != "Meta"]  # Exclude Meta category
        
        # Use default categories if no data is available or if they don't have categories
        if not categories:
            categories = list(self.labels.keys())
            if "Meta" in categories:
                categories.remove("Meta")
        
        menu = "Chọn loại chỉ số bạn muốn xem:\n\n"
        for idx, category in enumerate(categories, 1):
            menu += f"{idx}. {category}\n"
        menu += "\nNhập /vnstock_get [số] hoặc /vnstock_get all để xem tất cả chỉ số."
        return menu

    def get_indicators(self, category_idx):
        """Get indicators for a specific category"""
        if not self.current_symbol or self.stock_data is None:
            return "Vui lòng nhập lệnh /search [mã cổ phiếu] trước!"

        try:
            # Check if stock_data has categories
            if isinstance(self.stock_data.columns, pd.MultiIndex):
                # Get all categories except Meta
                categories = [cat for cat in self.stock_data.columns.get_level_values(0).unique() 
                             if cat != "Meta"]
            else:
                # Try to categorize using labels from labels.json
                return f"Dữ liệu tài chính cho {self.current_symbol} không có cấu trúc phù hợp để phân loại."
            
            if not categories:
                return f"Không tìm thấy dữ liệu phân loại cho {self.current_symbol}."
            
            if category_idx == 'all':
                result = f"📊 Tất cả chỉ số cho {self.current_symbol}:\n\n"
                
                # Get years and quarters if available
                years = []
                quarters = []
                if ('Meta', 'Năm') in self.stock_data.columns:
                    years = self.stock_data[('Meta', 'Năm')].tolist()
                    if ('Meta', 'Kỳ') in self.stock_data.columns:
                        quarters = self.stock_data[('Meta', 'Kỳ')].tolist()
                
                # Get indices for the 3 most recent years
                if years:
                    # Find unique years and sort in descending order (newest first)
                    unique_years = sorted(set(years), reverse=True)
                    recent_years = unique_years[:3]  # Get 3 most recent years
                    
                    # Find indices of the most recent data points for each of these years
                    indices_to_show = []
                    for year in recent_years:
                        # Find all indices for this year
                        year_indices = [i for i, y in enumerate(years) if y == year]
                        if year_indices:
                            # For each year, add its most recent quarter
                            indices_to_show.append(max(year_indices))
                    
                    # Sort indices in reverse chronological order (newest to oldest)
                    indices_to_show.sort(reverse=True)
                    
                    for cat in categories:
                        result += f"=== {cat} ===\n"
                        # Get indicators for this category
                        indicators = [col[1] for col in self.stock_data.columns if col[0] == cat]
                        
                        for indicator in indicators:
                            if (cat, indicator) in self.stock_data.columns:
                                values = self.stock_data[(cat, indicator)].tolist()
                                if values and len(values) > 0:
                                    result += f"{indicator}:\n"
                                    
                                    # Display values for the 3 most recent years
                                    for i in indices_to_show:
                                        if i < len(values):
                                            # Format the time period based on data type
                                            if self.time_period == "yearly" or self.time_period == "year":
                                                time_period = f"{years[i]}"
                                            else:
                                                time_period = f"Q{quarters[i]}/{years[i]}" if i < len(quarters) else f"{years[i]}"
                                                
                                            if isinstance(values[i], (int, float)):
                                                result += f"  {time_period}: {values[i]:.2f}\n"
                                            else:
                                                result += f"  {time_period}: {values[i]}\n"
                                    result += "\n"
                        result += "\n"
                else:
                    # No year data available
                    result += "Không có dữ liệu về năm."
                
                return result

            try:
                # Try to parse as integer index
                category_idx = int(category_idx)
                if category_idx < 1 or category_idx > len(categories):
                    return f"Lựa chọn không hợp lệ! Vui lòng chọn từ 1 đến {len(categories)}"
                
                category_name = categories[category_idx - 1]
                
            except ValueError:
                # If not an integer, try to match by name
                matching_categories = [cat for cat in categories 
                                     if category_idx.lower() in cat.lower()]
                if not matching_categories:
                    return "Không tìm thấy chỉ tiêu phù hợp. Vui lòng thử lại."
                category_name = matching_categories[0]

            # Get results for the selected category
            result = f"📊 {category_name} cho {self.current_symbol}:\n\n"
            
            # Get indicators for this category
            indicators = [col[1] for col in self.stock_data.columns if col[0] == category_name]
            
            for indicator in indicators:
                if (category_name, indicator) in self.stock_data.columns:
                    values = self.stock_data[(category_name, indicator)].tolist()
                    if values and len(values) > 0:
                        latest_value = values[-1]  # Get most recent value
                        if isinstance(latest_value, (int, float)):
                            result += f"{indicator}: {latest_value:.2f}\n"
                        else:
                            result += f"{indicator}: {latest_value}\n"
            
            return result

        except Exception as e:
            print(f"Error getting indicators: {e}")
            return f"Lỗi khi truy xuất dữ liệu: {str(e)}"

    async def vnstock_help_command(self, update: Update, context: CallbackContext):
        """Handle /vnstock_help command"""
        help_text = self.get_help()
        await update.message.reply_text(help_text)

    def get_help(self):
        """Return a help message"""
        return (
            "Hướng dẫn sử dụng tìm kiếm chứng khoán:\n\n"
            "1. Sử dụng lệnh /search [mã cổ phiếu] để bắt đầu.\n"
            "2. Chọn loại chỉ số tài chính hoặc thông tin công ty để xem.\n"
            "3. Sử dụng các nút tương tác để điều hướng và xem thêm thông tin.\n"
            "4. Sử dụng lệnh /vnstock_get [chỉ tiêu] để lấy dữ liệu tài chính cụ thể.\n"
            "5. Sử dụng lệnh /search_chart để xem biểu đồ giá cổ phiếu.\n"
            "6. Sử dụng lệnh /search_help để xem hướng dẫn sử dụng.\n"
        )
