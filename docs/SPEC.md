# Đặc tả sản phẩm — Score Calculator

## 1. Mục tiêu

Ứng dụng nhận một workbook Excel có một sheet tổng hợp điểm thi đua, nhận diện đúng vùng dữ liệu người, tách các sự kiện trong cột `Minh chứng`, kiểm tra từng sự kiện theo bảng quy tắc và tính lại các cột điểm để đối soát với số liệu người dùng đã nhập.

Sản phẩm ưu tiên tính kiểm toán và an toàn hơn việc cố tự động hóa mọi trường hợp. Nội dung mơ hồ, xung đột hoặc nghi trùng phải được trình cho người dùng duyệt.

## 2. Ngoài phạm vi phiên bản đầu

- Không chỉnh sửa workbook nguồn.
- Không huấn luyện mô hình AI.
- Không để AI quyết định quy tắc hoặc số điểm cuối.
- Không tự sửa chính tả/nội dung gốc trong dữ liệu nguồn.
- Không tự xóa sự kiện nghi trùng.
- Không xử lý workbook nhiều sheet trong cùng một lần chạy.
- Không xác định hạnh kiểm mới nếu chưa có một bộ quy tắc hạnh kiểm riêng được phê duyệt.

## 3. Đầu vào

### 3.1 Workbook

- Định dạng mục tiêu ban đầu: `.xlsx` hoặc `.xlsm` đọc ở chế độ không ghi.
- Workbook nghiệp vụ phải có đúng một sheet. Nếu có 0 hoặc nhiều hơn 1 sheet, dừng với lỗi có hướng dẫn; không tự chọn sheet.
- Sheet có thể chứa dòng tiêu đề/phụ đề phía trên, dòng trống, ô gộp và các vùng tổng hợp phía dưới.

### 3.2 Các cột tương đương

Ứng dụng phải ánh xạ được các tiêu đề tương đương với:

| Cột chuẩn | Vai trò |
|---|---|
| `TT` | số thứ tự, tín hiệu phụ để nhận diện hàng người |
| `Họ và tên` | định danh hiển thị của người |
| `Ngày sinh` | thông tin người, không phải ngày sự kiện |
| `Tổ` | nhóm/tổ |
| `Điểm gốc` | điểm nền để tính tổng mới |
| `Điểm cộng` | tổng cộng do người dùng nhập, chỉ dùng đối soát |
| `Điểm trừ` | tổng trừ do người dùng nhập, chỉ dùng đối soát |
| `Tổng` | tổng do người dùng nhập, chỉ dùng đối soát |
| `Hạnh kiểm` | dữ liệu tham chiếu |
| `Minh chứng` | văn bản sự kiện cần phân tích |

Ánh xạ dựa trên chuẩn hóa Unicode, khoảng trắng, chữ hoa/thường và danh sách alias có cấu hình. Nếu thiếu cột bắt buộc (`Họ và tên`, `Điểm gốc`, `Minh chứng`) hoặc có nhiều ánh xạ đồng hạng, phải dừng/chờ người dùng xác nhận.

## 4. Nhận diện vùng dữ liệu

### 4.1 Nhận diện hàng tiêu đề

Chấm điểm từng hàng theo số tiêu đề chuẩn/alias được khớp, độ duy nhất của ánh xạ và vị trí tương đối. Chỉ chấp nhận một ứng viên vượt ngưỡng cấu hình và có ba cột bắt buộc.

### 4.2 Phân loại hàng người

Một hàng chỉ là `PERSON_ROW` khi thỏa các tín hiệu tối thiểu đã cấu hình, trong đó `Họ và tên` không rỗng và không khớp các nhãn vùng như `Tổng hợp`, `Thành tích lớp`, `GVCN`, `Tổng cộng`. `TT`, ngày sinh, tổ và điểm gốc là tín hiệu hỗ trợ; không một tín hiệu đơn lẻ nào được dùng để quyết định.

Các loại hàng tối thiểu:

- `HEADER_ROW`
- `PERSON_ROW`
- `SUMMARY_ROW`
- `FOOTER_ROW`
- `BLANK_ROW`
- `UNKNOWN_ROW`

