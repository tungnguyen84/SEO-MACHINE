# OpenSEO + SEOMachine + Claude-SEO: Hệ Thống Affiliate Website Tự Động Hóa

Hệ thống kết hợp sức mạnh của 3 dự án mã nguồn mở hàng đầu:
1. **OpenSEO**: Bộ não dữ liệu (Nghiên cứu từ khóa thương mại & Rank tracking).
2. **SEOMachine**: Nhà máy nội dung (Cấu trúc bài viết chuẩn CRO, so sánh, review chi tiết, gắn thẻ affiliate).
3. **Claude-SEO**: Cổng kiểm định chất lượng (Tiêu chuẩn E-E-A-T chống thuật toán phạt Thin Affiliate của Google, sinh Schema.org Rich Snippets JSON-LD và tối ưu tìm kiếm AI/GEO).

---

## 🛠️ Cài đặt & Chuẩn bị

### 1. Cài đặt thư viện Python
```bash
pip install -r requirements.txt
```

### 2. Thiết lập cấu hình file `.env`
Sao chép `.env.example` thành `.env` và điền thông tin:
```bash
cp .env.example .env
```

Các thông tin quan trọng cần điền:
- **`WP_URL`**: Đường dẫn website WordPress của bạn (ví dụ: `https://mywebsite.com`).
- **`WP_USERNAME`**: Tên tài khoản quản trị WordPress.
- **`WP_APP_PASSWORD`**: Mật khẩu ứng dụng (Application Password) của WordPress.
  > **Cách lấy Application Password trong WordPress:**
  > 1. Đăng nhập WordPress Admin.
  > 2. Vào **Users (Thành viên)** -> **Profile (Hồ sơ của bạn)**.
  > 3. Kéo xuống mục **Application Passwords (Mật khẩu ứng dụng)**.
  > 4. Nhập tên (ví dụ: `OpenSEO Bot`) và bấm **Add New Application Password**.
  > 5. Copy chuỗi mật khẩu được sinh ra và dán vào `WP_APP_PASSWORD`.
- **`AMAZON_TAG`**: Store ID / Associate Tag của bạn (ví dụ: `yourstore-20`).
- **`LLM_PROVIDER` & API KEY**: Hỗ trợ `gemini`, `anthropic`, hoặc `openai`.

---

## 🖥️ Giao Diện Web Dashboard Trực Quan (Web UI)

Hệ thống đã tích hợp sẵn một **Web Dashboard** hiện đại, trực quan, cho phép bạn thao tác toàn bộ chức năng bằng chuột mà không cần nhớ câu lệnh:
```bash
python main.py ui
```
Sau đó mở trình duyệt tại: **`http://localhost:8000`**

### Các tính năng trên Giao diện Web:
1. **🛒 Phân Tích Sản Phẩm (Product Analyzer)**: Nhập URL hoặc ASIN Amazon -> Xem ảnh, giá, link aff -> Bảng phân tích từ khóa, đo Volume, độ cạnh tranh và điểm cơ hội -> 1 click chuyển sang viết bài.
2. **🔍 Nghiên Cứu Từ Khóa Long-tail**: Quét Google & Amazon Autocomplete theo seed keyword -> Lọc ý định mua hàng.
3. **✍️ Sinh Bài Viết Tự Động (Pipeline)**: Điền từ khóa, ASIN -> Xem tiến trình xử lý thời gian thực, điểm audit E-E-A-T -> Xem trước bài viết hoàn chỉnh (Live Preview) trong iframe.
4. **⚙️ Cấu Hình Hệ Thống**: Xem và cập nhật WordPress URL, Application Password, Amazon Tag, API Key trực tiếp trên giao diện web.

---

## 🚀 Các lệnh dòng lệnh CLI (Nếu muốn chạy tự động/Cron)

### 1. Nghiên cứu từ khóa đuôi dài (Long-tail Buyer Intent)
Tự động quét gợi ý từ khóa có tỷ lệ chuyển đổi mua hàng cao nhất từ **Google & Amazon Autocomplete** (miễn phí 100%, không tốn API key):
```bash
# Tìm 20 từ khóa đuôi dài tốt nhất và xuất ra file CSV:
python main.py find-keywords "office chair" --limit 20 --output my_topics.csv

# Tìm từ khóa cho ngách đồ công nghệ, đồ gia dụng:
python main.py find-keywords "air purifier" --limit 30
```

