# Point Audit

Ứng dụng Python dùng để kiểm tra và đối soát điểm thi đua từ một sheet Excel. Hiện dự án đã có khung chạy, domain contract, lớp đọc workbook một sheet ở chế độ bất biến và bộ tách sự kiện Minh chứng thuần Python. Semantic parser, áp dụng quy tắc và tính điểm cuối chưa được triển khai.

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

## Đọc workbook một sheet

```python
from point_audit.ingestion import WorkbookReader

result = WorkbookReader().read("duong-dan/workbook.xlsx")
print(result.header_row, len(result.students), result.scoring_period)
```

Reader tự tìm header, chỉ giữ dòng học sinh, dừng ở vùng tổng hợp/footer, đọc công thức cùng cached value nếu workbook có lưu và kiểm tra hash trước/sau. Reader không gọi `save` và không thay đổi file nguồn.

## Tách sự kiện Minh chứng

```python
from point_audit.parsing import segment_evidence

result = segment_evidence("+2,5 trực nhật tốt; +1 giúp lớp")
for segment in result.segments:
    print(segment.raw_text, segment.source_span, segment.delimiter_after)
```

Segmenter giữ chính xác span và delimiter trong chuỗi nguồn, không tách dấu phẩy thập phân,
bảo vệ URL/ngày/delta trong ngoặc và trả `SEGMENTATION_AMBIGUOUS` khi có nhiều cách tách hợp lý.
Nội dung chưa hiểu không bị loại bỏ và không có lời gọi AI trong bước này.

## Chạy giao diện Streamlit

```bash
streamlit run app.py
```

Giao diện hiện chỉ là trang khởi động và hiển thị trạng thái AI; ingestion mới được cung cấp qua Python API, chưa nối vào giao diện.

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
