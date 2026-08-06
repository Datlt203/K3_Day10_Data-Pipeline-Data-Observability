# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Bùi Văn Khởi |
| MSSV | 2A202601723 |
| Khóa/Lớp | K3 |
| Tên nhóm | fiveboiz |
| Vai trò chính | Data ingestion & cleaning owner (Role 1) |
| Repository | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload`, `_get_with_retry`, `fetch_source_records`, `load_raw_records` | Crossref REST API response và cấu hình trong `Settings` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Cleaning và data modeling | `src/ingestion/cleaning.py`: `build_clean_dataframe` và các hàm hỗ trợ | Danh sách `PaperRecord` và thời điểm chạy | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Tạo dữ liệu corruption và corruption log để kiểm thử | `src/ingestion/corruption.py`: `corrupt_clean_dataframe` | Cleaned DataFrame và đường dẫn output log | `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_corrupted.json`, `data/results/corruption_log.json` | Hoàn thành phần tạo dữ liệu và log; chưa có metrics tích hợp |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa `text_for_embedding` sau khi dữ liệu bị corruption | Embedding/index và corruption flow | Nội dung embedding phản ánh title/summary sau corruption và có thể được thêm noise có kiểm soát |
| Cung cấp các kịch bản corruption và log có seed cố định | Observability và pipeline integration | `corruption_log.json` ghi loại lỗi, số lượng, `paper_ids` bị tác động và seed `42` để tái hiện |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Gọi Crossref API với retry/backoff | `src/ingestion/crossref.py` | Xử lý lỗi request và HTTP `429`, `503`; tối đa 5 lần thử | Kiểm tra `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |
| Parse payload thành data model thống nhất | `PaperRecord`, `parse_crossref_payload` | Lọc record thiếu DOI, title, abstract hoặc ngày xuất bản | Đọc `data/raw/crossref_records.json`; hiện có 24 record |
| Chuẩn hóa dữ liệu trước embedding | `build_clean_dataframe` | Clean schema gồm 14 cột; strip markup, chuẩn hóa text, tính `age_days`, loại trùng `paper_id` | Đọc `data/clean/papers_clean.csv`; hiện có 24 record |
| Tạo corruption có thể tái hiện và ghi log | `corrupt_clean_dataframe`, `data/results/corruption_log.json` | Drop 2 record mới, blank 4 summary, truncate 3 title, làm cũ ngày của 3 record, thêm noise vào 4 record và duplicate 2 record | Đối chiếu `corruption_log.json` với hai artifact `papers_clean_corrupted.*` |

Output chính của phần việc là bộ dữ liệu raw và clean gồm 24 paper records. Clean dataset có các trường phục vụ downstream như `paper_id`, `title`, `summary`, `published`, `age_days` và `text_for_embedding`. Ngày xuất bản trong artifact hiện tại nằm trong khoảng 2026-02-12 đến 2026-08-01. Tôi cũng phụ trách `data/results/corruption_log.json`, artifact truy vết chính xác từng corruption scenario và các document ID bị tác động.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc giải quyết việc lấy dữ liệu paper từ Crossref và chuyển response có cấu trúc không đồng nhất thành schema ổn định cho embedding, evaluation và observability. Dữ liệu nguồn có thể thiếu DOI, abstract, ngày hoặc chứa XML/HTML trong abstract, vì vậy cần validate và clean trước khi đưa vào pipeline.

### Cách triển khai

Crossref được gọi qua endpoint `https://api.crossref.org/works` với query, filter ngày và số record lấy từ `Settings`. Request có timeout 30 giây, retry tối đa 5 lần và exponential backoff có jitter khi gặp lỗi mạng, HTTP `429` hoặc `503`.

Payload được parse thành `PaperRecord`. DOI được dùng làm `paper_id`; tác giả, subject, ngày xuất bản, ngày cập nhật, URL bài viết và PDF được trích xuất từ các trường tương ứng. Record thiếu DOI, title, abstract hoặc ngày xuất bản bị loại.

