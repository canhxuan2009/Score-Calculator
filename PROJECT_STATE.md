# PROJECT_STATE.md

## Trạng thái hiện tại

- Giai đoạn: `Specification / pre-implementation`.
- Repository ban đầu: trống.
- Code sản phẩm: chưa có, đúng theo yêu cầu.
- Tài liệu nền tảng: đã thiết kế trong bộ tài liệu này.
- Ngày cập nhật: 2026-08-05.

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
4. Sau đó mới tạo skeleton, fixture và kiểm thử ở Milestone 1 của roadmap.

