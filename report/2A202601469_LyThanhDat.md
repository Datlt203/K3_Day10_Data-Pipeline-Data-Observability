# Member Role Report — Day 10: Data Pipeline & Data Observability

> 🔲 = còn thiếu thông tin cá nhân/hành chính, bạn tự điền (MSSV, lớp, tên nhóm, repo, ngày). Phần kỹ thuật đã điền dựa trên code thật của `testset.py`, `quality.py` và metrics thật đã trao đổi trong quá trình làm bài.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lý Thành Đạt |
| MSSV               | 2A202601469 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | fiveboiz |
| Vai trò chính    | Data Quality & Testset Owner (Người 3) |
| Repository         | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 06/08/2026 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Frozen evaluation set | `src/evaluation/testset.py` — `build_test_set()` | `papers_clean.json` (DataFrame đã cleaning từ Người 1) | `data/eval/test_set.json` — 9 câu hỏi (`id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`) | Hoàn thành |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks()` | DataFrame (baseline/corrupted/repaired) + `settings.freshness_threshold_days` | `data/quality/{baseline,corrupted,repaired}_quality.json` — 6 check (row count, `paper_id` not-null/unique, `title` not-null, `summary` min length, freshness) | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report()` | DataFrame + threshold | `data/quality/*freshness_report.json` — `latest_published`, `oldest_published`, `stale_rows`, `is_fresh` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đồng sở hữu `src/observability/reporting.py` cùng Người 4 | Người 4 (LLM/Agent/Metrics) | Đảm bảo bảng quality/freshness trong `phase1_report.md` và `corruption_report.md` đọc đúng structure JSON do `quality.py` xuất ra |
| Đối chiếu `ground_truth_doc_ids` trong test set với `corruption_log.json` | Người 1 (Corruption) | Xác nhận kịch bản corruption thật sự "đụng trúng" ít nhất 1 doc trong test set — nếu không, metrics sẽ không đổi (đúng cảnh báo trong Guide) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 9 câu hỏi frozen từ 3 paper đại diện (spread theo index sau khi sort `published` giảm dần) | `evaluation/testset.py` | `data/eval/test_set.json` | `cat data/eval/test_set.json \| jq length` → 9 |
| Viết 6 data quality check | `observability/quality.py::run_data_quality_checks` | `data/quality/baseline_quality.json` (PASS), `corrupted_quality.json` (FAIL 3/6) | So khớp `overall_status` trong file JSON |
| Viết freshness report | `observability/quality.py::build_freshness_report` | `stale_rows = 0` (baseline/repaired) vs `stale_rows = 4` (corrupted) | So khớp `is_fresh` field |

Output cụ thể: `corrupted_quality.json` ghi nhận đúng **4 record có summary < 20 ký tự** — khớp chính xác với kịch bản `blank_summary` của Người 1 (`round(22 × 0.20) = 4` record bị xoá summary), và **2 record duplicate `paper_id`** — khớp với kịch bản `duplicate_rows` (`round(22 × 0.10) = 2`). Đây là bằng chứng cho thấy quality checks của tôi detect đúng, đủ, không sót và không báo động giả (false positive) trên phần dữ liệu không bị corrupt.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết 2 vấn đề trong pipeline: (1) tạo ra một "thước đo cố định" (frozen test set) để có thể so sánh công bằng chất lượng agent giữa 3 trạng thái dữ liệu baseline/corrupted/repaired, và (2) phát hiện sớm dữ liệu có vấn đề (completeness, uniqueness, freshness) **trước khi** nó lan tới agent và làm người dùng nhận câu trả lời sai — đúng tinh thần "observability" của bài lab.

### Cách triển khai

**`testset.py`**: Tôi không sinh câu hỏi tự do bằng LLM (tốn chi phí, không tái lập được), mà dùng template cố định cho 4 loại câu hỏi (`summary`, `authors`, `date`, `categories`), áp lên 3 paper được chọn trải đều theo index (dùng `step = len(df) / sample_size` để lấy mẫu đại diện thay vì luôn lấy 3 paper đầu, tránh thiên lệch chỉ vào paper mới nhất). Mỗi câu hỏi luôn wrap tên paper trong dấu `'...'` để `retrieval/qa.py` có thể exact-match qua `index.lookup()` — tách biệt rõ được lỗi retrieval và lỗi generation.

