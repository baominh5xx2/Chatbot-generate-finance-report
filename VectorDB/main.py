from sentence_transformers import SentenceTransformer
import torch
import pandas as pd
from pinecone import Pinecone
from tqdm import tqdm
import time

# ✅ KIỂM TRA VÀ CHẠY MÔ HÌNH TRÊN GPU (NẾU CÓ)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✅ Đang chạy trên: {device.upper()}")

# ✅ CẤU HÌNH BERT (Chạy trên GPU nếu có)
bert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)

# ✅ KẾT NỐI PINECONE
PINECONE_API_KEY = "pcsk_YgDiM_RwKYbFr23sS7RSEPjAwaQhf26BXzrSgUbeXdCeGX3mzusYUfgT3P58sQdp2uwMZ"
pc = Pinecone(api_key=PINECONE_API_KEY)

# ✅ KẾT NỐI HOẶC TẠO INDEX TRONG PINECONE
index_name = "chatbot-ed"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,  # Kích thước vector của "all-MiniLM-L6-v2" là 384
        metric="cosine"
    )
index = pc.Index(index_name)
print(f"✅ Đã kết nối tới index: {index_name}")
# ✅ ĐỌC FILE CSV
csv_path = "2022-Vietnam1.csv"
df = pd.read_csv(csv_path, encoding="utf-8-sig")

# ✅ XỬ LÝ DỮ LIỆU: Xóa cột trống, đặt lại tiêu đề
column_headers = df.iloc[0].tolist()  # Lấy tiêu đề từ hàng đầu tiên
df_cleaned = df.iloc[1:].reset_index(drop=True)  # Xóa hàng đầu tiên khỏi dữ liệu chính

# ✅ HÀM CẮT NGẮN VĂN BẢN (nếu quá dài)
def truncate_text(text, max_chars=10000000000000):
    """Giới hạn văn bản không quá max_chars ký tự."""
    return text[:max_chars] + "..." if len(text) > max_chars else text

# ✅ CHIA NHỎ DỮ LIỆU & TẠO EMBEDDINGS
batch_size = 1  # Số dòng gửi mỗi lần
total_rows = len(df_cleaned)
output_file = "embeddings_data.txt"

with open(output_file, "w", encoding="utf-8") as f:
    for i in tqdm(range(0, total_rows, batch_size), desc="🔄 Đang tạo embeddings với BERT trên GPU"):
        batch_vectors = []
        batch = df_cleaned.iloc[i:i+batch_size]

        for idx, row in batch.iterrows():
            # 🚀 Gộp dữ liệu đúng format: "Tên cột: Giá trị"
            text = " | ".join([f"{col_name}: {row.iloc[col_index]}" 
                               for col_index, col_name in enumerate(column_headers)])
            text = text.replace("#####", "MISSING_DATA")
            text = truncate_text(text)

            try:
                # 🚀 Tạo embedding từ BERT (Chạy trên GPU nếu có)
                embedding = bert_model.encode(text, convert_to_tensor=True, device=device).cpu().tolist()

                # 🚀 Lưu vào danh sách với metadata
                batch_vectors.append((str(idx), embedding, {"data": text}))

                # ✅ Ghi vào file txt
                f.write(f"ID: {idx} | Text: {text} | Embedding: {embedding}\n")

            except Exception as e:
                print(f"⚠️ Lỗi xử lý dòng {idx}: {str(e)}")
                continue

        # ✅ Gửi batch vào Pinecone
        if batch_vectors:
            try:
                index.upsert(vectors=batch_vectors)
            except Exception as e:
                print(f"⚠️ Lỗi khi upsert vào Pinecone: {str(e)}")
                continue

        time.sleep(1)

print(f"✅ Đã thêm {total_rows} vector embeddings vào Pinecone thành công!")
print("✅ Dữ liệu đã được lưu vào:", output_file)
print(index.describe_index_stats())
