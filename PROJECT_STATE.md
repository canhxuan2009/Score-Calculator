# PROJECT_STATE.md

## Trạng thái hiện tại

- Giai đoạn: `Milestone 1 input guard + Milestone 2 ingestion baseline + Milestone 3 deterministic segmenter / in progress`.
- Repository ban đầu chỉ có tài liệu đặc tả; skeleton Python 3.12 hiện đã được tạo.
- Lớp đọc workbook một sheet và bộ tách sự kiện Minh chứng thuần Python đã triển khai;
  semantic parser, áp dụng quy tắc và tính điểm cuối vẫn chưa triển khai.
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
- Domain contract Pydantic v2 phiên bản `0.3.0` đã được triển khai tại
  `src/point_audit/domain`.
- Domain model đã bao phủ provenance workbook, candidate/parsed event, ngày thiếu năm,
  kỳ tính điểm, rule/match/conflict, duplicate, review/timeline, totals và đối soát theo người.
- Mọi giá trị điểm/confidence dùng `Decimal` hữu hạn; model từ chối `float`, `NaN` và vô hạn.
- Event ID ổn định được sinh bằng SHA-256 từ định danh file nguồn và vị trí/span sự kiện.
- `docs/DATA_CONTRACT.md` đã đồng bộ với code contract `0.3.0`.
- `WorkbookReader` tại `src/point_audit/ingestion` chỉ nhận đúng một sheet, tự tìm header không phụ thuộc hàng 1 và không ghi workbook.
- Reader mở song song read-only view công thức/cached value, giữ cả hai trong provenance khi có và kiểm tra SHA-256 trước/sau.
- Reader nhận diện `ScoringPeriod` từ tiêu đề phía trên, đọc ngày sinh dạng Excel date/chuỗi/serial và không dùng ngày sinh làm ngày sự kiện.
- Dòng học sinh được xác định bằng TT số và/hoặc Họ và tên; các vùng `TỔNG HỢP`, `Thành tích lớp`, `GVCN` bị loại và chặn phần đọc phía sau.
- Các tổng khai báo được parse bằng `Decimal`; sai công thức dòng sinh `ROW_FORMULA_MISMATCH` nhưng dữ liệu và dòng vẫn được giữ.
- `segment_evidence` tại `point_audit.parsing` tách xác định theo dấu chấm phẩy,
  xuống dòng, dấu phẩy có ngữ cảnh và dấu hiệu sự kiện mới không có delimiter.
- Segmenter bảo vệ dấu phẩy thập phân, URL, ngày/tháng và delta trong ngoặc; nhận
  diện các dấu cộng/trừ Unicode thông dụng.
- Mỗi `EventSegment` giữ nguyên `raw_text`, `TextSpan` 0-based half-open và
  `delimiter_after`; toàn bộ kết quả luôn ghép lại chính xác thành chuỗi nguồn.
- Ca không chắc chắn được giữ nguyên, sinh `SEGMENTATION_AMBIGUOUS` blocking và có
  thể chuyển thành `EventCandidate` với đầy đủ provenance; không gọi AI và không
  loại bỏ đoạn chưa hiểu.

## Kiểm tra gần nhất

Chạy trong Python 3.12.13 với môi trường `.venv` cục bộ:

- `pytest`: đạt, `103 passed` (`59` test mới cho segmenter và `44` test sẵn có).
- `ruff check .`: đạt, không có lỗi.
- `mypy src/point_audit app.py`: đạt, 22 source files không có lỗi.
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

## Trường hợp segmenter chưa thể xác định chắc chắn

- Dấu phẩy trước một cụm yếu như `đạt ...`, tên hoạt động hoặc ngày mới khi phần
  trước chưa có delta hoàn chỉnh: giữ cả cụm thành một segment và cảnh báo thay vì
  chia quá mức.
- Nhiều hoạt động dùng chung đúng một delta, ví dụ `tham gia bóng đá, kéo co (+10)`:
  giữ nguyên một sự kiện; segmenter không tự phân bổ delta cho từng hoạt động.
- Hoạt động mới không nằm trong danh sách tín hiệu và không có delimiter/delta riêng:
  chưa có đủ căn cứ để tách, nên nội dung được bảo toàn cho semantic parser hoặc người duyệt.
- Dấu chấm phẩy/xuống dòng nằm trong ngoặc hoặc ngoặc mở không đóng: bảo toàn cụm và
  cảnh báo vì cả tách lẫn không tách đều có thể hợp lý.
- Dấu câu đứng sát cuối URL có thể thuộc URL hoặc là delimiter. Dấu câu bên trong URL
  được bảo vệ; dấu phẩy/chấm phẩy ngay trước khoảng trắng được coi là delimiter ngoài URL.
- Segmenter chỉ quyết định ranh giới. Nó chưa xác định ngày, môn, điểm môn hay
  `declared_delta` thành semantic fields.

## Chưa được quyết định — chặn triển khai nghiệp vụ

- Bảng quy tắc điểm chính thức và thứ tự ưu tiên khi nhiều quy tắc cùng khớp.
- Chính sách tự động chấp nhận khi chỉ có `declared_delta` hoặc chỉ có `expected_delta`.
- Ngưỡng sai số khi so sánh điểm và quy tắc làm tròn.
- Cách suy ra năm cho ngày chỉ có ngày/tháng.
- Định dạng đầu ra mong muốn: workbook báo cáo, JSON/CSV, giao diện duyệt hay kết hợp.
- Môi trường chạy và nhà cung cấp AI; yêu cầu bảo mật dữ liệu cá nhân.

Chi tiết và đề xuất mặc định nằm trong `docs/ASSUMPTIONS.md`.

## Bước tiếp theo được khuyến nghị

1. Chạy segmenter trên tập Minh chứng thật đã ẩn danh và bổ sung regression fixture cho
   mọi cảnh báo/tách sai mới gặp.
2. Triển khai semantic parser thuần Python cho ngày, môn, điểm môn và `declared_delta`
   trên các segment đã có provenance.
3. Người dùng xác nhận các câu hỏi chặn trong `docs/ASSUMPTIONS.md`.
4. Bổ sung bảng quy tắc phiên bản đầu tiên cùng ví dụ đúng/sai đã ẩn danh.
5. Chốt hợp đồng đầu ra, luồng duyệt và golden workbook nghiệp vụ.
