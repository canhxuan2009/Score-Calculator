# Point Audit

Khung ứng dụng Python dùng để kiểm tra và đối soát điểm thi đua từ một sheet Excel. Giai đoạn hiện tại chỉ thiết lập cấu trúc, cấu hình, CLI, giao diện Streamlit tối thiểu và công cụ kiểm tra chất lượng; chưa có logic phân tích Minh chứng hoặc tính điểm.

## Yêu cầu

- Python 3.12

## Cài đặt cho phát triển

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Trên Windows, kích hoạt môi trường bằng `.venv\Scripts\activate`.

OpenAI SDK là tùy chọn và không cần để khởi động ứng dụng:

```bash
python -m pip install -e ".[ai,dev]"
```

Không ghi API key vào mã nguồn. `.env.example` là mẫu tham khảo; skeleton hiện đọc `AI_ENABLED` và `OPENAI_API_KEY` trực tiếp từ môi trường chạy, không tự động nạp file `.env`. File `.env` cục bộ không được commit.

## Chạy CLI

Sau khi cài package:

```bash
python -m point_audit --help
```

## Chạy giao diện Streamlit

```bash
streamlit run app.py
```

Giao diện hiện chỉ là trang khởi động và hiển thị trạng thái AI; chưa xử lý workbook.

## Kiểm tra chất lượng

```bash
pytest
ruff check .
mypy src/point_audit app.py
```

## Nguyên tắc dữ liệu

- Không chỉnh sửa hoặc ghi đè workbook nguồn.
- Không commit workbook chứa dữ liệu cá nhân thật.
- AI mặc định tắt và không tham gia áp dụng quy tắc hay tính điểm.
