# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Ngô Hữu Nghĩa |
| MSSV | 2A202601924 |
| Khóa/Lớp | K3 |
| Tên nhóm | fiveboiz |
| Vai trò chính | Config & Integrator — Pipeline Integration & Evidence Owner (Người 5) |
| Repository | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `src/pipelines/phase1.py` (`main()`, 10 bước) | `Settings`, raw records, các module của Người 1–4 | `data/clean/`, `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline_quality.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` (`main()`, 9 bước) | Baseline artifacts + `corrupt_clean_dataframe()`, `build_clean_dataframe()` | `data/clean/papers_clean_corrupted.*`, `papers_clean_repaired.*`, `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `data/quality/corrupted_*.json`, `repaired_*.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Entrypoint & runtime bootstrap | `script/run_phase1.py`, `script/run_corruption_flow.py` | — | Hai lệnh chạy được trên môi trường sạch, không bắt buộc `pip install -e .` | Hoàn thành |
| Config ownership | `src/core/config.py` (`Settings`, `Paths`, `load_settings`, `require_llm_credentials`) | `.env`, biến môi trường | Chốt bộ giá trị cấu hình chung cho cả nhóm; xác minh không hard-code secret/path | Hoàn thành (xem ghi chú bên dưới) |
| Evidence & consistency check | `data/reports/`, đối chiếu report ↔ artifact | Toàn bộ artifact trong `data/` | Xác minh mọi số liệu trong `group_report.md` khớp file JSON thực tế | Hoàn thành |

