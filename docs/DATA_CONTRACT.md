# Hợp đồng dữ liệu domain

Tài liệu này mô tả đúng hợp đồng Pydantic v2 của `point_audit.domain` và kết quả đọc workbook tại `point_audit.ingestion`. Phiên bản hiện tại là `0.3.0`, tương ứng hằng `DOMAIN_CONTRACT_VERSION`.

## 1. Quy ước chung

- Tất cả model kế thừa `DomainModel` với `extra="forbid"`, `frozen=True` và `validate_default=True`.
- Điểm, delta, tổng, độ tương đồng và độ tin cậy dùng `Decimal`; đầu vào `float` và `bool` bị từ chối.
- Mọi `Decimal` phải hữu hạn. `NaN`, `Infinity` và `-Infinity` không hợp lệ.
- `NonNegativeDecimal` yêu cầu giá trị `>= 0`.
- `ConfidenceDecimal` yêu cầu giá trị trong đoạn `[0, 1]`.
- JSON biểu diễn `Decimal` bằng chuỗi thập phân và `date` bằng ISO `YYYY-MM-DD`.
- Các enum được serialize bằng giá trị chữ hoa ghi trong mục 2.
- Chỉ số dòng/cột Excel là 1-based. `TextSpan` là đoạn `[start, end)` 0-based trên `RawCell.raw_text`.
- Chuỗi nguồn không bị trim hoặc thay thế. `EventCandidate.raw_text` phải khớp chính xác substring của ô nguồn.

## 2. Enum

| Enum | Giá trị |
|---|---|
| `SourceColumn` | `SEQUENCE`, `FULL_NAME`, `BIRTH_DATE`, `GROUP`, `BASE_SCORE`, `POSITIVE_TOTAL`, `NEGATIVE_TOTAL`, `FINAL_TOTAL`, `CONDUCT`, `EVIDENCE`, `UNKNOWN` |
| `EventType` | `BONUS`, `PENALTY`, `INFORMATIONAL`, `UNKNOWN` |
| `DeltaSign` | `PLUS`, `MINUS` |
| `DatePrecision` | `FULL`, `DAY_MONTH`, `MISSING`, `AMBIGUOUS` |
| `ParseSource` | `DETERMINISTIC`, `AI`, `MANUAL`, `HYBRID` |
| `ReviewStatus` | `UNREVIEWED`, `PENDING_REVIEW`, `AUTO_ACCEPTED`, `APPROVED`, `REJECTED` |
| `ReviewAction` | `USE_DECLARED`, `USE_EXPECTED`, `SET_CUSTOM`, `REJECT_EVENT`, `EDIT_PARSED_FIELDS` |
| `RuleMatchStatus` | `NO_MATCH`, `ONE_MATCH`, `AMBIGUOUS_MATCH` |
| `TimelineItemType` | `DISCOVERED`, `PARSED`, `VALIDATED`, `RULE_MATCHED`, `DUPLICATE_FLAGGED`, `REVIEWED` |

`WarningCode` gồm:

`HEADER_NOT_FOUND`, `HEADER_AMBIGUOUS`, `MISSING_REQUIRED_COLUMN`, `UNKNOWN_ROW`, `INVALID_NUMBER`, `INVALID_DATE`, `DATE_AMBIGUOUS`, `DATE_OUTSIDE_PERIOD`, `MISSING_EVENT_DATE`, `MISSING_DECLARED_DELTA`, `SEGMENTATION_AMBIGUOUS`, `AI_OUTPUT_INVALID`, `NO_RULE_MATCH`, `AMBIGUOUS_RULE_MATCH`, `RULE_CONFLICT`, `DUPLICATE_CANDIDATE`, `SOURCE_TOTAL_MISMATCH`, `ROW_FORMULA_MISMATCH`, `UNRESOLVED_EVENT`, `INVALID_EVENT_STATE`, `MISSING_REVIEW_INFORMATION`.

## 3. Kiểu dùng chung

### 3.1 `TextSpan`

| Field | Type | Ràng buộc |
|---|---|---|
| `start` | `int` | `>= 0` |
| `end` | `int` | `> start` |

### 3.2 `DomainWarning`