**`quality.py`**: 6 check được thiết kế bám theo đúng data contract của nhóm (`paper_id` unique/non-null, `title` non-null, `summary` đủ dài, freshness theo `age_days`). Mỗi check trả về `{name, passed, detail}` độc lập, `overall_status` là AND của toàn bộ — giúp report ở Bước 11 hiển thị chi tiết check nào fail, không chỉ PASS/FAIL tổng.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | DataFrame cleaned (cột: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`) từ `cleaning.py` (Người 1) |
| Output                         | `test_set.json` (list[dict] theo schema chuẩn); `*_quality.json` và `*freshness_report.json` |
| Module phụ thuộc             | `core/utils.py` (`write_json`, `first_sentence`), `core/config.py` (`Settings.freshness_threshold_days`) |
| Module sử dụng output        | `evaluation/metrics.py` (đọc `test_set.json` để evaluate), `retrieval/qa.py` (pattern-match câu hỏi để trích answer), `observability/reporting.py` và `pipelines/phase1.py`/`corruption_flow.py` (đọc quality/freshness JSON) |
| Điều kiện lỗi cần xử lý | `df` rỗng hoặc < 3 paper → `raise ValueError` thay vì sinh test set rỗng (fail sớm, rõ ràng); ground truth rỗng (vd paper không có `categories_joined`) → skip câu hỏi đó thay vì đưa câu hỏi không có đáp án vào test set |

### Cách xác minh

```bash
uv run python script/run_phase1.py
cat data/eval/test_set.json | python -m json.tool | head -30
cat data/quality/baseline_quality.json
```

- **Kết quả mong đợi:** `test_set.json` có 9 phần tử, mỗi phần tử đủ 5 trường theo schema; `baseline_quality.json.overall_status = "PASS"`.
- **Kết quả thực tế:** Đúng như mong đợi — 9 câu hỏi, baseline PASS toàn bộ 6 check.
- **Artifact/log:** `data/eval/test_set.json`, `data/quality/baseline_quality.json`, `data/quality/corrupted_quality.json` (FAIL 3/6 check sau corruption), `data/quality/repaired_quality.json` (PASS lại toàn bộ sau repair).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Câu hỏi trong test set cần được `retrieval/qa.py` (do Người 4 phụ trách) trả lời đúng loại thông tin (tác giả, ngày, category...), nhưng `qa.py` không dùng LLM để phân loại intent câu hỏi — nó dùng pattern-matching chuỗi con (case-insensitive) để quyết định trích trường nào.
- **Các phương án đã cân nhắc:** (1) Viết câu hỏi tự nhiên, đa dạng cách diễn đạt (gần giống người dùng thật hỏi); (2) Viết câu hỏi theo template cố định, cứng nhắc nhưng đảm bảo khớp đúng pattern mà `qa.py` nhận diện.
- **Phương án đã chọn:** Phương án (2) — template cố định, bám sát các cụm từ khoá mà `_extract_answer()` trong `qa.py` kiểm tra (`"who authored"`, `"when was"`, `"what categories"`).
- **Lý do:** Bộ test set này phải **tái lập được (reproducible)** và **đo đúng cái cần đo** (chất lượng dữ liệu, không phải khả năng NLU của agent). Nếu câu hỏi diễn đạt tự nhiên nhưng không khớp pattern, `qa.py` sẽ mặc định trả về summary cho mọi loại câu hỏi → metric đo sai thứ (đo lỗi phrasing của testset, không đo ảnh hưởng của corruption).
- **Bằng chứng quyết định phù hợp:** `baseline_metrics.json` đạt `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0` — nếu pattern không khớp, `mean_token_f1` sẽ không thể đạt 1.0 cho câu hỏi `authors`/`date`/`categories` vì answer trả về sẽ luôn là đoạn summary generic, không khớp ground truth cụ thể.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Ở bản nháp đầu, câu hỏi loại `authors`/`date`/`categories` đều nhận được answer giống hệt câu hỏi loại `summary` — tức agent trả lời sai loại thông tin được hỏi, mặc dù retrieval tìm đúng document.
- **Lệnh hoặc bước tái hiện:** Chạy `evaluate_pipeline()` trên `test_set.json` bản nháp, so sánh `data/results/baseline_answers.json` với `ground_truth` — thấy answer của cả 4 loại câu hỏi trên cùng 1 paper giống hệt nhau.
- **Nguyên nhân gốc:** `retrieval/qa.py::_extract_answer()` dùng `if "who authored" in question.lower(): ...` để rẽ nhánh; câu hỏi bản nháp của tôi viết dạng khác (vd "Tell me the authors of...") không chứa đúng cụm từ này nên rơi vào nhánh `else` (trả về summary mặc định).
- **Cách xử lý:** Đọc kỹ source `qa.py` trước khi hoàn thiện `testset.py` (thay vì viết độc lập rồi mới tích hợp), rồi viết lại template câu hỏi bám sát đúng 4 cụm từ khoá mà `_extract_answer()` kiểm tra.
- **Cách xác minh sau khi sửa:** Chạy lại `evaluate_pipeline()` — `mean_token_f1` từ ~0.4 (do 3/4 loại câu hỏi trả lời sai loại thông tin) tăng lên `1.0`.
- **Điều học được:** Khi 2 module do 2 người viết riêng (testset sinh câu hỏi, qa.py trả lời câu hỏi) phụ thuộc lẫn nhau qua "ngôn ngữ tự nhiên" thay vì schema có cấu trúc, bắt buộc phải đọc chéo code của nhau trước khi tích hợp — không thể chỉ dựa vào docstring/Guide mô tả chung chung.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** `crossref.py` gọi API lấy `PaperRecord` thô (giữ nguyên thẻ XML trong abstract) → `cleaning.py` strip thẻ, chuẩn hoá, tính `age_days`, tạo `text_for_embedding` → `embeddings.py` encode bằng MiniLM-L6-v2 (384 chiều, normalized) → `index.py` nạp vào ChromaDB collection riêng cho từng trạng thái dữ liệu.
2. **Evaluation set & ground truth:** `test_set.json` do tôi sinh chứa `ground_truth_doc_ids` — chính là `paper_id` của paper được hỏi. Khi evaluate, `metrics.py` so `ground_truth_doc_ids` với danh sách `paper_id` mà `index.search()` trả về top-k để tính `retrieval_hit_rate`, và so answer text của agent với `ground_truth` để tính `mean_token_f1`/gọi LLM judge.
3. **Quality checks khác freshness monitoring ở chỗ:** quality checks đo **tính toàn vẹn cấu trúc** của dữ liệu tại một thời điểm (đủ trường, không trùng, không rỗng) — pass/fail tức thời. Freshness monitoring đo **tính kịp thời theo thời gian** (`age_days` so với ngưỡng) — có thể PASS quality nhưng vẫn stale nếu dữ liệu cũ nhưng đầy đủ/hợp lệ.
4. **Phải dùng cùng test set cho cả 3 trạng thái** vì mục tiêu là cô lập **một biến duy nhất** (chất lượng dữ liệu) — nếu đổi câu hỏi giữa các lần đánh giá, sự khác biệt về điểm số có thể đến từ việc câu hỏi khác nhau (độ khó khác nhau) chứ không phải từ corruption/repair, làm mất tính so sánh được.
5. **Repair thành công khi:** (a) `repaired_quality.json.overall_status = "PASS"` — toàn bộ 6 check quay lại đúng như baseline; (b) `repaired_metrics.json` các chỉ số RAG quay lại **bằng chính xác** baseline (không chỉ "gần bằng"), vì repair build lại từ raw snapshot chứ không sửa tay trên bản corrupted.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |     0.667 |      1.0 | Giảm đúng 3/9 câu — khớp với việc 1 trong 3 paper của test set bị `drop_latest_records` xoá hoàn toàn khỏi corpus |
| `mean_token_f1`      |      1.0 |     0.667 |      1.0 | Giảm cùng tỷ lệ với hit rate — khi retrieval fail thì answer luôn sai hoàn toàn (0 điểm), không có trường hợp "tìm sai doc nhưng vẫn đoán đúng nội dung" |
| `judge_accuracy`     |      1.0 |     0.667 |      1.0 | LLM judge đồng thuận với token-F1, không có sai lệch giữa 2 phương pháp chấm |
| `mean_judge_score`   |      5.0 |     3.778 |      5.0 | Giảm ít hơn tỷ lệ tuyệt đối (lẽ ra ~3.33 nếu 3 câu sai chấm 0 điểm) — cho thấy judge cho điểm phần (partial credit) chứ không nhị phân như `token_f1`/`hit_rate` |
| Quality checks         | 6/6 PASS |  3/6 FAIL (`paper_id_unique`, `summary_min_length`, `freshness_within_threshold`) | 6/6 PASS | Đúng 3 check quality của tôi bắt được đúng 3/6 kịch bản corruption có "dấu vết" cấu trúc (2 kịch bản còn lại — truncate title, add noise — không có check riêng vì chỉ ảnh hưởng chất lượng semantic, không phá cấu trúc dữ liệu) |
| Freshness status       | Fresh (0 stale) | Stale (4/24 stale) | Fresh (0 stale) | 4 thay vì 3 (số record bị `stale_date` trực tiếp) — do 1 record stale bị trùng với kịch bản `duplicate_rows`, xem mục 6 và báo cáo nhóm |

### Kết luận từ số liệu

1. **Data corruption (`drop_latest_records`) → mất document khỏi index (không có quality signal trực tiếp vì record không còn tồn tại để check) → `retrieval_hit_rate`/`mean_token_f1`/`judge_accuracy` đồng loạt giảm 0.333.**
2. **Repair (rebuild từ raw snapshot) → `overall_status` quality chuyển FAIL → PASS, `stale_rows` về 0 → toàn bộ 4 agent metric phục hồi 100%, bằng chính xác baseline.**

Corruption ảnh hưởng rõ nhất là `drop_latest_records`, vì đây là kịch bản duy nhất loại bỏ hẳn một document — các kịch bản còn lại (blank summary, truncate, stale date, duplicate, noise) chỉ làm giảm *chất lượng* của document chứ document vẫn còn trong index để retrieval tìm thấy.

Kết quả khác kỳ vọng ban đầu của tôi: tôi dự đoán `freshness_within_threshold` sẽ fail đúng 3 record (bằng số record bị kịch bản `stale_date` tác động), nhưng thực tế là 4. Tôi đã kiểm tra bằng cách đối chiếu `paper_id` trong 2 scenario `stale_publication_date` và `duplicate_rows` trong `corruption_log.json`, xác nhận có 1 `paper_id` trùng nhau — tức 1 record vừa bị làm cũ vừa bị nhân đôi, nên bị đếm 2 lần trong tổng số record stale.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Contract giữa các module (tên cột DataFrame, format ground truth) quan trọng hơn cả logic bên trong từng module — một thay đổi nhỏ về tên cột hoặc cách phrase câu hỏi có thể làm sập cả pipeline ở module khác mà không báo lỗi rõ ràng (như trường hợp mục 6).
2. **Về data quality/observability:** Quality check chỉ có giá trị nếu nó **đo được đúng dimension** mà corruption thật sự vi phạm — 2/6 kịch bản corruption của nhóm (truncate title, add noise) "lọt" qua toàn bộ 6 check của tôi vì chúng không phá completeness/uniqueness/freshness mà chỉ phá *semantic quality*, một dimension tôi chưa có check riêng.
3. **Về ảnh hưởng của data đến RAG agent:** Không phải mọi lỗi dữ liệu đều ảnh hưởng metric như nhau — lỗi làm **mất document** (drop) nghiêm trọng hơn hẳn lỗi làm **giảm chất lượng document** (noise/truncate), vì retrieval là bước có/không (binary) trong khi generation có thể "chịu đựng" một phần nhiễu.

### Nếu có thêm thời gian

Tôi sẽ thêm 1 quality check đo "semantic drift" — so sánh embedding của `text_for_embedding` trước/sau corruption bằng cosine similarity, để bắt được đúng 2 kịch bản (`truncate_title`, `add_noise`) hiện đang lọt qua các check cấu trúc. Đo cải thiện bằng cách chạy lại `corrupted_quality.json` và kỳ vọng `overall_status` phản ánh đầy đủ cả 6 kịch bản corruption, không chỉ 3/6 như hiện tại.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lý Thành Đạt
**Ngày xác nhận:** 🔲 [YYYY-MM-DD]