> **Ghi chú trung thực về `src/core/config.py`:** file này **đã được cung cấp hoàn chỉnh trong starter** (`git log -- src/core/config.py` chỉ có duy nhất commit `fae2342 first commit`), tôi **không viết mới** file này. Phạm vi "Config owner" của tôi là: chốt giá trị cấu hình nhóm sử dụng, hướng dẫn thành viên tạo `.env` từ `.env.example`, kiểm tra mọi module đọc đường dẫn qua `settings.paths` thay vì hard-code, và xác nhận không có key/secret nào lọt vào source hay artifact.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hoá lời gọi `LocalEmbeddingIndex.build(df, settings, embeddings_output_path=...)` trong cả 2 pipeline | Nguyễn Hữu Nhật Minh (Người 2 / `retrieval/index.py`) | 3 collection `papers-baseline` / `papers-corrupted` / `papers-repaired` được tạo đúng, không ghi đè nhau |
| Truyền cùng một `paths.eval_testset` vào cả 3 lần `evaluate_pipeline()` | Lý Thành Đạt (Người 3 / `testset.py`), Lê Văn Huy (Người 4 / `metrics.py`) | Đảm bảo so sánh apples-to-apples giữa baseline/corrupted/repaired |
| Truy vết nguyên nhân "4 stale rows" trong `corrupted_quality.json` | Bùi Văn Khởi (Người 1 / `corruption.py`) | Xác minh bằng `corruption_log.json` rằng đây là hành vi hợp lệ do overlap sampling, không phải bug (mục 6) |
| Xác minh chuỗi nhân quả drop → miss retrieval → tụt metric | Cả nhóm (`group_report.md` mục 10) | Chứng minh bằng số học chính xác, không suy đoán (mục 8) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Ghép 10 bước baseline end-to-end | `src/pipelines/phase1.py` | `main()` chạy trọn từ raw → clean → index → testset → eval → quality → report → agent demo | `uv run python script/run_phase1.py` in ra `[phase1] Baseline pipeline complete.` |
| Ghép 9 bước corruption → repair → compare | `src/pipelines/corruption_flow.py` | `main()` chạy trọn corrupt → re-index → eval → quality → repair → re-index → eval → compare | `uv run python script/run_corruption_flow.py` in ra dòng tổng kết `1.0 -> 0.667 -> 1.000` |
| Sửa lỗi import khi chạy entrypoint | `script/run_phase1.py:5-7`, `script/run_corruption_flow.py:4-7` | Thêm bootstrap `sys.path.insert(0, str(ROOT / "src"))` | Chạy `python script/run_phase1.py` trên venv **chưa** `pip install -e .` không còn `ModuleNotFoundError` |
| Thiết kế cơ chế đóng băng dữ liệu | `phase1.py:21-27` (`refresh_source`), `phase1.py:42-48` (`refresh_test_set`) | Mặc định tái sử dụng `crossref_records.json` và `test_set.json` có sẵn | Chạy lại `run_phase1.py` lần 2 → log in `Loading raw records from ...` và `Loading existing test set from ...` |
| Fail-fast khi thiếu tiền đề | `corruption_flow.py:21-24` | `RuntimeError` với thông điệp chỉ đúng lệnh cần chạy trước | Xoá tạm `data/results/baseline_metrics.json` rồi chạy Phase 2 → dừng ngay với message rõ ràng |
| Sinh và kiểm chứng báo cáo Markdown | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | 2 báo cáo tổng hợp source/metrics/quality/freshness cho 3 trạng thái | So từng dòng với `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `*_quality.json` |
| Đối chiếu report nhóm với artifact | `report/group_report.md` mục 7, 8, 10 | Xác nhận mọi con số trong báo cáo nhóm đều trích từ file JSON thực tế | Đọc trực tiếp các file trong `data/results/` và `data/quality/` |

**Artifact cụ thể tôi tạo ra:**

- `data/reports/phase1_report.md` — báo cáo baseline: 24 records fetched / 24 sau cleaning, 4 metric RAG, 6/6 quality check PASS, freshness 0/24 stale.
- `data/reports/corruption_report.md` — báo cáo so sánh 3 trạng thái, bảng quality corrupted (FAIL) vs repaired (PASS), kết luận `-0.333` / `+0.333` trên `retrieval_hit_rate`.
- Toàn bộ artifact trung gian của 2 flow (clean/corrupted/repaired dataset, 3 embedding manifest, 3 bộ metrics + answers, 3 quality report, 2 freshness report, corruption log) — được sinh ra bởi 2 pipeline tôi ghép.

**Thời điểm chạy được ghi lại trong artifact:**

| Flow | Timestamp (UTC) | Bằng chứng |
| --- | --- | --- |
| Baseline | `2026-08-06T03:49:44.896294+00:00` | `data/quality/baseline_quality.json` → `generated_at` |
| Corruption/repair | `2026-08-06T04:02:40.050212+00:00` | `data/results/corruption_log.json` → `generated_at` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bốn thành viên còn lại viết 4 nhóm module độc lập (ingestion/cleaning, embedding/index, testset/quality, LLM/agent/metrics). Nhiệm vụ của tôi là biến chúng thành **hai lệnh chạy được, tái lập được và tự sinh bằng chứng**, đồng thời đảm bảo 3 trạng thái dữ liệu (baseline / corrupted / repaired) được đo trên **cùng một thước đo** để phép so sánh có ý nghĩa.

### Cách triển khai

**a) `phase1.py` — baseline orchestration (10 bước)**

1. `load_settings()` một lần, `run_date = now_utc()` một lần → mọi bước dùng chung một mốc thời gian, nên `age_days` nhất quán trong toàn bộ một lần chạy.
2. Nhánh **load-or-fetch**: nếu `crossref_records.json` đã tồn tại và `REFRESH_SOURCE` không bật thì đọc lại từ đĩa, không gọi API.
3. `build_clean_dataframe(records, run_date)` + guard `if df.empty: raise RuntimeError(...)` để chặn trường hợp filter/threshold quá chặt làm rỗng dataset.
4. Ghi song song CSV + JSON qua `write_csv` / `write_json`.
5. `LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)`.
6. Nhánh **load-or-build test set**: chỉ sinh mới khi chưa có file hoặc `REFRESH_TEST_SET=1`.
7. `evaluate_pipeline(...)` → `baseline_metrics.json` + `baseline_answers.json`.
8. `run_data_quality_checks(df, settings, "baseline_quality")` + `build_freshness_report(...)`.
9. `generate_phase1_report(...)` → `data/reports/phase1_report.md`.
10. Demo agent trên 3 câu hỏi đầu, bọc trong `try/except` **best-effort**: nếu LLM lỗi (hết quota/mạng) thì ghi `{"error": ...}` vào `agent_demo_answers.json` và pipeline vẫn kết thúc thành công.

**b) `corruption_flow.py` — corruption/repair orchestration (9 bước)**

1. **Precondition check**: dừng ngay nếu thiếu `papers_clean.json`, `baseline_metrics.json` hoặc `crossref_records.json`.
2–3. `corrupt_clean_dataframe(baseline_df, paths.corruption_log)` → lưu CSV/JSON corrupted.
4. Re-index vào collection **riêng** (`papers-corrupted`) rồi `evaluate_pipeline` trên **đúng file test set cũ**.
5. Quality + freshness trên bản corrupted, ghi ra `corrupted_quality.json` / `corrupted_freshness_report.json`.
6. **Repair đúng nghĩa**: `load_raw_records(paths.raw_records_json)` rồi gọi lại chính `build_clean_dataframe()` — repaired dataset được dựng **độc lập hoàn toàn** với bản corrupted, không kế thừa bất kỳ giá trị lỗi nào, và **không fetch lại API** (nên repair vẫn tái lập được kể cả khi Crossref đã đổi dữ liệu).
7. Re-index vào `papers-repaired` + evaluate lại trên cùng test set.
8. Quality + freshness trên bản repaired.
9. `generate_corruption_report(...)` gộp 7 nguồn dữ liệu thành `corruption_report.md`.

**c) `script/*.py` — bootstrap runtime**

Starter import `from pipelines.phase1 import main`, mà `pipelines` chỉ nằm dưới `src/` (`pyproject.toml` khai báo `package-dir = {"" = "src"}`). Import này chỉ chạy được nếu project đã được cài editable. Tôi thêm 4 dòng bootstrap để `python script/run_phase1.py` chạy được ngay cả khi thành viên mới chỉ `pip install -r requirements.txt`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings` từ `load_settings()`; các hàm của Người 1–4: `fetch_source_records`/`load_raw_records`, `build_clean_dataframe`, `corrupt_clean_dataframe`, `LocalEmbeddingIndex.build`, `build_test_set`, `evaluate_pipeline`, `run_data_quality_checks`, `build_freshness_report`, `generate_*_report` |
| Output | Toàn bộ cây artifact `data/` + 2 báo cáo Markdown trong `data/reports/` |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.*`, `retrieval.index`, `retrieval.agent`, `evaluation.*`, `observability.*` |
| Module sử dụng output | `script/run_phase1.py`, `script/run_corruption_flow.py`; và bản thân `group_report.md` lấy số liệu từ artifact do 2 pipeline sinh ra |
| Contract tôi phải giữ | (1) không đổi chữ ký hàm của thành viên khác; (2) mọi đường dẫn lấy từ `settings.paths`, không hard-code; (3) truyền đúng `embeddings_output_path` để `_derive_collection_name()` chọn đúng collection; (4) cả 3 lần evaluate dùng **cùng** `paths.eval_testset` |
| Điều kiện lỗi cần xử lý | Cleaning ra dataframe rỗng → `RuntimeError`; thiếu baseline artifact khi chạy Phase 2 → `RuntimeError` có hướng dẫn; LLM demo lỗi → ghi error vào artifact, không làm fail pipeline |

### Cách xác minh

```bash
# 1. Baseline (phải chạy trước)
uv run python script/run_phase1.py

# 2. Corruption -> repair -> compare
uv run python script/run_corruption_flow.py

# 3. Đối chiếu report với artifact
uv run python -c "import json;print(json.load(open('data/results/baseline_metrics.json')));print(json.load(open('data/results/corrupted_metrics.json')));print(json.load(open('data/results/repaired_metrics.json')))"
```

- **Kết quả mong đợi:** Phase 1 kết thúc bằng `[phase1] Baseline pipeline complete.`; Phase 2 kết thúc bằng dòng tổng kết `baseline -> corrupted -> repaired retrieval_hit_rate`.
- **Kết quả thực tế:** Phase 2 in ra `1.0 -> 0.667 -> 1.000`. Ba file metrics khớp đúng với bảng trong `data/reports/corruption_report.md`.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/results/*_metrics.json`, `data/quality/*.json`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Bước repair trong `corruption_flow.py` có thể được cài theo hai hướng rất khác nhau, và lựa chọn này quyết định trực tiếp việc con số "phục hồi 100%" có đáng tin hay không.
- **Các phương án đã cân nhắc:**
  - *Phương án A — Repair tại chỗ (in-place):* đi từ `corrupted_df`, undo từng kịch bản (điền lại summary rỗng, khôi phục title bị cắt, sửa `published` về giá trị cũ, xoá dòng duplicate, thêm lại 2 record đã drop).
  - *Phương án B — Rebuild từ raw snapshot:* bỏ hẳn `corrupted_df`, gọi `load_raw_records(paths.raw_records_json)` rồi chạy lại đúng `build_clean_dataframe(raw_records, run_date)` — cùng hàm cleaning đã dùng ở Phase 1.
  - *Phương án C — Fetch lại Crossref API:* gọi lại `fetch_source_records(settings)`.
- **Phương án đã chọn:** **Phương án B** (`corruption_flow.py:60-61`).
- **Lý do:**
  1. Phương án A tạo ra **circular dependency về tính đúng đắn**: nếu logic undo có bug đối xứng với logic corrupt, metric vẫn trông "phục hồi" trong khi dữ liệu vẫn sai. Phương án B không đọc một byte nào từ bản corrupted, nên kết quả repaired là bằng chứng độc lập thật sự.
  2. Phương án A phải bám sát từng kịch bản corruption — thêm 1 kịch bản mới là phải viết thêm 1 hàm undo. Phương án B **bất biến với số lượng kịch bản**.
  3. Phương án C phá tính tái lập: Crossref là nguồn sống, chạy lại sau vài giờ sẽ trả về tập record khác → repaired không thể bằng baseline, và bài học "repair từ nguồn tin cậy" bị nhiễu bởi biến động dữ liệu.
- **Bằng chứng quyết định phù hợp:** `repaired_metrics.json` trùng **từng chữ số** với `baseline_metrics.json` (`retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=1.0`, `mean_judge_score=5`), và `repaired_quality.json` PASS đủ 6/6 check với đúng 24 rows. Đây là kết quả chỉ đạt được khi repaired dataset thực sự identical với baseline dataset, chứ không phải "gần đúng".

## 6. Một lỗi hoặc blocker đã xử lý

### 6.1. Lỗi đã xử lý — `ModuleNotFoundError` ở entrypoint

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  Traceback (most recent call last):
    File "script/run_phase1.py", line 3, in <module>
      from pipelines.phase1 import main
  ModuleNotFoundError: No module named 'pipelines'
  ```
- **Lệnh tái hiện:** `python script/run_phase1.py` trên một `.venv` mới chỉ cài `pip install -r requirements.txt` (chưa `pip install -e .`).
- **Nguyên nhân gốc:** `pyproject.toml` khai báo `package-dir = {"" = "src"}`, nên `pipelines`, `core`, `retrieval`… chỉ nằm trên `sys.path` sau khi project được cài editable. Khi chạy `python script/run_phase1.py`, Python chỉ thêm thư mục `script/` vào `sys.path`, không có `src/`.
- **Cách xử lý:** thêm bootstrap ở đầu cả 2 entrypoint, **trước** dòng import module nội bộ:
  ```python
  ROOT = Path(__file__).resolve().parent.parent
  SRC = ROOT / "src"
  sys.path.insert(0, str(SRC))
  ```
- **Cách xác minh sau khi sửa:** chạy lại cả 2 lệnh trên venv chưa cài editable — cả hai đều chạy trọn và sinh đủ artifact. Đường dẫn được tính từ `__file__` nên không phụ thuộc thư mục hiện hành khi gọi lệnh.
- **Điều học được:** entrypoint phải chạy được với cách cài **tối thiểu** mà thành viên trong nhóm thực sự dùng, không chỉ với cách cài "chuẩn" ghi trong README.

### 6.2. Nghi vấn đã điều tra — "4 stale rows" trong khi corruption chỉ làm cũ 3 record

- **Triệu chứng:** `corrupted_quality.json` và `corrupted_freshness_report.json` báo **4** rows older than 180 days, nhưng `corruption_log.json` ghi kịch bản `stale_publication_date` chỉ tác động **3** record. Ban đầu tôi nghi ngờ đây là bug đếm trùng ở tầng quality check.
- **Cách xác minh:** đối chiếu trực tiếp danh sách `paper_ids` giữa các kịch bản trong `data/results/corruption_log.json`.
- **Kết quả:** `10.2196/preprints.106157` xuất hiện đồng thời ở **cả hai** kịch bản `stale_publication_date` và `duplicate_rows`. Record này bị làm cũ trước, sau đó bị nhân đôi → xuất hiện 2 lần trong bảng cuối → được đếm 2 lần ở check freshness. **3 record gốc + 1 bản sao = 4.** Con số khớp chính xác, không có bug.
- **Kết luận:** đây là **hành vi hợp lệ**, không phải lỗi. Mỗi kịch bản trong `corruption.py` sample độc lập trên tập record còn lại nên các loại lỗi có thể chồng lên cùng một record — điều này phản ánh đúng thực tế dữ liệu bẩn. Nhóm giữ nguyên logic sampling độc lập.
- **Phát hiện thêm khi rà toàn bộ log:** có tổng cộng **3 cặp chồng lấn**, và **13/22 record** (59%) bị ít nhất một kịch bản tác động:

  | Paper ID | Chồng lấn giữa |
  | --- | --- |
  | `10.3390/buildings16132637` | `blank_summary` ∩ `truncate_title` |
  | `10.1007/s10278-026-02086-9` | `blank_summary` ∩ `add_noise_to_embedding_text` |
  | `10.2196/preprints.106157` | `stale_publication_date` ∩ `duplicate_rows` ← nguyên nhân của "4 stale rows" |

### 6.3. Blocker còn tồn đọng — `reporting.py` chưa được commit

- **Triệu chứng:** trên nhánh `main` hiện tại, `src/observability/reporting.py` vẫn ở trạng thái starter stub:
  ```text
  raise NotImplementedError("Student task: implement phase 1 report.")
  raise NotImplementedError("Student task: implement corruption comparison report.")
  ```
  trong khi `data/reports/phase1_report.md` và `data/reports/corruption_report.md` **đã tồn tại và có nội dung đúng**.
- **Cách xác minh:** `grep -rn "NotImplementedError" src/` chỉ còn trúng 2 dòng trong `reporting.py`; `git log --all -- src/observability/reporting.py` chỉ có duy nhất commit starter `fae2342`.
- **Nguyên nhân đã xác định:** hai hàm này đã được implement trên máy local khi chạy pipeline (nên artifact mới sinh ra được), nhưng **bản implement chưa được commit lên repo**.
- **Ảnh hưởng:** với repo ở trạng thái hiện tại, một người clone mới chạy `run_phase1.py` sẽ chạy trót lọt 8 bước rồi **crash ở bước 9** với `NotImplementedError` — tức là tiêu chí "một thành viên có thể chạy lại toàn bộ pipeline từ hướng dẫn chung" trong Definition of Done **chưa đạt trên bản commit**.
- **Bước tiếp theo:** owner của `reporting.py` (Người 3 / Người 4 — đồng sở hữu theo phân công nhóm) commit bản implement; sau đó tôi chạy lại cả 2 flow trên một clone sạch để xác nhận reproducibility trước khi nộp. Tôi ghi rõ trạng thái này thay vì đánh dấu hoàn thành, theo nguyên tắc báo cáo trung thực ở `report/README.md` mục 9.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index:** `fetch_source_records()` gọi `https://api.crossref.org/works` với query `agentic retrieval augmented generation large language model` và filter `from-pub-date:2026-02-07,has-abstract:true`, lưu raw response + raw records vào `data/raw/`. `build_clean_dataframe(records, run_date)` strip JATS XML khỏi title/summary, ghép `authors_joined`/`categories_joined`, tính `age_days` theo `run_date`, dựng `text_for_embedding = "Title: ... | Authors: ... | Summary: ..."`, drop record thiếu field bắt buộc hoặc summary quá ngắn → 24 record. `LocalEmbeddingIndex.build()` nhúng `text_for_embedding` bằng `all-MiniLM-L6-v2` (384 chiều) và nạp vào collection ChromaDB.

   Một chi tiết cấu hình quan trọng ở tầng orchestration: filter `from-pub-date` **được suy ra từ chính `freshness_threshold_days = 180`** (`config.py:73-74`). Nghĩa là ngưỡng freshness và bộ lọc ingestion là **một nguồn sự thật duy nhất** — baseline fresh **theo thiết kế**, chứ không phải may mắn. Bằng chứng số học: run date 2026-08-06, `from-pub-date` = 2026-02-07 (đúng 180 ngày trước), `oldest_published` = 2026-02-12 → `age_days` lớn nhất = 175 < 180, còn dư 5 ngày margin → `stale_rows = 0`.

2. **Evaluation set nối với ground-truth document IDs như thế nào:** `build_test_set()` sinh 9 câu hỏi frozen trên 3 paper đại diện (4 loại: summary/authors/date/categories), mỗi item mang `ground_truth` (đáp án text) và `ground_truth_doc_ids` (`paper_id` của chính paper đó). Trong `evaluate_pipeline()`, `retrieval_hit = any(doc_id in item["ground_truth_doc_ids"] for doc_id in result.retrieved_doc_ids)` — tức là hit khi paper gốc nằm trong top-k (`top_k = 4`) trả về. `mean_token_f1` so token giữa `ground_truth` và câu trả lời; `judge_accuracy`/`mean_judge_score` do LLM judge chấm.

3. **Quality checks khác Freshness monitoring ở đâu:** quality checks (`run_data_quality_checks`) trả lời "dữ liệu **hiện tại** có đúng contract không" — 6 check về completeness (`row_count_min`, `paper_id_not_null`, `title_not_null`), uniqueness (`paper_id_unique`) và validity (`summary_min_length`). Freshness (`build_freshness_report`) trả lời "dữ liệu có **còn kịp thời** không" — dựa trên `age_days` so với ngưỡng 180 ngày, kèm `latest_published`, `oldest_published`, `stale_ratio`. Một dataset có thể PASS toàn bộ completeness/uniqueness mà vẫn stale (đúng, đầy đủ, nhưng cũ) — đó là lý do freshness phải là tín hiệu riêng. Trong pipeline, `freshness_within_threshold` vừa là check thứ 6 của quality vừa được tách thành report độc lập để theo dõi xu hướng theo thời gian.

4. **Vì sao phải dùng cùng test set cho cả 3 trạng thái:** vì mục tiêu là đo tác động của **chất lượng dữ liệu**, nên chỉ được phép có một biến thay đổi. Nếu sinh lại test set từ `corrupted_df`, câu hỏi mới sẽ được sinh từ chính dữ liệu đã hỏng (ví dụ summary rỗng), ground truth sẽ "khớp" với dữ liệu hỏng và metric có thể **không giảm chút nào** — che mất đúng thứ ta cần phát hiện. Đây là lý do `phase1.py` chỉ sinh test set khi chưa tồn tại, và `corruption_flow.py` truyền `paths.eval_testset` (đọc file, không sinh mới) vào cả hai lần `evaluate_pipeline`.

5. **Repair được xem là thành công dựa trên artifact/metric nào:** thành công khi thoả đồng thời **3 tầng bằng chứng** — (a) tầng dữ liệu: `repaired_quality.json` PASS 6/6 với 24 rows, `repaired_freshness_report.json` có `stale_rows = 0`, `is_fresh = true`; (b) tầng chỉ số RAG: `repaired_metrics.json` = `baseline_metrics.json` (1.0 / 1.0 / 1.0 / 5); (c) tầng nguồn gốc: repaired dataset được dựng từ `crossref_records.json` chứ không phải sửa trên bản corrupted. Nếu chỉ có (b) mà thiếu (c) thì con số "phục hồi 100%" không chứng minh được điều gì.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Mất đúng 3/9 câu; là metric phản ứng trực tiếp nhất với việc document biến mất khỏi index |
| `mean_token_f1` | 1.000 | 0.667 | 1.000 | 3 câu miss có `token_f1 = 0.0` tuyệt đối — mất doc thì agent không có gì để trả lời đúng |
| `judge_accuracy` | 1.000 | 0.667 | 1.000 | Judge chấm sai đúng 3 câu tương ứng, không nhiều hơn không ít hơn |
| `mean_judge_score` | 5.000 | 3.778 | 5.000 | Giảm **nhẹ hơn tỷ lệ** vì judge cho partial credit (1, 1, 2 điểm) thay vì 0 |
| Quality checks | 6/6 PASS | 3/6 FAIL | 6/6 PASS | FAIL: `paper_id_unique`, `summary_min_length`, `freshness_within_threshold` |
| Freshness | Fresh (0/24) | Stale (4/24) | Fresh (0/24) | 3 record bị làm cũ + 1 bản sao của record đã cũ |
| Ragas | N/A (skipped) | N/A | N/A | `RUN_RAGAS=0` — tôi ghi rõ là **chưa chạy**, không suy đoán giá trị |

### Kết luận từ số liệu

Với vai trò evidence owner, tôi không dừng ở "metric giảm 0.333" mà truy ngược đến từng câu hỏi:

**1. [drop_latest_records] → [xoá `10.2118/234689-pa` khỏi corpus] → [q1/q2/q3 miss retrieval] → [cả 4 metric cùng giảm].**

Chuỗi này được xác minh bằng đối chiếu 3 artifact:

- `test_set.json`: 9 câu hỏi phân bố trên **đúng 3 paper**, mỗi paper 3 câu — `10.2118/234689-pa`, `10.47576/2949-1894.2026.7.7.023`, `10.55041/isjem07213`.
- `corruption_log.json` → `drop_latest_records` xoá `['10.2118/234689-pa', '10.1111/exsy.70341']`. Giao với tập ground-truth doc = **`{10.2118/234689-pa}`** — đúng 1 paper, kéo theo đúng 3 câu.
- `corrupted_answers.json`: đúng 3 item `q1`(summary), `q2`(authors), `q3`(date) có `retrieval_hit = false`, `token_f1 = 0.0`, judge score `1, 1, 2`. Sáu câu còn lại vẫn hit và vẫn được 5 điểm.

Phép tính khớp chính xác, không có phần dư cần giải thích:
`retrieval_hit_rate = 6/9 = 0.667` · `mean_token_f1 = 6/9 = 0.667` · `judge_accuracy = 6/9 = 0.667` · `mean_judge_score = (5×6 + 1 + 1 + 2)/9 = 34/9 = 3.778` ✓

**2. [Repair từ raw snapshot] → [dataset identical với baseline] → [phục hồi 100%, không phải "gần đúng"].**

Vì `corruption_flow.py:60-61` chạy lại đúng `build_clean_dataframe()` trên `crossref_records.json` với cùng logic cleaning, repaired dataset là bản tái tạo bit-level của baseline dataset. Hệ quả: index đủ 24 document, paper `10.2118/234689-pa` quay lại corpus, cả 9 câu hit lại, và cả 4 metric trở về **đúng bằng** baseline chứ không phải xấp xỉ. Đây là kiểm chứng gián tiếp rằng bản thân pipeline cleaning là **deterministic** — cùng input raw luôn cho cùng output clean.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records`. Lý do có tính cấu trúc, không phải ngẫu nhiên: đây là kịch bản duy nhất **xoá document khỏi ChromaDB**, trong khi 5 kịch bản còn lại chỉ làm nhiễu nội dung — document vẫn nằm trong index nên `index.lookup()` (exact-match theo title/paper_id) vẫn cứu được retrieval. Một điểm đáng chú ý củng cố nhận định này: `10.47576/2949-1894.2026.7.7.023` **cũng là paper trong test set** và **cũng bị `duplicate_rows` tác động**, nhưng cả 3 câu hỏi của nó vẫn `retrieval_hit = true` và vẫn được 5 điểm — nhân đôi một row làm FAIL quality check nhưng **không** làm hỏng retrieval. Nói cách khác: quality check bắt được nhiều loại lỗi hơn số loại lỗi thực sự làm hỏng agent, và đó chính là giá trị của observability — cảnh báo sớm trước khi lỗi kịp lan tới người dùng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về orchestration:** giá trị lớn nhất của lớp pipeline không nằm ở việc gọi hàm đúng thứ tự, mà ở các **guard và nhánh điều kiện** giữa các bước — precondition check, `df.empty` guard, load-or-fetch, load-or-build test set, try/except cho phần best-effort. Chúng biến một chuỗi lệnh thành thứ chạy lại được nhiều lần và báo lỗi ở đúng nơi có thể sửa.
2. **Về reproducibility:** tái lập không tự nhiên có. Nó đến từ những quyết định cụ thể: lưu raw snapshot ngay từ Phase 1 để repair không cần mạng, đóng băng test set để phép so sánh có nghĩa, seed cố định (42) cho corruption, và `run_date` tính một lần cho cả pipeline. Bỏ bất kỳ mảnh nào trong đó thì bảng so sánh 3 trạng thái mất giá trị chứng minh.
3. **Về vai trò integrator:** phần khó nhất không phải viết code ghép, mà là **kỷ luật đối chiếu**. Khi thấy "4 stale rows" trong khi log ghi 3, phản xạ dễ nhất là ghi đại một lời giải thích nghe hợp lý. Việc mở `corruption_log.json` ra so hai danh sách `paper_ids` mới cho câu trả lời chắc chắn — và cùng cách làm đó giúp tôi phát hiện `reporting.py` chưa được commit dù artifact đã tồn tại (mục 6.3).

### Nếu có thêm thời gian

Tôi sẽ thêm một bước **artifact validation** chạy tự động cuối mỗi pipeline: đọc lại toàn bộ file vừa ghi và assert các bất biến đã biết — số dòng CSV khớp `total_rows` trong quality report, số document trong index khớp số dòng dataset, `repaired_metrics.json` khớp `baseline_metrics.json` trong sai số cho phép, và mọi `paper_id` trong `ground_truth_doc_ids` phải tồn tại trong corpus tương ứng. Bước này sẽ biến việc kiểm tra thủ công tôi làm ở mục 6 và 8 thành một cổng kiểm soát tự động, chạy được trong CI, và sẽ **bắt được ngay** loại vấn đề như 6.3 (artifact tồn tại nhưng code sinh ra nó không có trong repo).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (xem mục 6.3 — blocker còn tồn đọng đã được ghi rõ thay vì đánh dấu hoàn thành).
- [x] Tôi không nhận ownership cho file mình không trực tiếp thực hiện (xem ghi chú về `src/core/config.py` ở mục 2).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Hữu Nghĩa
**Ngày xác nhận:** 2026-08-06