| Field | Type | Ràng buộc |
|---|---|---|
| `code` | `WarningCode` | bắt buộc |
| `message_vi` | `str` | không được rỗng/trắng |
| `blocking` | `bool` | mặc định `false` |

## 4. Provenance workbook

### 4.1 `RawCell`

| Field | Type | Ràng buộc |
|---|---|---|
| `source_file_sha256` | `str` | đúng 64 ký tự hex, chuẩn hóa lowercase |
| `sheet_name` | `str` | không rỗng |
| `excel_row` | `int` | `>= 1` |
| `excel_column` | `int` | `>= 1` |
| `source_column` | `SourceColumn` | cột chuẩn |
| `source_column_name` | `str` | tên header vật lý, không rỗng |
| `raw_text` | `str` | văn bản ô nguyên bản; có thể rỗng đối với ô nguồn |
| `formula` | `str | None` | công thức nguyên bản, phải bắt đầu bằng `=` và bằng `raw_text` |
| `cached_value_text` | `str | None` | giá trị tính sẵn được lưu trong file; chỉ hợp lệ khi có `formula` |

### 4.2 `RawWorkbookRow`

| Field | Type | Ràng buộc |
|---|---|---|
| `source_file_sha256` | `str` | SHA-256 nguồn |
| `sheet_name` | `str` | không rỗng |
| `excel_row` | `int` | `>= 1` |
| `cells` | `tuple[RawCell, ...]` | ít nhất một ô |

Mọi cell phải cùng hash file, sheet và dòng với row. Không được lặp `excel_column` trong một row.

### 4.3 `DetectedColumn`

| Field | Type | Ràng buộc |
|---|---|---|
| `source_column` | `SourceColumn` | cột chuẩn được nhận diện |
| `excel_column` | `int` | `>= 1` |
| `source_column_name` | `str` | header vật lý nguyên bản, không rỗng |

### 4.4 `IngestedStudentRow`

| Field | Type | Ý nghĩa/ràng buộc |
|---|---|---|
| `source_file_sha256` | `str` | hash file nguồn |
| `sheet_name` | `str` | sheet nguồn |
| `excel_row` | `int` | dòng Excel 1-based |
| `sequence_raw` | `str | None` | TT nguyên bản |
| `sequence_number` | `int | None` | TT số nguyên không âm nếu parse được |
| `full_name_raw` | `str | None` | họ tên nguyên bản |
| `birth_date_raw` | `str | None` | ngày sinh nguyên bản, kể cả serial/công thức |
| `birth_date` | `date | None` | ngày sinh đã parse; không phải ngày sự kiện |
| `group_raw` | `str | None` | tổ nguyên bản |
| `base_score_raw` | `str | None` | Điểm gốc nguyên bản |
| `base_score` | `Decimal | None` | Điểm gốc parse được |
| `declared_positive_raw` | `str | None` | Điểm cộng khai báo nguyên bản |
| `declared_positive_total` | non-negative `Decimal | None` | Điểm cộng khai báo parse được |
| `declared_negative_raw` | `str | None` | Điểm trừ khai báo nguyên bản |
| `declared_negative_total` | non-negative `Decimal | None` | Điểm trừ khai báo parse được |
| `declared_final_raw` | `str | None` | Tổng khai báo nguyên bản |
| `declared_final_total` | `Decimal | None` | Tổng khai báo parse được |
| `conduct_raw` | `str | None` | hạnh kiểm nguyên bản |
| `evidence_raw` | `str` | Minh chứng nguyên bản, có thể rỗng |
| `raw_row` | `RawWorkbookRow` | toàn bộ ô cột đã ánh xạ với provenance |
| `warnings` | `tuple[DomainWarning, ...]` | cảnh báo mức dòng |

Một dòng được giữ khi có `sequence_number` và/hoặc `full_name_raw` không rỗng. `raw_row` phải cùng hash, sheet và dòng. Ngày sinh chỉ là thuộc tính người; ingestion không tạo `ParsedEvent` và không chuyển ngày sinh sang `event_date`.

### 4.5 `WorkbookIngestionResult`