Ở bước cleaning, markup được loại khỏi title và summary, khoảng trắng được chuẩn hóa, summary phải dài ít nhất 100 ký tự, ngày phải đúng định dạng `YYYY-MM-DD`, và record trùng `paper_id` bị loại. `text_for_embedding` được tạo theo cấu trúc `Title | Authors | Summary`; `age_days` là số ngày từ ngày xuất bản đến ngày chạy và không nhỏ hơn 0.

Module corruption sử dụng seed cố định `42` để tạo các lỗi dữ liệu có thể tái hiện: loại record mới nhất, xóa summary, cắt title, đổi ngày xuất bản về năm 2000, thêm noise vào embedding text và nhân bản record. Trong cùng hàm, log được ghi bằng `write_json` với các trường `generated_at`, `seed`, `total_rows_before`, `scenarios` và `total_rows_after`. Mỗi scenario ghi `type`, `count` và danh sách `paper_ids`, nhờ đó module observability và integration có thể đối chiếu lỗi được tạo với thay đổi của quality signals và metrics.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref `works` JSON payload; `Settings`; thời điểm chạy cleaning |
| Output | Raw JSON; clean CSV/JSON; corrupted CSV/JSON; corruption log JSON |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py`, `requests`, `pandas` |
| Module sử dụng output | Embedding/index, evaluation set, quality/freshness và orchestration |
| Điều kiện lỗi cần xử lý | Lỗi mạng; HTTP `429`/`503`; JSON thiếu trường; ngày không hợp lệ; summary quá ngắn; trùng DOI; DataFrame rỗng khi corruption |

### Cách xác minh

```powershell
python script/run_phase1.py
```

- **Kết quả mong đợi:** tạo raw response, raw records, clean CSV/JSON và các artifact downstream của phase 1.
- **Kết quả thực tế:** đã có raw và clean artifact, mỗi bộ có 24 record. Chưa có đủ embedding, evaluation, metrics và report để xác nhận toàn bộ phase 1 chạy end-to-end.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_corrupted.json`, `data/results/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref có thể trả về các record thiếu trường hoặc abstract chứa markup, trong khi module embedding cần text ổn định và document ID không đổi.
- **Các phương án đã cân nhắc:** giữ mọi record rồi điền giá trị mặc định; hoặc loại các record không đạt contract tối thiểu và chỉ chuẩn hóa record hợp lệ.
- **Phương án đã chọn:** dùng DOI làm `paper_id`; loại record thiếu DOI, title, abstract, ngày xuất bản hoặc có summary sau cleaning ngắn hơn 100 ký tự; loại markup và duplicate trước embedding.
- **Lý do:** ưu tiên correctness, identity ổn định và chất lượng nội dung cho retrieval. Việc giữ record thiếu nội dung có thể làm giảm chất lượng embedding và gây khó cho evaluation.
- **Bằng chứng quyết định phù hợp:** artifact clean hiện có 24 record, không mất record so với 24 raw records của lần chạy này, đồng thời cung cấp đầy đủ 14 cột theo clean contract.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** request tới Crossref có thể thất bại tạm thời hoặc trả HTTP `429 Too Many Requests`/`503 Service Unavailable`.
- **Lệnh hoặc bước tái hiện:** chạy ingestion nhiều lần hoặc khi API giới hạn lưu lượng.
- **Nguyên nhân gốc:** nguồn Crossref là API bên ngoài, có rate limit và có thể tạm thời không sẵn sàng.
- **Cách xử lý:** thêm timeout 30 giây, tối đa 5 lần retry, exponential backoff, jitter và hỗ trợ header `Retry-After`.
- **Cách xác minh sau khi sửa:** chạy lại ingestion và kiểm tra hai raw artifact được tạo; lần chạy được lưu hiện có 24 records.
- **Điều học được:** pipeline dùng nguồn bên ngoài cần retry có giới hạn, backoff và snapshot raw response để tăng khả năng tái hiện và điều tra lỗi.

Blocker còn lại là môi trường ảo cục bộ đã bị xóa trong quá trình dọn repository, và repository hiện chưa có đầy đủ baseline/corrupted/repaired metrics để xác minh tác động của dữ liệu đến RAG agent. Bước tiếp theo là cài lại dependencies, tích hợp các module downstream và chạy lại hai flow.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu được lấy từ Crossref, lưu nguyên response để truy vết, parse thành `PaperRecord`, clean thành DataFrame, tạo `text_for_embedding`, sau đó embedding và đưa vào vector index.
2. Evaluation set chứa câu hỏi và ground-truth document ID. Retriever trả về top-k document IDs; các ID này được đối chiếu với ground truth để tính retrieval hit rate. Nội dung trả lời được đánh giá thêm bằng token F1 và judge metrics.
3. Quality checks đo các thuộc tính như completeness, validity và uniqueness của dữ liệu. Freshness monitoring tập trung vào độ mới của timestamp/dataset so với ngưỡng thời gian quy định.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để thay đổi metric phản ánh thay đổi dữ liệu, không phải do thay câu hỏi hoặc ground truth.
5. Repair thành công khi dữ liệu được phục hồi từ nguồn raw/baseline đáng tin cậy, quality/freshness signals trở lại mức mong đợi và các retrieval/answer metrics phục hồi so với baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa có | Chưa có | Chưa có | Chưa có artifact metrics để kết luận |
| `mean_token_f1` | Chưa có | Chưa có | Chưa có | Chưa có artifact metrics để kết luận |
| `judge_accuracy` | Chưa có | Chưa có | Chưa có | Chưa có artifact metrics để kết luận |
| `mean_judge_score` | Chưa có | Chưa có | Chưa có | Chưa có artifact metrics để kết luận |
| Quality checks | Chưa có | Chưa có | Chưa có | Chưa có quality report để kết luận |
| Freshness status | Chưa có | Chưa có | Chưa có | Chưa có freshness report để kết luận |

### Kết luận từ số liệu

1. Blank summary/duplicate/stale date **được kỳ vọng** làm giảm completeness/uniqueness/freshness và có thể làm giảm retrieval/answer metrics. Hiện chưa có quality report và metrics nên chưa thể khẳng định tác động thực tế.
2. Repair từ raw hoặc baseline clean data **được kỳ vọng** phục hồi quality/freshness và agent metrics. Chưa có repaired artifact và comparison report để đo mức phục hồi.

Trong các kịch bản đã triển khai, drop latest records và blank summary có khả năng ảnh hưởng retrieval rõ nhất vì chúng loại tài liệu hoặc làm mất nội dung dùng để tạo embedding. Đây mới là giả thuyết kỹ thuật; cần chạy cùng evaluation set trên ba trạng thái để kiểm chứng.

Kết quả khác kỳ vọng là corrupted CSV hiện vẫn có 24 dòng như baseline. `corruption_log.json` giải thích nguyên nhân: 2 record mới nhất bị loại và 2 record khác bị duplicate, nên tổng số dòng trước và sau đều là 24. Vì vậy chỉ nhìn row count không đủ để phát hiện corruption; cần kiểm tra đồng thời uniqueness, completeness và danh sách paper IDs bị tác động trong log.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot và schema ổn định giúp pipeline có thể tái hiện và debug khi nguồn API thay đổi.
2. Data quality cần nhiều tín hiệu; row count bình thường không có nghĩa dữ liệu không bị thiếu, trùng hoặc stale.
3. Corruption của title, summary và document identity có thể lan truyền sang embedding, retrieval và cuối cùng là chất lượng câu trả lời của RAG agent.

### Nếu có thêm thời gian

Tôi sẽ bổ sung unit tests cho parsing/cleaning, tạo corruption log cùng artifact, chạy baseline–corrupted–repaired trên cùng test set và đo mức thay đổi của retrieval hit rate, token F1, judge score, completeness, uniqueness và freshness.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu; nội dung chưa có bằng chứng được ghi rõ là giả thuyết hoặc chưa xác minh.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Bùi Văn Khởi  
**Ngày xác nhận:** 2026-08-06
