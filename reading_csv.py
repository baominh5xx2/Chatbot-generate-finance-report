import pandas as pd
import io
import os
import matplotlib.pyplot as plt
from datetime import datetime
import re

class CSVReader:
    def __init__(self):
        self.user_csv_data = {}  # Store CSV data by user ID
        self.MAX_HISTORY = 5     # Keep only the last 5 CSV files per user
        self.temp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_csv")
        
        # Create temp folder if it doesn't exist
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
    
    def process_csv(self, file_content, user_id):
        """Process CSV content and return summary information"""
        try:
            # Read CSV from bytes content
            file_stream = io.BytesIO(file_content)
            
            # Try to detect encoding and delimiter
            encoding = 'utf-8'  # Default encoding
            try:
                # Try to read with utf-8 first
                df = pd.read_csv(file_stream, encoding=encoding)
            except UnicodeDecodeError:
                # If utf-8 fails, try with latin1
                file_stream.seek(0)  # Reset file pointer
                encoding = 'latin1'
                df = pd.read_csv(file_stream, encoding=encoding)
            except pd.errors.ParserError:
                # If comma delimiter fails, try with semicolon
                file_stream.seek(0)  # Reset file pointer
                df = pd.read_csv(file_stream, encoding=encoding, sep=';')
            
            # Generate a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_{user_id}_{timestamp}.csv"
            filepath = os.path.join(self.temp_folder, filename)
            
            # Save the file to temp folder
            df.to_csv(filepath, index=False)
            
            # Store in user history
            if user_id not in self.user_csv_data:
                self.user_csv_data[user_id] = []
            
            # Add to user's data with metadata
            file_info = {
                "filename": filename,
                "filepath": filepath,
                "timestamp": timestamp,
                "columns": list(df.columns),
                "shape": df.shape,
                "preview": df.head(5).to_dict(),
                "dataframe": df  # Store the actual dataframe
            }
            
            self.user_csv_data[user_id].append(file_info)
            
            # Trim history if needed
            if len(self.user_csv_data[user_id]) > self.MAX_HISTORY:
                old_data = self.user_csv_data[user_id].pop(0)
                # Remove old file
                if os.path.exists(old_data["filepath"]):
                    os.remove(old_data["filepath"])
            
            # Create summary
            summary = self._generate_summary(df)
            
            return {
                "success": True,
                "filename": filename,
                "summary": summary,
                "columns": list(df.columns),
                "rows": df.shape[0],
                "dataframe": df
            }
            
        except Exception as e:
            error_msg = f"Lỗi khi xử lý file CSV: {str(e)}"
            print(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _generate_summary(self, df):
        """Generate summary statistics and information about the CSV data"""
        summary = []
        
        # Basic info
        summary.append(f"👥 Số dòng: {df.shape[0]}")
        summary.append(f"📊 Số cột: {df.shape[1]}")
        summary.append(f"📋 Tên các cột: {', '.join(df.columns.tolist())}")
        
        # Identify numeric columns for statistics
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        if numeric_cols:
            summary.append("\n📈 Thống kê các cột số:")
            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                stats = df[col].describe()
                summary.append(f"  • {col}: Min={stats['min']:.2f}, Max={stats['max']:.2f}, Trung bình={stats['mean']:.2f}")
        
        # Identify potential date columns
        date_pattern = re.compile(r'date|time|ngay|thang|nam', re.IGNORECASE)
        potential_date_cols = [col for col in df.columns if date_pattern.search(col)]
        if potential_date_cols:
            summary.append("\n📅 Cột có thể chứa ngày tháng: " + ", ".join(potential_date_cols))
        
        # Check for missing values
        missing_data = df.isnull().sum()
        cols_with_missing = missing_data[missing_data > 0]
        if not cols_with_missing.empty:
            summary.append("\n⚠️ Dữ liệu thiếu:")
            for col, count in cols_with_missing.items():
                summary.append(f"  • {col}: {count} giá trị thiếu")
        else:
            summary.append("\n✅ Không có giá trị thiếu trong dữ liệu")
            
        return "\n".join(summary)
    
    def get_csv_preview(self, user_id):
        """Get a preview of the most recent CSV file for a user"""
        if user_id not in self.user_csv_data or not self.user_csv_data[user_id]:
            return "Không có dữ liệu CSV nào được lưu trữ."
        
        # Get most recent file
        recent_file = self.user_csv_data[user_id][-1]
        df = recent_file["dataframe"]
        
        # Create a string representation of the first few rows
        preview = df.head(5).to_string()
        return f"Xem trước {recent_file['filename']}:\n```\n{preview}\n```"
    
    def get_column_info(self, user_id, column_name=None):
        """Get information about a specific column or all columns"""
        if user_id not in self.user_csv_data or not self.user_csv_data[user_id]:
            return "Không có dữ liệu CSV nào được lưu trữ."
        
        # Get most recent file
        recent_file = self.user_csv_data[user_id][-1]
        df = recent_file["dataframe"]
        
        if column_name:
            if column_name not in df.columns:
                return f"Không tìm thấy cột '{column_name}' trong dữ liệu."
            
            # Get info about specific column
            col_data = df[column_name]
            data_type = col_data.dtype
            
            info = [f"Thông tin về cột '{column_name}':"]
            info.append(f"• Kiểu dữ liệu: {data_type}")
            info.append(f"• Số giá trị duy nhất: {col_data.nunique()}")
            
            # For numeric columns
            if pd.api.types.is_numeric_dtype(col_data):
                stats = col_data.describe()
                info.append(f"• Giá trị nhỏ nhất: {stats['min']}")
                info.append(f"• Giá trị lớn nhất: {stats['max']}")
                info.append(f"• Giá trị trung bình: {stats['mean']:.2f}")
                info.append(f"• Độ lệch chuẩn: {stats['std']:.2f}")
            
            # For string/object columns
            elif pd.api.types.is_string_dtype(col_data) or pd.api.types.is_object_dtype(col_data):
                # Get most common values
                most_common = col_data.value_counts().head(3)
                if not most_common.empty:
                    info.append("• Các giá trị phổ biến nhất:")
                    for value, count in most_common.items():
                        info.append(f"  - {value}: {count} lần")
            
            # Check for missing values
            missing = col_data.isnull().sum()
            if missing > 0:
                info.append(f"• Số giá trị thiếu: {missing} ({missing/len(col_data)*100:.1f}%)")
            else:
                info.append("• Không có giá trị thiếu")
                
            return "\n".join(info)
        else:
            # Get quick summary of all columns
            info = ["Thông tin tất cả các cột:"]
            for col in df.columns:
                data_type = df[col].dtype
                missing = df[col].isnull().sum()
                unique = df[col].nunique()
                info.append(f"• {col}: {data_type}, {unique} giá trị duy nhất, {missing} giá trị thiếu")
            
            return "\n".join(info)
    
    def generate_quick_plot(self, user_id, plot_description):
        """Generate a quick plot based on the latest CSV data"""
        if user_id not in self.user_csv_data or not self.user_csv_data[user_id]:
            return None, "Không có dữ liệu CSV nào được lưu trữ."
        
        # Get most recent file
        recent_file = self.user_csv_data[user_id][-1]
        df = recent_file["dataframe"]
        
        try:
            plt.figure(figsize=(10, 6))
            
            # Check what kind of plot is requested
            plot_description = plot_description.lower()
            
            # Find column names mentioned in the description
            mentioned_cols = [col for col in df.columns if col.lower() in plot_description]
            
            # If no specific columns are mentioned, use the first numeric columns
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            
            if not mentioned_cols and numeric_cols:
                if "pie" in plot_description or "tròn" in plot_description:
                    # For pie charts, use the first categorical column and its counts
                    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
                    if cat_cols:
                        counts = df[cat_cols[0]].value_counts()
                        counts.plot(kind='pie', autopct='%1.1f%%')
                        plt.title(f"Biểu đồ tròn {cat_cols[0]}")
                    else:
                        # If no categorical columns, use the first numeric column binned into categories
                        df[numeric_cols[0]].plot(kind='hist', bins=5)
                        plt.title(f"Biểu đồ phân phối {numeric_cols[0]}")
                
                elif "bar" in plot_description or "cột" in plot_description:
                    # For bar charts, use the first two columns if possible
                    if len(numeric_cols) >= 2:
                        df[numeric_cols[0]][:20].plot(kind='bar')
                        plt.title(f"Biểu đồ cột {numeric_cols[0]}")
                    else:
                        df[numeric_cols[0]][:20].plot(kind='bar')
                        plt.title(f"Biểu đồ cột {numeric_cols[0]}")
                
                elif "scatter" in plot_description or "điểm" in plot_description:
                    # For scatter plots, use first two numeric columns
                    if len(numeric_cols) >= 2:
                        plt.scatter(df[numeric_cols[0]], df[numeric_cols[1]])
                        plt.xlabel(numeric_cols[0])
                        plt.ylabel(numeric_cols[1])
                        plt.title(f"Biểu đồ điểm {numeric_cols[0]} vs {numeric_cols[1]}")
                    else:
                        plt.scatter(range(len(df)), df[numeric_cols[0]])
                        plt.xlabel("Chỉ mục")
                        plt.ylabel(numeric_cols[0])
                        plt.title(f"Biểu đồ điểm {numeric_cols[0]}")
                
                else:  # Default to line chart
                    df[numeric_cols[0]][:50].plot(kind='line')
                    plt.title(f"Biểu đồ đường {numeric_cols[0]}")
            
            else:  # Use mentioned columns
                col = mentioned_cols[0]  # Use the first mentioned column
                
                if pd.api.types.is_numeric_dtype(df[col]):
                    if "pie" in plot_description or "tròn" in plot_description:
                        # For numeric column in pie chart, we need to bin it
                        df[col].value_counts(bins=5).plot(kind='pie', autopct='%1.1f%%')
                        plt.title(f"Biểu đồ tròn {col} (đã nhóm)")
                    
                    elif "bar" in plot_description or "cột" in plot_description:
                        df[col][:20].plot(kind='bar')
                        plt.title(f"Biểu đồ cột {col}")
                    
                    elif "hist" in plot_description or "phân phối" in plot_description:
                        df[col].plot(kind='hist', bins=10)
                        plt.title(f"Biểu đồ phân phối {col}")
                    
                    else:  # Default to line chart
                        df[col][:50].plot(kind='line')
                        plt.title(f"Biểu đồ đường {col}")
                
                else:  # Categorical column
                    counts = df[col].value_counts()
                    if "pie" in plot_description or "tròn" in plot_description:
                        counts.plot(kind='pie', autopct='%1.1f%%')
                        plt.title(f"Biểu đồ tròn {col}")
                    else:
                        counts.plot(kind='bar')
                        plt.title(f"Biểu đồ cột {col}")
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=300)
            buffer.seek(0)
            plt.close()
            
            return buffer, "Thành công"
            
        except Exception as e:
            plt.close()
            error_msg = f"Lỗi khi tạo biểu đồ: {str(e)}"
            print(error_msg)
            return None, error_msg

    def prepare_csv_analysis_data(self, user_id):
        """Prepare CSV data for PDF analysis"""
        if user_id not in self.user_csv_data or not self.user_csv_data[user_id]:
            return None, "Không tìm thấy file CSV nào. Vui lòng tải lên trước khi yêu cầu phân tích."
        
        # Get the most recent CSV file
        recent_file = self.user_csv_data[user_id][-1]
        df = recent_file["dataframe"]
        
        # Generate basic statistics and insights
        analysis_data = {
            "filename": recent_file["filename"],
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns),
            "summary": self._generate_summary(df),
            "head": df.head(10).to_html(),
            "describe": df.describe().to_html(),
            "missing_values": df.isnull().sum().to_dict(),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
        }
        
        # Generate additional insights based on data types
        insights = []
        
        # Analyze numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        if numeric_cols:
            insights.append("### Phân tích cột số:")
            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns for brevity
                col_insights = []
                # Basic statistics
                stats = df[col].describe()
                col_insights.append(f"- **{col}**: Min={stats['min']:.2f}, Max={stats['max']:.2f}, Mean={stats['mean']:.2f}, Std={stats['std']:.2f}")
                
                # Check for potential outliers using IQR method
                Q1 = stats['25%']
                Q3 = stats['75%']
                IQR = Q3 - Q1
                outlier_count = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
                if outlier_count > 0:
                    col_insights.append(f"  - Có {outlier_count} giá trị có thể là ngoại lai (~{outlier_count/len(df)*100:.1f}%)")
                
                # Check distribution
                skew = df[col].skew()
                if abs(skew) > 1:
                    skew_direction = "phải" if skew > 0 else "trái"
                    col_insights.append(f"  - Phân phối lệch {skew_direction} (skewness={skew:.2f})")
                
                insights.extend(col_insights)
        
        # Analyze categorical columns
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        if cat_cols:
            insights.append("\n### Phân tích cột phân loại:")
            for col in cat_cols[:5]:  # Limit to first 5 categorical columns
                value_counts = df[col].value_counts()
                top_categories = value_counts.head(3).to_dict()
                unique_count = df[col].nunique()
                insights.append(f"- **{col}**: {unique_count} giá trị duy nhất")
                
                # Common categories
                categories_str = ", ".join([f"{k} ({v})" for k, v in top_categories.items()])
                insights.append(f"  - Các giá trị phổ biến nhất: {categories_str}")
                
                # Check for high cardinality
                if unique_count > df.shape[0] * 0.5 and unique_count > 10:
                    insights.append(f"  - Cột này có độ phân tán cao, có thể là ID hoặc dữ liệu duy nhất")
        
        # Look for potential date columns
        date_pattern = re.compile(r'date|time|ngay|thang|nam', re.IGNORECASE)
        potential_date_cols = [col for col in df.columns if date_pattern.search(col)]
        if potential_date_cols:
            insights.append("\n### Phân tích cột thời gian:")
            for col in potential_date_cols:
                insights.append(f"- **{col}** có thể chứa thông tin thời gian")
        
        # Add insights about missing values
        missing_data = df.isnull().sum()
        cols_with_missing = missing_data[missing_data > 0]
        if not cols_with_missing.empty:
            insights.append("\n### Phân tích dữ liệu thiếu:")
            for col, count in cols_with_missing.items():
                pct = count / len(df) * 100
                insights.append(f"- **{col}**: {count} giá trị thiếu ({pct:.2f}%)")
                if pct > 20:
                    insights.append(f"  - Cột này có tỷ lệ thiếu cao, cần xử lý thận trọng")
        
        # Add insights to the analysis data
        analysis_data["insights"] = "\n".join(insights)
        
        return analysis_data, "success"
