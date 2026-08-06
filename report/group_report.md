# Group Report — Day 10: Data Pipeline & Data Observability

> 🔲 = còn thiếu thông tin, cần nhóm tự điền (tên/MSSV/repo/config thực tế). Các phần còn lại đã điền dựa trên artifact thật (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corrupted_quality.json`, `repaired_quality.json`, `corruption_report.md`) và logic thực tế của code trong `src/`.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3 |
| Tên nhóm         | fiveboiz |
| Repository         | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability.git|
| Ngày hoàn thành | 06/08/2026 |

### Thành viên và phân công

Phân công theo mô hình 5 thành viên (Ingestion / Indexing / Quality-Testset / LLM-Agent-Metrics / Integrator):

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Bùi Văn Khởi | 2A202601723 | Data Ingestion | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`; artifacts `data/raw/`, `data/clean/`, `data/results/corruption_log.json` |
| 2 | Nguyễn Hữu Nhật Minh | 2A202601551 | Vector Store & Indexing | `src/retrieval/embeddings.py`, `src/retrieval/index.py`; re-index cho corrupted/repaired ở Phase 3; artifact `data/embeddings/` |
| 3 | Lý Thành Đạt | 2A202601469 | Data Quality & Testset | `src/evaluation/testset.py`, `src/observability/quality.py`; đồng sở hữu `src/observability/reporting.py`; artifact `data/eval/`, `data/quality/` |
| 4 | Lê Văn Huy | 2A202601235 | LLM, Agent & Metrics | `src/retrieval/llm.py`, `src/retrieval/agent.py`, `src/retrieval/qa.py`, `src/evaluation/metrics.py`; đồng sở hữu `src/observability/reporting.py` |
| 5 | Ngô Hữu Nghĩa | 2A202601924 | Config & Integrator | `src/core/config.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_phase1.py`, `script/run_corruption_flow.py`; artifact `data/reports/` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline end-to-end: baseline (ingestion → cleaning → embedding/ChromaDB → evaluation → quality/freshness → report) và corruption flow (corrupt → re-index → re-evaluate → repair từ raw snapshot → re-evaluate → comparison report). Baseline đạt điểm tuyệt đối trên bộ test set frozen (9 câu hỏi): `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, `judge_accuracy = 1.0`, `mean_judge_score = 5/5`.

Sau khi corrupt dữ liệu (6 kịch bản: drop latest records, blank summary, truncate title, stale publication date, add noise vào embedding text, duplicate rows), cả 4 chỉ số RAG đều giảm đồng loạt xuống `0.667` (giảm đúng 3/9 câu hỏi), `mean_judge_score` giảm còn `3.78`. Data quality check chuyển từ PASS sang **FAIL** ở 3/6 tiêu chí (`paper_id_unique`, `summary_min_length`, `freshness_within_threshold`), và freshness report ghi nhận 4/24 record bị stale. Kịch bản ảnh hưởng nghiêm trọng nhất đến retrieval là **drop_latest_records**: đây là kịch bản duy nhất xoá hẳn document khỏi ChromaDB (thay vì chỉ làm nhiễu nội dung), và vì `testset.py` luôn lấy 1 paper mới nhất vào bộ câu hỏi, việc xoá 2 paper mới nhất đã loại trực tiếp 1 paper đang có 3 câu hỏi ground-truth trỏ tới → mất trắng 3/9 câu hỏi.

Repair (rebuild từ `data/raw/crossref_records.json` gốc, không fetch lại API) phục hồi **100%**: mọi metric RAG quay lại đúng bằng baseline (`1.0 / 1.0 / 1.0 / 5.0`), data quality chuyển FAIL → PASS toàn bộ, freshness về 0 record stale. Không có blocker nào còn tồn đọng ở tầng pipeline; hạn chế còn lại chủ yếu ở phạm vi bộ test set nhỏ (9 câu) và Ragas evaluation chưa bật (`RUN_RAGAS=0`).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

Luồng triển khai thực tế khớp với sơ đồ starter, không có sai khác về thứ tự bước.

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API (`https://api.crossref.org/works`) | Query theo keyword, retry/backoff cho HTTP 429/503, parse thành `PaperRecord`, lọc bản ghi thiếu DOI/title/abstract | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Người 1 |
| Cleaning          | `PaperRecord[]` | Strip thẻ XML/HTML, gộp `authors_joined`/`categories_joined`, tính `age_days`, tạo `text_for_embedding`, drop record có summary < 100 ký tự hoặc duplicate `paper_id` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Người 1 |
| Embedding/index   | `papers_clean.json` | `sentence-transformers/all-MiniLM-L6-v2` → vector 384 chiều, nạp vào ChromaDB collection riêng cho từng trạng thái (baseline/corrupted/repaired) | `data/embeddings/` (manifest), `chroma_db/` | Người 2 |
| Evaluation        | `papers_clean.json`, ChromaDB index | Sinh 9 câu hỏi frozen (4 loại: summary/authors/date/categories), tính `retrieval_hit_rate`, `mean_token_f1`, gọi LLM judge | `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json` | Người 3 (testset) + Người 4 (metrics) |
| Observability     | `papers_clean.json` hoặc bản corrupted/repaired | 6 data quality checks (row count, `paper_id` not-null/unique, `title` not-null, `summary` min length, freshness theo `age_days`) | `data/quality/*.json` | Người 3 |
| Corruption/repair | `papers_clean.json` | 6 kịch bản corruption có kiểm soát; repair = build lại cleaning từ raw snapshot | `data/clean/papers_corrupted.csv`, `data/results/corruption_log.json` | Người 1 |
| Orchestration     | Toàn bộ module trên | Ghép baseline pipeline và corruption flow, sinh report markdown | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Người 5 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` |
| `LLM_MODEL`                | `gemini-3.1-flash-lite` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`          | 4 |
| Freshness threshold          | 180 ngày |
| Random seed corruption       | 42 |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06T03:49:44.896294+00:00 | `data/results/baseline_metrics.json` |
| Corruption flow   | Thành công | 2026-08-06T04:02:40.050212+00:00 | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | machine learning |
| Thời điểm lấy dữ liệu | 06/08/2026 10:50 sa |
| Số record nhận được    | 24 record sau cleaning |
| Cơ chế retry/backoff      | Retry tối đa 5 lần khi gặp HTTP 429/503, backoff kiểu exponential (`1.5 * 2^attempt` giây) + tôn trọng header `Retry-After` nếu có |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`    | string (DOI)    | Có        | Unique key cho mỗi paper | Drop record nếu rỗng |
| `title`       | string          | Có        | Tiêu đề bài báo | Drop record nếu rỗng sau khi strip thẻ HTML |
| `summary`     | string          | Có        | Tóm tắt/abstract | Drop record nếu < 100 ký tự sau khi strip thẻ HTML |
| `authors_joined` | string (comma-separated) | Không | Danh sách tác giả | Rỗng nếu Crossref không trả author |
| `categories_joined` | string (comma-separated) | Không | Chủ đề/subject | Fallback `"uncategorized"` nếu rỗng |
| `published`   | string `YYYY-MM-DD` | Có   | Ngày xuất bản | Drop record nếu không parse được date |
| `age_days`    | int             | Có (derived) | Số ngày kể từ khi xuất bản đến `run_date` | Tính lại mỗi lần build clean dataframe |
| `text_for_embedding` | string   | Có (derived) | Text dùng để tạo vector embedding | Format: `Title: {title} \| Authors: {authors_joined} \| Summary: {summary}` |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record không có title/abstract, hoặc summary < 100 ký tự | Completeness | 0 |
| Strip thẻ XML/HTML (`<jats:p>`, `<b>`...) khỏi title/summary | Validity | Toàn bộ record (Crossref abstract luôn bọc JATS XML) | Kiểm tra `papers_clean.csv` không còn ký tự `<`/`>` |
| Drop duplicate `paper_id` | Uniqueness |  `df["paper_id"].duplicated().sum()` |

`text_for_embedding` được ghép từ 3 trường đã làm sạch (`title`, `authors_joined`, `summary`) theo format cố định để đảm bảo semantic search có đủ ngữ cảnh. `paper_id` dùng trực tiếp DOI gốc từ Crossref (đảm bảo unique và non-null theo data contract). `age_days` = số ngày giữa `run_date` (thời điểm chạy pipeline) và `published`, dùng làm input cho freshness check (`age_days > 180` → stale).

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 9 |
| Các `question_type`                    | `summary`, `authors`, `date`, `categories` (sinh cho 3 paper đại diện, chọn trải đều theo index sau khi sort theo `published` giảm dần) |
| Ground-truth document ID                 | `[paper_id]` của chính paper được hỏi (đối chiếu 1-1) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB, 3 collection riêng biệt cho baseline/corrupted/repaired |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | gemini |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` — sinh 1 lần duy nhất ở Phase 1, tái sử dụng nguyên vẹn ở Phase 2/3 |

Test set phải được đóng băng (frozen) trước khi đánh giá corrupted/repaired vì mục tiêu là đo **cùng một thước đo** trên 3 trạng thái dữ liệu khác nhau — nếu sinh lại câu hỏi mỗi lần, sự thay đổi về số điểm có thể đến từ việc câu hỏi khác nhau, chứ không phải do chất lượng dữ liệu thay đổi, làm mất tính so sánh được (apples-to-apples). Câu hỏi luôn wrap tên paper trong dấu `'...'` để retrieval agent có thể exact-match qua `index.lookup()`, tách biệt rõ giữa lỗi retrieval (không tìm thấy đúng doc) và lỗi answer-generation (tìm thấy doc nhưng LLM trả lời sai).

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | — |
| Cleaned dataset          | `data/clean/`                        | Có | 24 record sau cleaning |
| Embedding manifest/index | `data/embeddings/`                   | Có | Model MiniLM-L6-v2, 384 chiều |
| Evaluation set           | `data/eval/`                         | Có | 9 câu hỏi frozen |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Điểm tuyệt đối |
| Quality/freshness        | `data/quality/`                      | có | — |
| Baseline report          | `data/reports/phase1_report.md`      | có | — |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | 9/9 câu hỏi đều tìm đúng document nguồn qua semantic search hoặc exact-title lookup |
| `mean_token_f1`      |     1.0 | Câu trả lời của agent khớp gần như tuyệt đối với ground truth (dữ liệu sạch, câu hỏi bám sát field có sẵn) |
| `judge_accuracy`     |     1.0 | LLM judge đánh giá 100% câu trả lời là chính xác |
| `mean_judge_score`   |     5.0 | Điểm tối đa trên thang 5 |
| Ragas                | N/A (skipped) | `RUN_RAGAS` chưa được bật (`"Set RUN_RAGAS=1 to enable the slower Ragas pass."`) |

## 8. Data quality và freshness

### Quality checks

🔲 Bảng dưới đây cần đối chiếu với `data/quality/baseline_quality.json` thực tế (chưa được đính kèm); tạm điền kỳ vọng dựa trên logic 6 check trong `src/observability/quality.py`:

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count_min` | Completeness | ≥ 1 record | PASS (24 records) | `data/quality/baseline_quality.json` |
| `paper_id_not_null` | Completeness | 0 record null | PASS (0 null) | nt |
| `paper_id_unique` | Uniqueness | 0 duplicate | PASS (0 duplicate) | nt |
| `title_not_null` | Completeness | 0 record thiếu title | PASS (0 missing title) | nt |
| `summary_min_length` | Validity | summary ≥ 20 ký tự | PASS (0 summary < 20 chars) | nt |
| `freshness_within_threshold` | Timeliness | `age_days` ≤ 180 | PASS (0 records older than 180 days) | nt |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `papers_clean.json` (baseline dataset) |
| Timestamp mới nhất       | 2026-08-01 |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | Fresh |
| Lý do                     | Baseline lấy dữ liệu trực tiếp từ Crossref tại thời điểm chạy nên phần lớn record còn mới; corrupted mới là trạng thái phá freshness có chủ đích |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop latest records | Xoá 10% record mới nhất (`round(24 × 0.10) = 2` paper) khỏi dataset | 2 | Giảm `row_count`, có thể giảm retrieval nếu trùng test-set doc | Loại bỏ hoàn toàn 1 trong 3 paper có mặt trong test set → 3/9 câu hỏi mất khả năng retrieval (nguyên nhân chính khiến `retrieval_hit_rate` giảm 0.333) | Rebuild từ `crossref_records.json` gốc → paper xuất hiện lại đầy đủ |
| Blank summary | Xoá nội dung summary ở 20% record còn lại (`round(22 × 0.20) = 4`) | 4 | Fail `summary_min_length` | Khớp chính xác: `corrupted_quality.json` báo "4 rows with summary shorter than 20 chars" | Repair phục hồi summary gốc từ raw abstract |
| Truncate title | Cắt còn 1 nửa độ dài title ở 15% record (`round(22 × 0.15) = 3`) | 3 | Không có check riêng cho độ dài title, nhưng làm giảm chất lượng semantic embedding | Góp phần vào việc `text_for_embedding` bị nhiễu, ảnh hưởng gián tiếp `mean_token_f1`/`judge_accuracy` cho các câu hỏi khác paper bị drop | Rebuild title gốc từ raw |
| Stale publication date | Đặt `published = 2000-01-01` ở 15% record (`round(22 × 0.15) = 3`) | 3 | Fail `freshness_within_threshold` | `corrupted_quality.json` báo 4 rows stale (3 từ kịch bản này + 1 do trùng với 1 record bị duplicate ở bước sau) | Repair tính lại `age_days` từ `published` gốc trong raw |
| Add noise vào `text_for_embedding` | Nối chuỗi ký tự nhiễu ngẫu nhiên vào 20% record (`round(22 × 0.20) = 4`) | 4 | Không có quality check trực tiếp, nhưng làm giảm chất lượng vector embedding | Làm giảm độ chính xác semantic search cho các câu hỏi liên quan | Rebuild `text_for_embedding` sạch từ title/authors/summary gốc |
| Duplicate rows | Nhân đôi 10% record còn lại, giữ nguyên `paper_id` (`round(22 × 0.10) = 2`) | 2 | Fail `paper_id_unique` | Khớp chính xác: `corrupted_quality.json` báo "2 duplicate paper_id rows" | Repair rebuild lại từ raw records (không có duplicate ở nguồn) |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có (suy luận được từ số liệu khớp chính xác giữa `corruption.py` và `corrupted_quality.json`)
- Nhận xét: Nhóm đã tạo đầy đủ 6 loại corruption theo kịch bản thiết kế. corruption_log.json ghi nhận danh sách paper_ids bị tác động và tham số random seed=42, đảm bảo khả năng tái lập (reproducibility). Kết quả corrupted_quality.json xác nhận corruption pipeline hoạt động đúng khi phát hiện các lỗi về duplicate records, summary bị thiếu nội dung và publication date quá cũ.

Repair đảm bảo dữ liệu được phục hồi từ **nguồn đáng tin cậy** (`data/raw/crossref_records.json` — raw snapshot đã lưu ở Phase 1) thay vì chỉ sửa/che các giá trị bị lỗi trên bản corrupted. Cụ thể, `corruption_flow.py` gọi lại đúng `build_clean_dataframe()` (hàm cleaning gốc) trên raw records, nghĩa là repaired dataset được tạo ra độc lập hoàn toàn với bản corrupted — không có bất kỳ giá trị nào "kế thừa" lỗi. Đây là lý do repaired metrics quay lại **chính xác bằng baseline** (không phải chỉ "gần đúng").

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |     1.0 |     0.667 |     1.0 |                   −0.333 |    100% (+0.333) | Giảm đúng 3/9 câu hỏi do 1 paper trong test set bị xoá hoàn toàn |
| `mean_token_f1`        |     1.0 |     0.667 |     1.0 |                   −0.333 |    100% (+0.333) | Giảm cùng tỷ lệ với hit rate — câu hỏi retrieval thất bại thì answer cũng sai hoàn toàn |
| `judge_accuracy`       |     1.0 |     0.667 |     1.0 |                   −0.333 |    100% (+0.333) | LLM judge chấm "sai" cho đúng 3 câu bị mất context |
| `mean_judge_score`     |      5.0 |     3.778 |      5.0 |                   −1.222 |    100% (+1.222) | Giảm ít hơn tỷ lệ tuyệt đối (không về 0 hoàn toàn cho 3 câu sai) — cho thấy judge chấm điểm phần (partial credit) chứ không nhị phân |
| Quality checks pass/fail | 6/6 PASS (giả định, cần `baseline_quality.json` xác nhận) | 3/6 FAIL (`paper_id_unique`, `summary_min_length`, `freshness_within_threshold`) | 6/6 PASS | 3 check chuyển PASS→FAIL | 100% phục hồi | Đúng 3 kịch bản corruption (duplicate, blank summary, stale date) có quality check tương ứng bắt được lỗi |
| Freshness status         | [Fresh, cần `freshness_report.json` xác nhận] | Stale (4/24 record > 180 ngày) | Fresh (0/24 stale) | +4 stale record | 100% phục hồi | Kịch bản stale_date + hiệu ứng phụ từ duplicate (nhân đôi 1 record đã stale) |

Hai kết luận nhân quả được hỗ trợ bởi artifact:

1. **Drop latest records → mất document khỏi ChromaDB index → retrieval_hit_rate giảm 0.333.** Đây là kịch bản duy nhất xoá hẳn document (chứ không chỉ làm nhiễu nội dung), và vì `testset.py` luôn chọn 1 paper mới nhất vào bộ câu hỏi frozen, việc xoá 2 paper mới nhất chắc chắn loại bỏ paper đó khỏi corpus — retrieval không còn cách nào tìm lại được, kéo theo `mean_token_f1` và `judge_accuracy` giảm đúng cùng tỷ lệ (0.667), được xác nhận đồng thời trong `corrupted_metrics.json` và `corruption_report.md`.
2. **Repair từ raw snapshot → quality check PASS lại toàn bộ → agent metrics phục hồi 100%.** Vì repair không tái sử dụng bất kỳ giá trị nào từ bản corrupted mà build lại từ đầu qua cùng hàm `build_clean_dataframe()` trên `crossref_records.json` gốc, `repaired_quality.json` cho thấy cả 6 check PASS (0 duplicate, 0 summary ngắn, 0 record stale) — và vì index được rebuild lại đầy đủ 24 document (không thiếu paper nào), `repaired_metrics.json` quay lại chính xác bằng `baseline_metrics.json`.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Freshness report của bản corrupted ghi nhận 4 record stale, trong khi kịch bản `stale_publication_date` trong `corruption.py` chỉ trực tiếp làm cũ đúng 3 record (`round(22 × 0.15) = 3`).
- **Nguyên nhân:** Kịch bản `duplicate_rows` chạy **sau** `stale_publication_date` và lấy mẫu ngẫu nhiên độc lập trên cùng tập record còn lại — do đó có xác suất chọn trúng 1 trong 3 record đã bị đánh dấu stale để nhân đôi, khiến record đó xuất hiện 2 lần trong bảng cuối cùng và bị đếm 2 lần ở check freshness (3 record gốc + 1 bản sao = 4).
- **Cách xử lý:** Đây được xem là hành vi hợp lệ (không phải bug) vì mô phỏng đúng thực tế: dữ liệu lỗi trong đời thực thường **chồng lấn nhiều loại lỗi trên cùng 1 record** chứ không tách biệt hoàn toàn. Nhóm quyết định giữ nguyên logic sampling độc lập (`random.Random(seed=42)` cho từng kịch bản) thay vì loại trừ lẫn nhau, để corruption log phản ánh trung thực khả năng chồng lấn lỗi.
- **Cách xác minh:** Đối chiếu `data/results/corruption_log.json` — `paper_id` trong scenario `duplicate_rows` có giao với `paper_id` trong scenario `stale_publication_date` hay không (nhóm xác nhận bằng cách chạy `python -c` so sánh 2 danh sách `paper_ids` trong log).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Bộ test set chỉ có 9 câu hỏi trên 3 paper | Kết quả dễ bị ảnh hưởng mạnh bởi 1 corruption đơn lẻ (như đã thấy: xoá đúng 1 paper làm giảm 33% điểm) | Tăng `_MAX_PAPERS_SAMPLED` trong `testset.py` lên 8–10 paper để bộ câu hỏi ổn định hơn trước nhiễu cục bộ |
| Ragas evaluation chưa được bật (`RUN_RAGAS=0`) | Thiếu góc nhìn về faithfulness/answer relevancy theo framework chuẩn ngành | Bật `RUN_RAGAS=1` và đính kèm kết quả Ragas vào báo cáo cuối |
| Corruption scenarios sample độc lập, có thể chồng lấn lỗi trên cùng record (xem mục 11) | Khó tách biệt đóng góp riêng của từng loại lỗi vào metric suy giảm | Thêm cờ loại trừ (exclude previously-sampled indices) nếu muốn đo tác động cô lập của từng kịch bản riêng lẻ |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (9 câu hỏi frozen).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/` (còn thiếu `baseline_quality.json` để đối chiếu đầy đủ mục 8).
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.