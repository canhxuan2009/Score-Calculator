# Roadmap

Roadmap chia theo cổng chất lượng. Không bắt đầu milestone sau khi tiêu chí thoát của milestone trước chưa đạt.

> Trạng thái 2026-08-06: theo yêu cầu triển khai trực tiếp của người dùng, input guard và baseline ingestion một sheet đã được thực hiện bằng fixture ẩn danh dù các blocker nghiệp vụ của Milestone 0 vẫn còn. Việc này không suy đoán bảng quy tắc và không mở phạm vi parser/rule engine.

## Milestone 0 — Chốt nghiệp vụ và dữ liệu

### Công việc

- Trả lời các câu hỏi chặn trong `ASSUMPTIONS.md`.
- Nhận workbook mẫu đã ẩn danh hoặc được phép sử dụng cho phát triển.
- Lập danh sách alias tiêu đề thực tế.
- Chuyển bảng quy tắc điểm thành catalog có ID, version, priority, hiệu lực và ví dụ.
- Gắn nhãn thủ công một bộ ô Minh chứng đại diện: separator hỗn hợp, không separator, decimal comma/dot, thiếu ngày/delta, lỗi nhập và trùng.
- Chốt đầu ra và luồng duyệt.

### Tiêu chí thoát

- Rule catalog v1 được người dùng xác nhận.
- Có golden dataset và expected results.
- Không còn câu hỏi `BLOCKER` chưa trả lời.

## Milestone 1 — Khung dự án và hợp đồng

### Công việc

- Khởi tạo package Python, cấu hình, logging an toàn và test runner.
- Cài model/schema từ `DATA_CONTRACT.md`.
- Xây input guard, hash nguồn và kiểm tra một sheet.
- Fixture bảo đảm workbook nguồn không đổi.

Input guard, hash bất biến và fixture tích hợp đã hoàn thành. Logging an toàn vẫn là phần còn lại trước khi đóng toàn bộ milestone.

### Tiêu chí thoát

- Schema validation và serialization round-trip đạt kiểm thử.
- Hash trước/sau giống nhau trong integration test.
- Chưa cần AI.

## Milestone 2 — Ingest và nhận diện sheet

### Công việc

- Header scoring và alias mapping.
- Row classifier cho person/header/summary/footer/blank/unknown.
- Parse điểm nguồn bằng Decimal, giữ raw values.
- Báo cáo lỗi cột bắt buộc và dòng không xác định.

Baseline đã hoàn thành cho header bắt buộc, alias cột, dòng học sinh/footer, `Decimal`, ngày sinh và provenance. Golden workbook nghiệp vụ vẫn cần được cung cấp để hoàn tất tiêu chí thoát của milestone.

### Tiêu chí thoát

- Đúng toàn bộ hàng người trên golden workbook.
- Không nhận nhầm `Tổng hợp`, `Thành tích lớp`, `GVCN`.
- Mọi record có provenance hàng/cột.

## Milestone 3 — Parser xác định

### Công việc

- Segmenter có bảo vệ dấu phẩy thập phân, ngày và ngoặc delta.
- Parser ngày, môn, điểm môn, delta và normalized content.
- Source span validation.
- Warning cho ambiguity/missing/invalid.

### Tiêu chí thoát

- Đạt bộ test ví dụ đã gắn nhãn.
- Không tách `4,8đ` thành hai sự kiện.
- Round-trip raw substring đạt 100% với span không null.

## Milestone 4 — Rule engine và conflict

### Công việc

- Loader/validator cho rule catalog versioned.
- Matching, priority và trace.
- Tính `expected_delta` bằng Python.
- Detector `RULE_CONFLICT`, ambiguous rule và duplicate candidate.

### Tiêu chí thoát

- Tất cả rule có unit test biên.
- Conflict không bao giờ sinh `final_delta` tự động.
- Duplicate candidate không bị tự loại.

## Milestone 5 — AI semantic fallback

### Công việc

- Adapter AI schema-constrained, prompt versioned và data minimization.
- Validation trường cấm, span và numeric fields.
- Timeout/retry/cache/fallback.
- Benchmark so với parser xác định và golden labels.

### Tiêu chí thoát

- AI không thể đặt rule/expected/final/tổng.
- Output sai schema chuyển duyệt, không làm crash run.
- Chỉ bật AI ở các ca đã chứng minh cải thiện đủ theo ngưỡng được chốt.

## Milestone 6 — Duyệt, tính và đối soát

### Công việc

- Review queue và decision log append-only.
- Auto-accept policy đã được phê duyệt.
- Calculator, provisional/finalized state và differences.
- Test property/invariant cho tổng.

### Tiêu chí thoát

- Mọi `final_delta` truy về policy hoặc review decision.
- Kết quả blocked/provisional không bị trình bày là final.
- Tái chạy với cùng decision log cho cùng tổng.

## Milestone 7 — Báo cáo và trải nghiệm người dùng

### Công việc

- Xuất workbook/JSON/CSV theo lựa chọn.
- Giao diện CLI trước; giao diện duyệt cục bộ nếu cần.
- Summary, per-person reconciliation, events, review queue và warnings.
- Chính sách tên file đầu ra không ghi đè.

### Tiêu chí thoát

- Người dùng hoàn thành luồng với workbook mẫu.
- Báo cáo truy ngược được từ total → event → source cell.
- Kiểm tra accessibility/encoding tiếng Việt.

## Milestone 8 — Hardening và phát hành

- Kiểm thử workbook lớn và giới hạn hiệu năng.
- Threat/privacy review, scrub log, quản lý secret.
- Backup/restore decision log.
- Packaging và hướng dẫn vận hành.
- Regression suite cho mọi lỗi thực tế đã gặp.

## Chiến lược kiểm thử xuyên suốt

- Unit: decimal/date parsing, segmentation, rule conditions, formulas.
- Golden: input đã gắn nhãn → events/rules/warnings mong đợi.
- Property-based: tổng dấu, bất biến raw/span, deterministic rerun.
- Mutation tests cho rule boundary quan trọng.
- Integration: workbook read-only đến artifact output.
- AI contract tests: JSON sai, hallucinated fields, timeout và kết quả mơ hồ.
- Regression: mỗi lỗi người dùng báo phải có fixture tối thiểu đã ẩn danh.