`UNKNOWN_ROW` không được tính điểm và phải xuất cảnh báo để kiểm tra.

## 5. Tách và hiểu sự kiện

### 5.1 Yêu cầu giữ nguyên nguồn

Với mỗi ô `Minh chứng`, lưu nguyên văn ô, tọa độ workbook/sheet/hàng/cột và các đoạn ký tự (`source_span`) tạo thành từng sự kiện. Chuẩn hóa chỉ tạo trường mới; không thay thế văn bản gốc.

### 5.2 Chiến lược tách

1. Python tiền xử lý Unicode và ký tự xuống dòng mà không làm mất offset.
2. Tách xác định ở dấu chấm phẩy, xuống dòng và dấu phẩy chỉ khi dấu phẩy không nằm trong số thập phân/ngày/cấu trúc liên quan.
3. Bảo vệ các cụm như `4,8đ`, `(+3)`, ngày `10/3` và tên môn.
4. Khi một đoạn có dấu hiệu chứa nhiều delta/ngày/hành động nhưng không có ranh giới rõ, gửi đoạn đó cho AI để đề xuất segmentation và semantic fields theo schema.
5. Python kiểm tra output AI, đối chiếu span và giá trị; nếu không hợp lệ, giữ đoạn như một sự kiện mơ hồ và cảnh báo.

Ví dụ đầu vào:

`Đạt HĐTN 10/3(+3), 9đ Lí 13/3(+5), 4.8đ Toán GK2(-5), tham gia văn nghệ đạt giải 3(+15), diễn văn nghệ mít tinh(+10)`

Kỳ vọng tách thành năm sự kiện, vẫn giữ từng chuỗi nguyên bản và vị trí của chúng trong ô.

### 5.3 Trường được trích xuất

Mỗi sự kiện tối thiểu có:

- người, hàng/cột/ô nguồn;
- văn bản nguyên bản và nội dung chuẩn hóa;
- ngày sự kiện nếu có;
- điểm môn học nếu có;
- `declared_delta` nếu văn bản ghi điểm cộng/trừ;
- tín hiệu ngữ nghĩa phục vụ khớp quy tắc;
- độ tin cậy, cảnh báo và trạng thái duyệt.

Thứ tự ngày, nội dung và delta là tự do. Dấu thập phân `,` và `.` đều được hỗ trợ. Delta có thể trong/ngoài ngoặc. Việc thiếu ngày hoặc thiếu delta không làm mất sự kiện; nó tạo cảnh báo/phân nhánh duyệt phù hợp.

## 6. Áp dụng bảng quy tắc

- Bảng quy tắc phải có phiên bản, hiệu lực thời gian và định danh ổn định.
- Python nhận semantic fields đã được xác thực rồi khớp rule theo điều kiện xác định.
- Mỗi sự kiện lưu rule được khớp, lý do khớp và `expected_delta`.
- Không khớp rule: `expected_delta = null`, cảnh báo `NO_RULE_MATCH`.
- Nhiều rule cùng mức ưu tiên: không tự chọn; cảnh báo `AMBIGUOUS_RULE_MATCH`.
- Nếu cả `declared_delta` và `expected_delta` tồn tại nhưng khác nhau theo chính sách so sánh: thêm `RULE_CONFLICT`, `review_status = PENDING_REVIEW`, `final_delta = null`.
- Một rule không được phép đọc các tổng do người dùng nhập để quyết định điểm sự kiện.

## 7. Quyết định `final_delta`

`final_delta` là giá trị duy nhất được phép tham gia tổng chính thức.

- Có conflict/ambiguity/duplicate chưa duyệt: `final_delta = null`.
- Người duyệt có thể chọn declared, expected, nhập giá trị khác hoặc loại sự kiện; mọi lựa chọn phải có lý do và audit.
- Có thể cấu hình auto-accept cho trường hợp an toàn, nhưng chính sách phải được xác nhận trước khi triển khai.
- `REJECTED` không đồng nghĩa với điểm 0: sự kiện bị loại và `final_delta = null`; phép tổng hợp bỏ qua có chủ đích dựa trên trạng thái.

## 8. Tính toán và đối soát