### 2. Phân tích ngược từ URL Amazon (Reverse Keyword & Opportunity Scoring)
Chỉ cần đưa vào 1 link sản phẩm Amazon hoặc mã ASIN, hệ thống sẽ:
1. Nhận diện tên Brand, Model và Ngách sản phẩm.
2. Tự động sinh danh sách từ khóa chính + từ khóa đuôi dài (Review, so sánh, đối tượng sử dụng).
3. Đo lường **Lượng tìm kiếm (Search Volume)** & **Độ cạnh tranh (Competition)**.
4. Chấm **Điểm cơ hội (Opportunity Score / 100)** và **Đề xuất từ khóa tốt nhất để viết bài** (dễ lên Top nhất và tỷ lệ chuyển đổi ra đơn cao nhất):
```bash
python main.py analyze-product "https://www.amazon.com/dp/B08N5WRWNW"
# hoặc dùng trực tiếp mã ASIN:
python main.py analyze-product B08N5WRWNW
```

### 3. Kiểm tra kết nối tới WordPress
Kiểm tra xem hệ thống đã kết nối và đăng nhập thành công vào WordPress chưa:
```bash
python main.py test-wp
```

### 3. Kiểm tra cào sản phẩm & gắn link Affiliate Amazon
Thử nghiệm lấy dữ liệu một sản phẩm Amazon qua ASIN:
```bash
python main.py test-amazon B08N5WRWNW
```

### 4. Tự động sinh bài viết và đăng lên WordPress
Tự động lấy thông tin từ các ASIN, sinh bài viết chuẩn CRO, kiểm định E-E-A-T, chèn Schema JSON-LD và đăng lên WordPress:
```bash
# Đăng dưới dạng bài nháp (Draft) để xem lại:
python main.py generate --keyword "ergonomic office chairs" --asins "B08N5WRWNW,B07J281VDD,B07L4J4L1G" --category "Office Furniture"

# Đăng công khai ngay lập tức (Publish):
python main.py generate --keyword "ergonomic office chairs" --asins "B08N5WRWNW,B07J281VDD,B07L4J4L1G" --category "Office Furniture" --publish

# Chạy thử nghiệm xuất file HTML cục bộ (không đăng lên WP):
python main.py generate --keyword "ergonomic office chairs" --asins "B08N5WRWNW,B07J281VDD" --dry-run
```

### 5. Chạy tự động hàng loạt từ danh sách file CSV:
```bash
python main.py batch --file topics.example.csv
```

---

## 📁 Cấu trúc thư mục

```text
d:\App\openseo/
├── core/
│   ├── config.py              # Đọc cấu hình từ .env
│   └── __init__.py
├── connectors/
│   ├── wordpress.py           # Kết nối WordPress REST API, upload ảnh, đăng bài
│   ├── amazon.py              # Trích xuất giá, ảnh, tính năng & gắn tag affiliate
│   ├── ebay.py                # Hỗ trợ eBay Partner Network (EPN)
│   └── __init__.py
├── seomachine/
│   ├── context/               # Hướng dẫn văn phong, quy định FTC, CRO
│   ├── writer.py              # Sinh bài viết in-depth review, comparison matrix
│   └── __init__.py
├── claude_seo/
│   ├── schema_generator.py    # Sinh Schema.org ItemList, Product, FAQ JSON-LD
│   ├── eeat_checker.py        # Kiểm toán E-E-A-T, quét từ sáo rỗng AI
│   ├── geo_optimizer.py       # Tối ưu cho AI search & llms.txt
│   └── __init__.py
├── pipeline/
│   ├── orchestrator.py        # Điều phối luồng làm việc tự động toàn diện
│   └── __init__.py
├── main.py                    # Giao diện dòng lệnh CLI chính
├── requirements.txt           # Danh sách thư viện Python
└── .env.example               # Mẫu cấu hình môi trường
```