| Field | Type | Ý nghĩa/ràng buộc |
|---|---|---|
| `source_file_name` | `str` | tên file, không chứa nội dung workbook |
| `source_file_sha256` | `str` | SHA-256 trước và sau khi đọc phải giống nhau |
| `sheet_name` | `str` | sheet duy nhất |
| `header_row` | `int` | dòng tiêu đề nhận diện, `>= 1` |
| `columns` | `tuple[DetectedColumn, ...]` | ít nhất 5 cột, không lặp cột chuẩn |
| `scoring_period` | `ScoringPeriod | None` | kỳ nhận diện từ vùng trên header |
| `students` | `tuple[IngestedStudentRow, ...]` | các dòng học sinh |
| `stopped_at_row` | `int | None` | dòng bắt đầu footer/summary nếu gặp |
| `formulas_found` | `bool` | có ít nhất một công thức trong các ô đã đọc |
| `cached_formula_values_found` | `bool` | có ít nhất một giá trị công thức tính sẵn |
| `warnings` | `tuple[DomainWarning, ...]` | cảnh báo cấp workbook |

`cached_formula_values_found=true` chỉ hợp lệ khi `formulas_found=true`. Mọi student phải cùng file/sheet và nằm sau `header_row`.

### 4.6 Hợp đồng `WorkbookReader`

- Chỉ chấp nhận workbook có đúng một sheet; không chọn hoặc gộp nhiều sheet.
- Mở file hai lần ở chế độ read-only: `data_only=false` để giữ công thức và `data_only=true` để đọc cached value nếu file có lưu. Không gọi `save`.
- Header là duy nhất và phải có đồng thời `Họ và tên`, `Điểm cộng`, `Điểm trừ`, `Tổng`, `Minh chứng` sau chuẩn hóa alias. Không tìm thấy hoặc có nhiều candidate là lỗi dừng.
- Vùng trên header được quét để nhận diện khoảng có hai ngày đầy đủ, ví dụ `Đợt 6: Từ 28/02/2026 – 03/04/2026`; không nhận diện được thì `scoring_period=null`.
- Dòng học sinh được nhận diện bằng TT số và/hoặc Họ và tên. Khi gặp `TỔNG HỢP`, `Thành tích lớp`, `GVCN` ở vùng định danh dòng, reader dừng và không coi dòng đó/các dòng sau là học sinh.
- Ngày sinh nhận Excel date, chuỗi ngày và serial number theo epoch của workbook. Parse lỗi tạo `INVALID_DATE` nhưng vẫn giữ dòng.
- Điểm nguồn được chuyển qua chuỗi sang `Decimal`, không lưu `float`. Số thiếu khác số `0`; số sai tạo `INVALID_NUMBER`.
- Khi đủ bốn số và `declared_final_total != base_score + declared_positive_total - declared_negative_total`, reader thêm `ROW_FORMULA_MISMATCH` nhưng giữ nguyên dòng và dữ liệu khai báo.
- Hash file được tính lại sau khi đóng workbook; thay đổi trong lúc đọc là lỗi dừng `SourceWorkbookChangedError`.

## 5. Sự kiện

### 5.1 Event ID ổn định

`build_event_id` tạo chuỗi `evt_<sha256>` từ đúng các thành phần sau, nối bằng ký tự phân cách ổn định:

1. `source_file_sha256`;
2. `sheet_name`;
3. `excel_row`;
4. `excel_column`;
5. `source_column_name`;
6. `source_span.start` và `source_span.end`;
7. `candidate_index`;
8. `raw_text`.

Nếu caller cung cấp `event_id` không khớp giá trị trên, model bị từ chối. Nếu bỏ trống, model tự sinh ID.

### 5.2 `EventCandidate`

| Field | Type | Ràng buộc |
|---|---|---|
| `event_id` | `str` | ID ổn định được kiểm tra/tự sinh |
| `person_id` | `str` | không rỗng |
| `source_cell` | `RawCell` | phải thuộc `SourceColumn.EVIDENCE` |
| `source_span` | `TextSpan` | nằm trong `source_cell.raw_text` |
| `candidate_index` | `int` | `>= 0` |
| `raw_text` | `str` | không rỗng, bằng chính xác source substring |
| `parse_source` | `ParseSource` | nguồn phân tích |
| `reported_confidence` | `ConfidenceDecimal | None` | độ tin cậy do parser/AI tự khai; không phải kết quả cuối |
| `warnings` | `tuple[DomainWarning, ...]` | mặc định rỗng |

