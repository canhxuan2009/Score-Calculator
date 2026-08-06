# Hợp đồng dữ liệu

## 1. Quy ước chung

- `contract_version`: SemVer, bắt đầu dự kiến từ `1.0.0` khi triển khai.
- ID: chuỗi ổn định trong phạm vi một run; UUID/ULID sẽ chốt khi code.
- Điểm: decimal dưới dạng chuỗi trong JSON, ví dụ `"4.8"`, `"-5"`; `null` nghĩa là chưa biết/không áp dụng.
- Chỉ số hàng/cột Excel: 1-based. `source_span`: `[start, end)` 0-based trên chuỗi `cell_raw_text`.
- Ngày chuẩn: ISO `YYYY-MM-DD`; ngày thiếu năm chưa được giả lập thành ngày đầy đủ nếu chưa có policy.
- Tất cả enum viết hoa với dấu gạch dưới.
- `warnings` là danh sách có thứ tự ổn định, không phải chuỗi ghép.

## 2. RunRecord

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---:|---|
| `run_id` | string | có | định danh lần chạy |
| `contract_version` | string | có | phiên bản schema |
| `application_version` | string | có | phiên bản ứng dụng |
| `started_at`, `finished_at` | datetime/null | có | UTC ISO-8601 |
| `status` | enum | có | `RUNNING`, `FAILED`, `PARTIAL`, `PROVISIONAL`, `FINALIZED` |
| `source` | SourceWorkbook | có | metadata nguồn |
| `header` | HeaderMapping/null | có | kết quả nhận diện header |
| `rule_catalog` | RuleCatalogRef | có | version/checksum |
| `ai_context` | AiContext/null | có | model/prompt/schema version, không chứa secret |
| `persons` | PersonResult[] | có | kết quả theo người |
| `warnings` | Warning[] | có | cảnh báo cấp run |

## 3. SourceWorkbook

| Trường | Kiểu | Mô tả |
|---|---|---|
| `file_name` | string | tên hiển thị, không nhất thiết là đường dẫn tuyệt đối |
| `sha256_before` | string | hash trước xử lý |
| `sha256_after` | string | hash sau xử lý |
| `sheet_count` | integer | phải bằng 1 để chạy nghiệp vụ |
| `sheet_name` | string/null | sheet được xử lý |
| `read_only` | boolean | phải là `true` |

Ràng buộc nghiệm thu: `sha256_before == sha256_after`.

## 4. HeaderMapping và nguồn ô

`HeaderMapping` gồm `header_row`, `confidence` và map từ canonical field sang `CellRef`.

`CellRef`:

| Trường | Kiểu | Mô tả |
|---|---|---|
| `sheet_name` | string | tên sheet |
| `row_index` | integer | 1-based |
| `column_index` | integer | 1-based |
| `coordinate` | string | ví dụ `J12` |
| `header_raw` | string/null | tiêu đề vật lý nếu áp dụng |

## 5. PersonSourceRecord

| Trường | Kiểu | Mô tả |
|---|---|---|
| `person_id` | string | ID nội bộ, không chỉ dựa vào tên |
| `source_row` | integer | hàng nguồn |
| `row_class` | enum | `PERSON_ROW` đối với record hợp lệ |
| `sequence_raw` | scalar/null | TT gốc |
| `full_name_raw` | string | họ tên nguyên bản |
| `birth_date_raw` | scalar/null | ngày sinh nguyên bản |
| `group_raw` | scalar/null | tổ nguyên bản |
| `base_score_raw` | scalar/null | điểm gốc nguyên bản |
| `base_score` | decimal/null | điểm gốc parse được |
| `source_bonus_raw` | scalar/null | điểm cộng trong file |
| `source_bonus` | decimal/null | giá trị parse được |
| `source_penalty_raw` | scalar/null | điểm trừ trong file, quy ước độ lớn không âm |
| `source_penalty` | decimal/null | giá trị parse được |
| `source_total_raw` | scalar/null | tổng trong file |
| `source_total` | decimal/null | giá trị parse được |
| `conduct_raw` | scalar/null | hạnh kiểm gốc |
| `evidence_cell` | EvidenceCell | nguồn Minh chứng |
| `warnings` | Warning[] | cảnh báo hàng |

## 6. EvidenceCell

| Trường | Kiểu | Mô tả |
|---|---|---|
| `cell_ref` | CellRef | tọa độ nguồn |
| `cell_raw_text` | string | toàn bộ văn bản ô, không sửa |
| `events` | EventRecord[] | sự kiện theo thứ tự nguồn |

## 7. EventRecord

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---:|---|
| `event_id` | string | có | ID ổn định trong run |
| `person_id` | string | có | tham chiếu người |
| `source_cell` | CellRef | có | hàng/cột/ô nguồn |
| `source_span` | object/null | có | `start`, `end`; null nếu không xác định an toàn |
| `raw_text` | string | có | văn bản sự kiện nguyên bản |
| `normalized_content` | string | có | nội dung chuẩn hóa phục vụ khớp |
| `event_date_raw` | string/null | có | ngày như được viết |
| `event_date` | date/null | có | ngày ISO khi xác định đủ |
| `subject` | string/null | có | mã/tên môn chuẩn |
| `subject_score_raw` | string/null | có | điểm môn nguyên bản |
| `subject_score` | decimal/null | có | điểm môn đã parse |
| `declared_delta_raw` | string/null | có | delta nguyên bản |
| `declared_delta` | decimal/null | có | delta có dấu trong Minh chứng |
| `expected_delta` | decimal/null | có | delta do Rule Engine tạo |
| `final_delta` | decimal/null | có | delta cuối đã được phép dùng |
| `matched_rule` | RuleMatch/null | có | rule và trace |
| `parse_confidence` | decimal | có | `[0,1]`, không phải xác suất pháp lý |
| `warnings` | Warning[] | có | cảnh báo event |
| `review_status` | enum | có | trạng thái duyệt |
| `review_decision_id` | string/null | có | quyết định gần nhất |
| `duplicate_group_id` | string/null | có | nhóm nghi trùng |