Với tập sự kiện được tính (`AUTO_ACCEPTED` hoặc `APPROVED` và có `final_delta`):

- `calculated_bonus = sum(final_delta > 0)`
- `calculated_penalty = sum(abs(final_delta < 0))`
- `calculated_total = base_score + calculated_bonus - calculated_penalty`

Đối soát:

- `bonus_difference = calculated_bonus - source_bonus`
- `penalty_difference = calculated_penalty - source_penalty`
- `total_difference = calculated_total - source_total`

Nếu còn sự kiện `PENDING_REVIEW`, kết quả là `PROVISIONAL`, phải kèm số lượng mục chặn và không được trình bày như tổng cuối. Sau khi không còn mục chặn, kết quả là `FINALIZED`.

Giá trị thiếu không được biến thành `0`. Điểm nguồn không đọc được phải tạo lỗi/cảnh báo riêng và có thể chặn tính tổng người đó.

## 9. Đầu ra chức năng

Thiết kế đầu ra logic gồm:

1. Bản sao báo cáo mới, không phải workbook nguồn, chứa:
   - tổng quan lần chạy;
   - đối soát theo người;
   - danh sách sự kiện;
   - hàng đợi duyệt;
   - cảnh báo/lỗi;
   - thông tin phiên bản rule và cấu hình.
2. Dữ liệu kiểm toán máy đọc được theo `docs/DATA_CONTRACT.md`.
3. Hash file nguồn để chứng minh file không bị thay đổi.

Tên và định dạng vật lý cuối cùng cần được người dùng xác nhận trong `docs/ASSUMPTIONS.md`.

## 10. Yêu cầu phi chức năng

- Tính xác định: cùng input, rule version và quyết định duyệt phải cho cùng phép tính.
- Khả năng kiểm toán: truy ngược từ mọi tổng về các sự kiện và ô nguồn.
- Chống hỏng cục bộ: lỗi AI ở một ô không làm mất dữ liệu các hàng khác.
- Bảo mật: tối thiểu hóa dữ liệu gửi ra AI; không ghi log dữ liệu cá nhân toàn phần.
- Quan sát được: lưu run ID, phiên bản ứng dụng, rule version, model/prompt version (nếu dùng AI), thời gian và thống kê cảnh báo.
- Hỗ trợ tiếng Việt có/không dấu ở mức alias và khớp nội dung đã cấu hình.

## 11. Mã cảnh báo tối thiểu

`HEADER_NOT_FOUND`, `HEADER_AMBIGUOUS`, `MISSING_REQUIRED_COLUMN`, `UNKNOWN_ROW`, `INVALID_NUMBER`, `INVALID_DATE`, `MISSING_EVENT_DATE`, `MISSING_DECLARED_DELTA`, `SEGMENTATION_AMBIGUOUS`, `AI_OUTPUT_INVALID`, `NO_RULE_MATCH`, `AMBIGUOUS_RULE_MATCH`, `RULE_CONFLICT`, `DUPLICATE_CANDIDATE`, `SOURCE_TOTAL_MISMATCH`, `UNRESOLVED_EVENT`.

## 12. Tiêu chí nghiệm thu cấp cao

1. File nguồn trước và sau lần chạy có cùng hash.
2. Các vùng `Tổng hợp`, `Thành tích lớp`, `GVCN` không xuất hiện như người.
3. Ví dụ năm sự kiện ở trên được tách đúng trong fixture được duyệt.
4. `4,8đ` và `4.8đ` đều được đọc là điểm môn `4.8`, không bị tách nhầm ở dấu phẩy.
5. Thứ tự tự do của ngày/nội dung/delta không làm thay đổi giá trị đã trích xuất khi ngữ nghĩa tương đương.
6. Mọi conflict declared/expected sinh `RULE_CONFLICT` và không có `final_delta` tự động.
7. Ứng viên trùng không bị tự xóa.
8. Tất cả tổng và chênh lệch dùng phép tính Python/Decimal và truy ngược được về sự kiện.
9. Khi có mục chưa duyệt, báo cáo ghi rõ `PROVISIONAL`.
10. Không có lời gọi AI nào trực tiếp tạo `expected_delta`, `final_delta` hoặc tổng điểm.