### 5.3 `ParsedEvent`

`ParsedEvent` kế thừa toàn bộ field/ràng buộc của `EventCandidate` và bổ sung:

| Field | Type | Ý nghĩa/ràng buộc |
|---|---|---|
| `event_type` | `EventType` | hướng cộng/trừ/thông tin/chưa rõ |
| `description` | `str` | mô tả chuẩn hóa, không rỗng |
| `evidence_text` | `str` | minh chứng phải còn nguyên trong `raw_text` |
| `academic_score` | `Decimal | None` | điểm bài kiểm tra/môn học |
| `declared_delta` | `Decimal | None` | delta có dấu ghi trong Minh chứng |
| `expected_delta` | `Decimal | None` | delta có dấu do rule Python tạo |
| `final_delta` | `Decimal | None` | delta cuối chỉ có sau auto-accept/duyệt |
| `declared_delta_sign` | `DeltaSign | None` | dấu được viết trong nguồn |
| `academic_score_span` | `TextSpan | None` | span điểm bài kiểm tra |
| `declared_delta_span` | `TextSpan | None` | span delta khai báo |
| `date_span` | `TextSpan | None` | span ngày |
| `event_date_text` | `str | None` | ngày như được viết |
| `event_date` | `date | None` | chỉ dùng khi `FULL` |
| `event_day` | `int | None` | `1..31`, dùng cho `DAY_MONTH` |
| `event_month` | `int | None` | `1..12`, dùng cho `DAY_MONTH` |
| `date_precision` | `DatePrecision` | trạng thái ngày tường minh |
| `matched_rule_id` | `str | None` | rule duy nhất được khớp |
| `rule_match_confidence` | `ConfidenceDecimal | None` | confidence của rule match |
| `final_confidence` | `ConfidenceDecimal` | confidence cuối sau kiểm tra Python |
| `requires_review` | `bool` | có cần người duyệt hay không |
| `review_status` | `ReviewStatus` | mặc định `UNREVIEWED` |
| `review_record_id` | `str | None` | liên kết quyết định duyệt |

Các bất biến của `ParsedEvent`:

- `academic_score` và `academic_score_span` phải cùng tồn tại hoặc cùng `null`.
- `declared_delta`, `declared_delta_span`, `declared_delta_sign` phải cùng tồn tại hoặc cùng `null`; dấu phải khớp giá trị.
- Các span con phải nằm trong `source_span`.
- `FULL`: có `event_date`, `event_date_text`, `date_span`; không có `event_day/month`.
- `DAY_MONTH`: không có `event_date`; bắt buộc day, month, raw date text và span. Ngày/tháng phải có thể tồn tại trong ít nhất một năm; ví dụ 31/2 bị từ chối, 29/2 được giữ.
- `MISSING`: không mang bất kỳ giá trị/span ngày nào và phải có warning `MISSING_EVENT_DATE`.
- `AMBIGUOUS`: không có ngày đầy đủ, phải giữ text mơ hồ, có warning `DATE_AMBIGUOUS` và `requires_review=true`.
- `matched_rule_id`, `expected_delta`, `rule_match_confidence` phải cùng tồn tại hoặc cùng `null`.
- `BONUS` không nhận delta âm; `PENALTY` không nhận delta dương; `INFORMATIONAL` không nhận delta.
- `UNKNOWN` luôn yêu cầu duyệt.
- Khi `declared_delta != expected_delta`: bắt buộc `RULE_CONFLICT`, `PENDING_REVIEW`, `requires_review=true`, `final_delta=null`.
- `AUTO_ACCEPTED`/`APPROVED`: bắt buộc `final_delta` và `review_record_id`, đồng thời `requires_review=false`.
- `REJECTED`: bắt buộc `review_record_id`, `final_delta=null`, `requires_review=false`.
- `UNREVIEWED`/`PENDING_REVIEW` không được chứa final review data.

`reported_confidence` và `final_confidence` là hai field độc lập. Giá trị AI tự khai không bao giờ tự động trở thành confidence cuối.