Ràng buộc:

1. `raw_text` phải bằng substring theo `source_span` nếu span tồn tại.
2. `expected_delta` chỉ tồn tại khi có đúng một rule hợp lệ hoặc quyết định có trace tương đương theo policy.
3. Có `RULE_CONFLICT` ⇒ `review_status = PENDING_REVIEW` và `final_delta = null` cho tới khi có quyết định người dùng.
4. `review_status = AUTO_ACCEPTED` hoặc `APPROVED` và sự kiện được tính ⇒ `final_delta != null`.
5. `review_status = REJECTED` ⇒ `final_delta = null`.
6. `declared_delta`, `expected_delta`, `final_delta` là số có dấu: cộng dương, trừ âm.

## 8. RuleCatalog và RuleMatch

`RuleCatalogRef`:

- `catalog_id`
- `version`
- `effective_from`, `effective_to`
- `sha256`

Một rule logic tối thiểu gồm:

- `rule_id`, `version`, `name`, `priority`, `enabled`;
- thời gian hiệu lực;
- điều kiện có cấu trúc (event type, subject, score range, achievement, keyword/alias đã duyệt...);
- `delta` có dấu;
- `explanation` và examples/tests.

`RuleMatch`:

| Trường | Kiểu | Mô tả |
|---|---|---|
| `status` | enum | `NO_MATCH`, `ONE_MATCH`, `AMBIGUOUS_MATCH` |
| `rule_id` | string/null | chỉ có khi `ONE_MATCH` |
| `rule_version` | string/null | phiên bản rule |
| `candidate_rule_ids` | string[] | ứng viên đã xét/đồng hạng |
| `trace` | object[] | điều kiện và kết quả, không chứa suy luận AI tự do |

## 9. ReviewDecision

| Trường | Kiểu | Mô tả |
|---|---|---|
| `decision_id` | string | ID append-only |
| `event_id` | string | sự kiện được duyệt |
| `action` | enum | `USE_DECLARED`, `USE_EXPECTED`, `SET_CUSTOM`, `REJECT_EVENT`, `EDIT_PARSED_FIELDS` |
| `final_delta` | decimal/null | bắt buộc với ba action chọn/đặt điểm |
| `reason` | string | bắt buộc, không rỗng |
| `reviewer_id` | string | người/hệ thống theo policy |
| `created_at` | datetime | UTC ISO-8601 |
| `previous_decision_id` | string/null | chuỗi lịch sử |

`EDIT_PARSED_FIELDS` không tự phê duyệt điểm; nó tạo phiên bản event mới hoặc revision, chạy lại rule engine rồi trở về policy duyệt.

## 10. Review status

- `UNREVIEWED`: đã parse nhưng chưa đủ điều kiện quyết định.
- `PENDING_REVIEW`: có cảnh báo chặn hoặc cần lựa chọn người dùng.
- `AUTO_ACCEPTED`: policy xác định đã đặt final an toàn.
- `APPROVED`: người dùng đã duyệt.
- `REJECTED`: người dùng loại sự kiện.

## 11. PersonResult và công thức

| Trường | Kiểu | Mô tả |
|---|---|---|
| `person` | PersonSourceRecord | dữ liệu nguồn |
| `calculation_status` | enum | `BLOCKED`, `PROVISIONAL`, `FINALIZED` |
| `calculated_bonus` | decimal/null | tổng delta dương |
| `calculated_penalty` | decimal/null | tổng trị tuyệt đối delta âm |
| `calculated_total` | decimal/null | tổng mới |
| `bonus_difference` | decimal/null | mới trừ nguồn |
| `penalty_difference` | decimal/null | mới trừ nguồn |
| `total_difference` | decimal/null | mới trừ nguồn |
| `blocking_event_count` | integer | số event chưa giải quyết |
| `warnings` | Warning[] | cảnh báo đối soát |

Với `included_events = status in {AUTO_ACCEPTED, APPROVED} and final_delta != null`:

```text
calculated_bonus   = Σ max(final_delta, 0)
calculated_penalty = Σ abs(min(final_delta, 0))
calculated_total   = base_score + calculated_bonus - calculated_penalty
bonus_difference   = calculated_bonus - source_bonus
penalty_difference = calculated_penalty - source_penalty
total_difference   = calculated_total - source_total
```

Nếu `base_score` thiếu/không hợp lệ, `calculated_total = null` và status `BLOCKED`. Nếu một source comparison value là null, difference tương ứng là null.

## 12. Warning

| Trường | Kiểu | Mô tả |
|---|---|---|
| `code` | enum/string ổn định | mã máy đọc được |
| `severity` | enum | `INFO`, `WARNING`, `ERROR`, `BLOCKING` |
| `message_vi` | string | thông điệp cho người dùng |
| `scope` | enum | `RUN`, `ROW`, `CELL`, `EVENT`, `CALCULATION` |
| `source_ref` | CellRef/null | nguồn nếu có |
| `details` | object | dữ liệu có cấu trúc, đã giảm PII |

`RULE_CONFLICT`, `AMBIGUOUS_RULE_MATCH`, `DUPLICATE_CANDIDATE` và `UNRESOLVED_EVENT` mặc định là cảnh báo chặn event cho tới khi reviewer quyết định.

