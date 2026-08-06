# Giả định và câu hỏi cần xác nhận

Tài liệu này tách rõ điều đã được yêu cầu, quyết định thiết kế an toàn và phần chưa được phép suy đoán.

## 1. Đã được xác nhận từ yêu cầu

- Một file đầu vào có một sheet nghiệp vụ.
- Các cột tương đương danh sách trong `SPEC.md`.
- Một hàng tương ứng một người, nhưng có header phía trên và vùng không-phải-người phía dưới.
- Minh chứng có thể rất tự do về dấu ngăn, thứ tự, dấu thập phân, ngoặc, ngày và lỗi nhập.
- Điểm cộng/trừ/tổng trong file do người dùng tự tính, chỉ dùng đối soát.
- Ba nguồn delta phải tách biệt.
- Conflict declared/expected phải là `RULE_CONFLICT`, không tự chọn.
- AI chỉ hỗ trợ tách/hiểu; Python áp rule/tính/đối soát.
- Workbook nguồn bất biến.
- Ngày sự kiện thiếu năm dùng `ScoringPeriod` khi kỳ cho đúng một năm hợp lý; ngày
  ngoài kỳ được giữ nguyên và cảnh báo, không tự sửa.

## 2. Quyết định an toàn tạm thời

Những quyết định này được dùng để hoàn thiện đặc tả, có thể đổi trước khi code:

| Chủ đề | Mặc định đề xuất | Lý do |
|---|---|---|
| Điểm nội bộ | `Decimal`, JSON string | tránh sai số float |
| Dấu của delta | cộng dương, trừ âm | đơn giản hóa rule và audit |
| Cột Điểm trừ nguồn | độ lớn không âm | phù hợp công thức `gốc + cộng - trừ` |
| Xung đột/trùng/mơ hồ | chặn event, chờ duyệt | không tự làm sai dữ liệu |
| Event bị từ chối | `final_delta = null`, loại có dấu vết | phân biệt loại với 0 điểm |
| Ngày thiếu năm | chỉ dựng ngày đầy đủ khi `ScoringPeriod` suy ra duy nhất; luôn giữ raw/span | tránh gán sai năm và vẫn hỗ trợ sắp thời gian |
| Hạnh kiểm | chỉ giữ và đối chiếu nếu có rule riêng | yêu cầu chưa nêu cách tính |
| Nhiều sheet | dừng có hướng dẫn | input contract nói một sheet |
| Output | file mới + audit machine-readable | bảo vệ nguồn và truy vết |

## 3. Câu hỏi BLOCKER trước khi viết logic nghiệp vụ

### B1. Bảng quy tắc chính thức là gì?

Cần bảng có: loại sự kiện, điều kiện/keyword, ngưỡng điểm môn, delta, thời gian hiệu lực, priority, ngoại lệ và ví dụ. Không thể suy ra an toàn chỉ từ các ví dụ Minh chứng.

### B2. Khi chỉ có một nguồn delta thì xử lý thế nào?

Cần chọn policy riêng cho:

- có declared nhưng không khớp rule;
- khớp rule nhưng không có declared;
- có declared = expected;
- không có cả hai.

Đề xuất thận trọng: chỉ auto-accept khi cả hai tồn tại, bằng nhau, khớp duy nhất và confidence đạt ngưỡng; các trường hợp khác chờ duyệt. Nếu muốn tự động nhiều hơn, cần xác nhận rõ.

### B3. So sánh và làm tròn điểm ra sao?

Cần biết số chữ số thập phân, có cho tolerance hay yêu cầu bằng Decimal tuyệt đối, và cách làm tròn (`ROUND_HALF_UP` hay chính sách khác). Đề xuất: chuẩn hóa trailing zero và so sánh Decimal chính xác; không dùng tolerance nếu rule tạo điểm rời rạc.

### B5. Đầu ra và nơi duyệt mong muốn?

Chọn một trong: CLI hỏi tuần tự, workbook báo cáo có cột quyết định, giao diện web/local, hoặc kết hợp. Cần chốt cách nhập lại quyết định và danh tính reviewer.

### B6. AI và dữ liệu cá nhân

Cần xác nhận có được gửi tên/ngày sinh/nội dung Minh chứng tới API bên ngoài hay không. Đề xuất: không gửi tên, ngày sinh, tổ; chỉ gửi đoạn Minh chứng tối thiểu đã thay thế định danh nếu có, trừ khi người dùng đồng ý khác.

## 4. Câu hỏi không chặn skeleton nhưng chặn phát hành

- Alias tiêu đề thực tế ngoài các tên đã nêu?
- `.xls` cũ có cần hỗ trợ hay chỉ `.xlsx/.xlsm`?
- Công thức trong ô cần đọc giá trị cached hay tự tính lại bằng Excel/LibreOffice?
- Ngưỡng kích thước workbook và thời gian chạy chấp nhận được?
- Có cần chạy hoàn toàn offline?
- Có cần nhiều người duyệt, phân quyền hoặc chữ ký quyết định?
- Cần lưu audit bao lâu và ở đâu?
- Một người có thể xuất hiện nhiều hàng không; khóa nhận diện là gì?
- Khi `Điểm trừ` nguồn được nhập số âm, coi là lỗi hay chuẩn hóa thành độ lớn?
- Có đối soát `Hạnh kiểm` hay chỉ giữ nguyên?

## 5. Giả định cần kiểm chứng bằng file mẫu

- Header nằm trong vùng quét hữu hạn ở đầu sheet.
- Một cột `Minh chứng` duy nhất cho mỗi hàng người.
- Ô gộp không đi xuyên qua nhiều hàng người.
- `Họ và tên` đủ để hiển thị nhưng không đủ làm ID duy nhất.
- Các khu vực footer có nhãn nhận diện được; row classifier vẫn cần kiểm tra format/thành phần khác.
- Dấu phẩy giữa sự kiện và dấu phẩy thập phân có thể phân biệt bằng ngữ cảnh trong phần lớn trường hợp.

Mỗi giả định thất bại trong file thật phải trở thành fixture regression và, nếu ảnh hưởng hợp đồng, cập nhật tài liệu trước khi sửa code.