## 6. Validation và duplicate

### 6.1 `ValidationResult`

| Field | Type |
|---|---|
| `is_valid` | `bool` |
| `warnings` | `tuple[DomainWarning, ...]` |
| `errors` | `tuple[str, ...]` |
| `requires_review` | `bool` |

Kết quả hợp lệ không có errors; kết quả không hợp lệ phải có ít nhất một error không rỗng. Error hoặc warning blocking bắt buộc `requires_review=true`.

### 6.2 `DuplicateMatch`

| Field | Type | Ràng buộc |
|---|---|---|
| `event_id` | `str` | sự kiện gốc |
| `duplicate_event_id` | `str` | phải khác `event_id` |
| `similarity_score` | `ConfidenceDecimal` | `[0,1]` |
| `reasons` | `tuple[str, ...]` | ít nhất một lý do không rỗng |
| `requires_review` | `bool` | luôn phải là `true` |

Model không có trạng thái tự xóa hoặc tự gộp sự kiện.

## 7. Review và timeline

### 7.1 `ReviewRecord`

| Field | Type |
|---|---|
| `review_id` | `str` |
| `event_id` | `str` |
| `status` | `ReviewStatus` |
| `action` | `ReviewAction | None` |
| `reviewer_id` | `str | None` |
| `reviewed_at` | `datetime | None` |
| `reason` | `str | None` |
| `final_delta` | `Decimal | None` |
| `previous_review_id` | `str | None` |

`AUTO_ACCEPTED`, `APPROVED`, `REJECTED` đều cần action, reviewer, thời gian có timezone và lý do. Hai trạng thái accepted cần `final_delta` và không được dùng `REJECT_EVENT`. `REJECTED` chỉ dùng `REJECT_EVENT` và không có `final_delta`. Trạng thái chưa hoàn tất không được mang decision metadata.

### 7.2 `TimelineItem`

| Field | Type |
|---|---|
| `item_id` | `str` |
| `person_id` | `str` |
| `event_id` | `str | None` |
| `item_type` | `TimelineItemType` |
| `occurred_at` | timezone-aware `datetime` |
| `description` | `str` |
| `actor_id` | `str` |

Các trường text bắt buộc không rỗng.

## 8. Kỳ tính điểm và kiểm tra ngày

### 8.1 `ScoringPeriod`

| Field | Type |
|---|---|
| `period_id` | `str` |
| `name` | `str` |
| `starts_on` | `date` |
| `ends_on` | `date` |
| `academic_year_label` | `str` |

Khoảng thời gian bao gồm cả hai đầu và `ends_on >= starts_on`.

### 8.2 `DatePeriodValidation`

| Field | Type |
|---|---|
| `event_id` | `str` |
| `scoring_period` | `ScoringPeriod` |
| `date_precision` | `DatePrecision` |
| `event_date` | `date | None` |
| `event_day` | `int | None` |
| `event_month` | `int | None` |
| `candidate_dates` | `tuple[date, ...]` |
| `is_within_period` | `bool | None` |
| `warnings` | `tuple[DomainWarning, ...]` |

- `FULL`: `is_within_period` phải khớp phép so sánh với period; ngoài kỳ cần `DATE_OUTSIDE_PERIOD`.
- `DAY_MONTH`: không có `event_date`; `candidate_dates` chỉ là các ngày đầy đủ khả dĩ nằm trong period và giữ đúng day/month. Đây không phải hành động tự gán năm. `is_within_period` phản ánh có/không candidate.
- `MISSING`/`AMBIGUOUS`: không có resolved date/period result và phải có warning tương ứng.

## 9. Tổng điểm và đối soát

### 9.1 `DeclaredRowTotals`

| Field | Type |
|---|---|
| `base_score` | `Decimal | None` |
| `positive_total` | non-negative `Decimal | None` |
| `negative_total` | non-negative `Decimal | None` |
| `final_total` | `Decimal | None` |

Đây là số người dùng nhập nên model không ép công thức nội bộ phải đúng.

### 9.2 `CalculatedRowTotals`

Có cùng bốn field và kiểu như `DeclaredRowTotals`. Khi cả bốn tồn tại, bắt buộc:

```text
final_total = base_score + positive_total - negative_total
```

