# AGENTS.md

## Mục tiêu dự án

Xây dựng ứng dụng Python đọc một workbook Excel đầu vào có đúng một sheet tổng hợp điểm thi đua, tách các sự kiện trong cột `Minh chứng`, áp dụng bảng quy tắc một cách xác định, tính lại điểm và tạo báo cáo đối soát có thể kiểm toán.

## Nguyên tắc bất biến

1. Không bao giờ ghi đè hoặc chỉnh sửa workbook nguồn.
2. AI chỉ được hỗ trợ tách sự kiện và diễn giải văn bản. AI không được áp dụng quy tắc, cộng điểm, trừ điểm, chọn giá trị khi có xung đột hoặc quyết định kết quả cuối.
3. Python là nguồn chân lý duy nhất cho:
   - chuẩn hóa dữ liệu có tính xác định;
   - khớp và áp dụng bảng quy tắc;
   - phát hiện xung đột;
   - tính tổng và đối soát;
   - kiểm tra schema và ràng buộc dữ liệu.
4. Luôn giữ riêng ba nguồn điểm:
   - `declared_delta`: điểm có trong văn bản Minh chứng;
   - `expected_delta`: điểm suy ra từ bảng quy tắc;
   - `final_delta`: điểm được sử dụng sau khi tự động chấp nhận an toàn hoặc người dùng duyệt.
5. Nếu `declared_delta != expected_delta` khi cả hai cùng tồn tại, phải thêm cảnh báo `RULE_CONFLICT`, đặt trạng thái chờ duyệt và không tự điền `final_delta`.
6. Không tự loại bỏ nội dung lặp. Chỉ đánh dấu `DUPLICATE_CANDIDATE` để người dùng duyệt.
7. Mọi biến đổi phải truy ngược được về workbook, sheet, hàng, cột, ô và văn bản gốc.

## Phạm vi hiện tại

Repository đang ở giai đoạn đặc tả. Chưa được viết code sản phẩm cho tới khi các câu hỏi chặn trong `docs/ASSUMPTIONS.md` được xác nhận và milestone tài liệu trong `docs/ROADMAP.md` hoàn tất.

Các tài liệu chuẩn:

- `docs/SPEC.md`: yêu cầu chức năng và tiêu chí nghiệm thu.
- `docs/ARCHITECTURE.md`: kiến trúc, luồng xử lý và ranh giới AI/Python.
- `docs/DATA_CONTRACT.md`: schema, enum, công thức và ràng buộc.
- `docs/ROADMAP.md`: thứ tự triển khai.
- `docs/ASSUMPTIONS.md`: giả định, quyết định tạm thời và câu hỏi mở.
- `PROJECT_STATE.md`: trạng thái bàn giao mới nhất.

Nếu tài liệu mâu thuẫn, ưu tiên theo thứ tự: yêu cầu người dùng mới nhất → `docs/DATA_CONTRACT.md` đối với dữ liệu → `docs/SPEC.md` đối với hành vi → `docs/ARCHITECTURE.md` đối với thiết kế nội bộ.

## Quy tắc cho lần triển khai sau

- Trước khi sửa, đọc toàn bộ các tài liệu chuẩn ở trên.
- Không suy đoán bảng điểm nghiệp vụ. Bảng quy tắc phải được người dùng cung cấp/xác nhận, có phiên bản và có kiểm thử.
- Dùng `Decimal` cho điểm; không dùng số thực nhị phân cho phép tính nghiệp vụ.
- Phân biệt giá trị thiếu với số `0`.
- Mỗi cảnh báo dùng mã máy đọc được và thông điệp tiếng Việt.
- Mọi đầu ra phải được ghi vào đường dẫn mới; nếu tên đã tồn tại, yêu cầu xác nhận hoặc sinh tên không đụng độ theo chính sách đã duyệt.
- Mọi tích hợp AI phải có schema đầu ra chặt, timeout, retry hữu hạn và đường lui không-AI. Kết quả AI không hợp lệ phải chuyển sang duyệt thủ công, không làm hỏng toàn bộ lần chạy.
- Viết kiểm thử từ dữ liệu đã ẩn danh; không commit workbook chứa dữ liệu cá nhân thật.
- Không log khóa API, toàn bộ workbook hoặc dữ liệu cá nhân không cần thiết.
- Các thay đổi schema phải cập nhật `docs/DATA_CONTRACT.md`, migration/version và fixture kiểm thử liên quan trong cùng thay đổi.

## Definition of Done cho một tính năng

- Có tiêu chí nghiệm thu và kiểm thử tương ứng.
- Không vi phạm tính bất biến của file nguồn.
- Kết quả có provenance đầy đủ.
- Các ca mơ hồ/xung đột đi vào hàng đợi duyệt, không bị tự quyết.
- Tài liệu và `PROJECT_STATE.md` được cập nhật.

