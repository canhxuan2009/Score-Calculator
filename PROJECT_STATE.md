# PROJECT_STATE.md

## Trạng thái hiện tại

- Giai đoạn: `Milestone 1 — project skeleton / in progress`.
- Repository ban đầu chỉ có tài liệu đặc tả; skeleton Python 3.12 hiện đã được tạo.
- Logic nghiệp vụ phân tích Minh chứng, áp dụng quy tắc và tính điểm: chưa triển khai.
- Tài liệu nền tảng: đã thiết kế trong bộ tài liệu này.
- Ngày cập nhật: 2026-08-06.

## Khung kỹ thuật hiện có

- Package theo `src` layout tại `src/point_audit` cùng các ranh giới module đã nêu trong kiến trúc.
- CLI `python -m point_audit --help` và console script `point-audit`.
- Streamlit entry point tại `app.py`; giao diện hiện chỉ là trang khởi động.
- Cấu hình Pydantic v2 đọc từ biến môi trường; `AI_ENABLED` mặc định là `false`.
- OpenAI SDK là optional dependency, không cần để import package, chạy CLI hoặc khởi động UI.
- Tooling và cấu hình cho pytest, Ruff và mypy strict trong `pyproject.toml`.
- Smoke tests xác minh package import và CLI help hoạt động.

## Kiểm tra gần nhất

Chạy trong Python 3.12.13 với môi trường `.venv` cục bộ:

- `pytest`: đạt, `3 passed`.
- `ruff check .`: đạt, không có lỗi.
- `mypy src/point_audit app.py`: đạt, 15 source files không có lỗi.
- `python -m point_audit --help`: exit code 0.
- Streamlit `AppTest` khi `AI_ENABLED=false` và không có API key: đạt.

## Phạm vi đã chốt ở mức đặc tả

- Đầu vào là một file Excel có đúng một sheet nghiệp vụ.
- Một hàng dữ liệu tương ứng một người; các vùng tiêu đề, tổng hợp, thành tích lớp và GVCN không phải hàng người.
- Cột `Minh chứng` có thể chứa nhiều sự kiện nhập tự do, định dạng không ổn định.
- Ba nguồn điểm `declared_delta`, `expected_delta`, `final_delta` luôn độc lập.
- `RULE_CONFLICT` bắt buộc duyệt thủ công; không tự chọn điểm khai báo hay điểm theo quy tắc.
- File nguồn bất biến.
- AI chỉ tách/hiểu văn bản; Python áp quy tắc, tính toán và đối soát.

## Các quyết định thiết kế chính

1. Sự kiện là đơn vị kiểm toán nhỏ nhất và luôn giữ tọa độ nguồn cùng văn bản nguyên bản.
2. Tách sự kiện theo hai tầng: heuristic xác định trước, AI có schema sau; trường hợp không chắc chắn đi vào hàng đợi duyệt.
3. Bảng quy tắc là dữ liệu cấu hình có phiên bản, không được chôn trong prompt AI.
4. Điểm được lưu và tính bằng số thập phân chính xác.
5. Báo cáo phân biệt `provisional` (có mục chưa duyệt) và `finalized` (không còn mục chặn).
6. Dữ liệu gốc và các cột người dùng tự tính chỉ được đọc để đối soát.

## Chưa được quyết định — chặn triển khai nghiệp vụ

- Bảng quy tắc điểm chính thức và thứ tự ưu tiên khi nhiều quy tắc cùng khớp.
- Chính sách tự động chấp nhận khi chỉ có `declared_delta` hoặc chỉ có `expected_delta`.
- Ngưỡng sai số khi so sánh điểm và quy tắc làm tròn.
- Cách suy ra năm cho ngày chỉ có ngày/tháng.
- Định dạng đầu ra mong muốn: workbook báo cáo, JSON/CSV, giao diện duyệt hay kết hợp.
- Môi trường chạy và nhà cung cấp AI; yêu cầu bảo mật dữ liệu cá nhân.

Chi tiết và đề xuất mặc định nằm trong `docs/ASSUMPTIONS.md`.

## Bước tiếp theo được khuyến nghị

1. Người dùng xác nhận các câu hỏi chặn trong `docs/ASSUMPTIONS.md`.
2. Bổ sung bảng quy tắc phiên bản đầu tiên cùng ví dụ đúng/sai đã ẩn danh.
3. Chốt hợp đồng đầu ra và luồng duyệt.
4. Tiếp tục Milestone 1 bằng domain schema, input guard và fixture bất biến nguồn sau khi dữ liệu mẫu/phạm vi tương ứng được xác nhận.