### 9.3 `PersonReconciliation`

| Field | Type |
|---|---|
| `declared_positive_total` | non-negative `Decimal | None` |
| `declared_negative_total` | non-negative `Decimal | None` |
| `declared_final_total` | `Decimal | None` |
| `calculated_positive_total` | non-negative `Decimal | None` |
| `calculated_negative_total` | non-negative `Decimal | None` |
| `calculated_final_total` | `Decimal | None` |
| `positive_difference` | `Decimal | None` |
| `negative_difference` | `Decimal | None` |
| `final_difference` | `Decimal | None` |
| `unresolved_event_count` | `int >= 0` |

Mỗi difference bằng `calculated - declared`. Nếu cả hai total có mặt và difference bị bỏ trống, model tính chính xác bằng `Decimal`; nếu caller đưa difference sai, model từ chối. Nếu một total thiếu, difference tương ứng phải `null`.

`from_totals` tạo reconciliation từ `DeclaredRowTotals` và `CalculatedRowTotals`.

## 10. Rule

### 10.1 `RuleDefinition`

| Field | Type |
|---|---|
| `rule_id`, `version`, `name` | `str` không rỗng |
| `event_type` | `EventType` |
| `expected_delta` | `Decimal` hữu hạn, đúng hướng event |
| `priority` | `int >= 0` |
| `enabled` | `bool`, mặc định `true` |
| `effective_from`, `effective_to` | `date | None` |
| `academic_score_min`, `academic_score_max` | `Decimal | None` |
| `description_keywords` | unique `tuple[str, ...]` không rỗng |
| `scoring_period_ids` | `tuple[str, ...]` không rỗng |
| `requires_event_date` | `bool` |

Rule không được dùng `UNKNOWN`, sai hướng delta, khoảng score đảo hoặc khoảng hiệu lực đảo.

### 10.2 `RuleMatch`

| Field | Type |
|---|---|
| `event_id` | `str` |
| `status` | `RuleMatchStatus` |
| `matched_rule_id` | `str | None` |
| `candidate_rule_ids` | `tuple[str, ...]` |
| `expected_delta` | `Decimal | None` |
| `confidence` | `ConfidenceDecimal | None` |
| `trace` | `tuple[str, ...]` |

- `NO_MATCH`: không có selected rule/delta/confidence.
- `ONE_MATCH`: có rule ID, delta, confidence; selected ID phải thuộc candidates.
- `AMBIGUOUS_MATCH`: có ít nhất hai candidates và không được chọn rule/delta.

### 10.3 `RuleConflict`

| Field | Type |
|---|---|
| `event_id`, `rule_id` | `str` |
| `declared_delta`, `expected_delta` | `Decimal`, phải khác nhau |
| `warning_code` | luôn `RULE_CONFLICT` |
| `resolved` | `bool`, mặc định `false` |
| `resolved_delta` | `Decimal | None` |
| `review_record_id` | `str | None` |

Conflict chưa giải quyết không có resolution data. Conflict đã giải quyết phải có cả `resolved_delta` và `review_record_id`.

## 11. `PersonSummary`

| Field | Type |
|---|---|
| `person_id` | `str` |
| `full_name` | `str` |
| `sheet_name` | `str` |
| `excel_row` | `int >= 1` |
| `scoring_period_id` | `str` |
| `reconciliation` | `PersonReconciliation` |
| `event_ids` | unique `tuple[str, ...]` |
| `warnings` | `tuple[DomainWarning, ...]` |
| `requires_review` | `bool` |

`requires_review` phải đúng khi `unresolved_event_count > 0` hoặc có warning blocking.

## 12. Compatibility và migration

Phiên bản `0.3.0` là thay đổi cộng thêm so với `0.2.0`: bổ sung `RawCell.formula`, `RawCell.cached_value_text`, `ROW_FORMULA_MISMATCH` và ba model kết quả ingestion. Không có dữ liệu persistence sản xuất nên chưa cần migration vật lý; payload `0.2.0` vẫn validate vì hai field mới của `RawCell` đều mặc định `null`. Mọi thay đổi sau `0.3.0` phải cập nhật đồng thời code, test fixture, tài liệu này và version contract.
