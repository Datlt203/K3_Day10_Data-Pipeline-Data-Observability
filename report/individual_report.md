# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Hữu Nhật Minh             |
| MSSV               | 2A202601551                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | fiveboiz     |
| Vai trò chính    | Vector Store & Indexing (Người 2) |
| Repository         | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Embedding Generation | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`) | Danh sách văn bản `text_for_embedding` | Vector nhúng 384 chiều | Hoàn thành |
| Vector Store Indexing | `src/retrieval/index.py` (`LocalEmbeddingIndex`) | Cleaned DataFrame `papers_clean.json` | Cơ sở dữ liệu ChromaDB (`data/chroma/`) và JSON Manifest (`data/embeddings/`) | Hoàn thành |
| Multi-stage Re-indexing | `LocalEmbeddingIndex.build()` | `papers_corrupted.json`, `papers_repaired.json` | Các Collections ChromaDB & Manifests tương ứng | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp Retriever vào Orchestration Pipeline | Ngô Hữu Nghĩa (Người 5 / `phase1.py`, `corruption_flow.py`) | Đồng bộ chuẩn giao diện OOP `LocalEmbeddingIndex.build()` giúp pipeline chạy tự động end-to-end |
| Cung cấp giao diện Search & Lookup | Lê Văn Huy (Người 4 / `agent.py`, `qa.py`) | Cung cấp các hàm `index.search()` và `index.lookup()` hỗ trợ Top-K Semantic Search và Exact Title Lookup |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai mô hình Embedding | `src/retrieval/embeddings.py` | Lớp `MiniLMEmbeddings` bọc `sentence-transformers/all-MiniLM-L6-v2` | Khởi tạo mô hình và kiểm tra kích thước vector trả về (384 float) |
| Xây dựng chỉ mục ChromaDB | `src/retrieval/index.py` | Lớp `LocalEmbeddingIndex` khởi tạo Persistent Client | Tạo thành công các collection `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Xuất Manifest & Vector Store Artifacts | `data/embeddings/`, `data/chroma/` | File `papers_embeddings.json` & thư mục `chroma.sqlite3` | Kiểm tra sự tồn tại và cấu trúc file trong thư mục `data/` |

**Artifact cụ thể đã tạo ra:**
- File Manifest metadata: [data/embeddings/papers_embeddings.json](file:///d:/CODELAB/LAB10/K3_Day10_Data-Pipeline-Data-Observability/data/embeddings/papers_embeddings.json) ghi nhận đầy đủ 24 tài liệu được nhúng kèm cấu hình `all-MiniLM-L6-v2`.
- Cơ sở dữ liệu Vector Database: [data/chroma/chroma.sqlite3](file:///d:/CODELAB/LAB10/K3_Day10_Data-Pipeline-Data-Observability/data/chroma/chroma.sqlite3) lưu chỉ mục vector không gian Cosine HNSW.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG cần chuyển đổi dữ liệu bài báo học thuật đã làm sạch (`papers_clean.json`) từ định dạng văn bản thuần túy sang không gian vector dày (dense vector embedding) và lưu trữ vào Vector Database có khả năng truy vấn theo độ tương đồng ngữ cảnh (Cosine distance), nhằm giúp RAG Agent dễ dàng lấy ra Top-K tài liệu liên quan nhất cho câu hỏi của người dùng.

### Cách triển khai
1. **Lớp `MiniLMEmbeddings`**: Kế thừa giao diện `Embeddings` từ `langchain_core`. Sử dụng hàm `@lru_cache` để nạp mô hình `sentence-transformers/all-MiniLM-L6-v2` một lần duy nhất vào bộ nhớ, tránh overhead khi gọi lại. Chuẩn hóa vector đầu ra bằng `normalize_embeddings=True`.
2. **Lớp `LocalEmbeddingIndex`**:
   - `_build_documents()`: Đóng gói mỗi bản ghi thành đối tượng document gồm `record_id`, `paper_id`, `title`, `content` (`text_for_embedding`) và `metadata`.
   - `build()`: Khởi tạo `chromadb.PersistentClient`, tạo collection với cấu hình khoảng cách Cosine `{"hnsw": {"space": "cosine"}}`, tính toán vector nhúng và nạp toàn bộ vào ChromaDB collection. Đồng thời xuất file Manifest JSON ghi nhận toàn bộ thông số index.
   - `search()`: Nhận `query`, tính `query_embedding` và gọi `collection.query()` lấy Top-K tài liệu có khoảng cách Cosine ngắn nhất, đổi khoảng cách thành điểm tương đồng `score = max(0.0, 1.0 - distance)`.
   - `lookup()`: Cho phép tra cứu chính xác tài liệu theo `paper_id` hoặc `title` thông qua Hash Map tra cứu nhanh `documents_by_paper_id` và `documents_by_title`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned DataFrame (`papers_clean.json`), đối tượng `Settings` chứa cấu hình đường dẫn và tên model |
| Output                         | Instance `LocalEmbeddingIndex`, file manifest JSON tại `data/embeddings/`, database tại `data/chroma/` |
| Module phụ thuộc             | `core.config`, `core.utils`, `sentence_transformers`, `chromadb` |
| Module sử dụng output        | `retrieval.agent`, `retrieval.qa`, `evaluation.metrics`, `pipelines.phase1`, `pipelines.corruption_flow` |
| Điều kiện lỗi cần xử lý | Xóa collection cũ nếu trùng tên trước khi tạo mới; bỏ qua record bị thiếu ID/metadata khi search |

### Cách xác minh

```bash
.venv\Scripts\python.exe -c "import pandas as pd; from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; settings = load_settings(); df = pd.read_json(settings.paths.clean_json); index = LocalEmbeddingIndex.build(df, settings); print('Collection created:', index.collection_name); results = index.search('agentic RAG', top_k=2); print('Top result:', results[0].title)"
```

- **Kết quả mong đợi:** Khởi tạo thành công collection `papers-baseline`, tính toán vector 384 chiều, lưu Manifest và trả về Top-2 bài báo liên quan tới từ khóa `'agentic RAG'`.
- **Kết quả thực tế:** Hệ thống tạo thành công `papers-baseline`, lưu dữ liệu vào `data/chroma/chroma.sqlite3` và tìm thấy bài báo liên quan với điểm số `score > 0.7`.
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/chroma/chroma.sqlite3`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Trong bài lab, dữ liệu được đánh giá ở 3 trạng thái: Baseline (sạch), Corrupted (lỗi) và Repaired (phục hồi). Cần đảm bảo dữ liệu vector của 3 trạng thái không bị nhiễu hoặc ghi đè lẫn nhau trong Vector Store.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Dùng 1 collection duy nhất trong ChromaDB và xóa/ghi đè lại dữ liệu mỗi lần chạy flow mới.
  - *Phương án B:* Khởi tạo 3 Collection riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong ChromaDB và lưu 3 file Manifest độc lập.
- **Phương án đã chọn:** Phương án B (Tạo 3 Collection độc lập).
- **Lý do:** Phương án B đảm bảo tính cô lập tuyệt đối dữ liệu (Data Isolation), tránh nguy cơ Data Contamination (nhiễm bẩn dữ liệu giữa bản lỗi và bản sạch). Đồng thời giúp việc đối chiếu metrics RAG giữa 3 trạng thái được chính xác và có thể tái lập (reproducibility) bất kỳ lúc nào mà không cần train/index lại.
- **Bằng chứng quyết định phù hợp:** Cả 3 file Manifest (`papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json`) cùng 3 collection tồn tại song song trong `data/chroma/`, cho phép kiểm thử đối chiếu độc lập.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0: character maps to <undefined>
  ```
  Và lỗi không tìm thấy tên hàm khi pipeline cũ cố gắng import procedural functions:
  ```text
  ImportError: cannot import name 'compute_embeddings' from 'retrieval.embeddings'
  ```
- **Lệnh hoặc bước tái hiện:** Running script `test_role2.py` hoặc `run_phase1.py` trên môi trường Windows PowerShell mặc định.
- **Nguyên nhân gốc:** Windows Terminal mặc định sử dụng bảng mã CP1252/Console CodePage không hỗ trợ ký tự UTF-8 Emoji (`✅`). Đồng thời pipeline ban đầu giả định gọi các hàm tự do (`compute_embeddings`, `build_index`) trong khi thiết kế mã nguồn của Role 2 được đóng gói theo hướng đối tượng (OOP Class `LocalEmbeddingIndex`).
- **Cách xử lý:** Thay thế các ký tự emoji trong lệnh print/log bằng text tiếng Anh chuẩn UTF-8/ASCII, đồng thời cập nhật `src/pipelines/phase1.py` để sử dụng trực tiếp class method `LocalEmbeddingIndex.build(df, settings)`.
- **Cách xác minh sau khi sửa:** Lệnh chạy `run_phase1.py` diễn ra 100% thành công không có ngoại lệ hay cảnh báo ImportError, tạo ra đầy đủ ChromaDB database và Manifest.
- **Điều học được:** Luôn chú ý tính tương thích mã hóa ký tự (encoding) trên các hệ điều hành khác nhau (Windows vs Linux) và tuân thủ đúng giao diện thiết kế OOP của module.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu raw JSON lấy từ Crossref REST API được trích xuất và chuẩn hóa bởi module Ingestion/Cleaning thành `papers_clean.json`. Trường `text_for_embedding` (kết hợp Title, Authors, Categories, Summary) được đưa qua lớp `MiniLMEmbeddings` để tính toán vector 384 chiều, sau đó nạp kèm metadata vào chỉ mục HNSW Cosine của ChromaDB Vector Store.
2. **Evaluation set và ground-truth document IDs:** Evaluation set (`test_set.json`) được đóng băng (frozen) chứa danh sách câu hỏi kèm `ground_truth_doc_ids` (ID bài báo gốc). Khi RAG Agent tìm kiếm, danh sách `retrieved_doc_ids` từ Vector Store sẽ được so sánh với `ground_truth_doc_ids`. Nếu ID bài báo gốc nằm trong Top-K kết quả trả về, `retrieval_hit_rate` được tính là 1 (Hit), ngược lại là 0 (Miss).
3. **Quality checks vs Freshness monitoring:** Data Quality checks tập trung vào tính toàn vẹn và hợp lệ của cấu trúc dữ liệu hiện tại (kiểm tra rỗng, trùng lặp `paper_id`, độ dài `summary`). Trong khi Freshness monitoring tập trung vào tính thời sự của dữ liệu theo thời gian (dựa vào `age_days` so với ngưỡng threshold 180 ngày) để phát hiện dữ liệu lỗi thời.
4. **Vì sao phải dùng cùng test set cho 3 trạng thái:** Phải dùng cùng một bộ test set đóng băng để đảm bảo tính so sánh công bằng (apples-to-apples). Mọi sự thay đổi về điểm số metrics RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_score`) giữa Baseline, Corrupted và Repaired đều phản ánh chính xác tác động của chất lượng dữ liệu, chứ không bị nhiễu do khác biệt câu hỏi.
5. **Repair được xem là thành công dựa trên artifact và metric nào:** Repair thành công khi `repaired_quality.json` trả về `passed: True` ở toàn bộ 6 tiêu chí kiểm tra, `freshness` đạt 0 record stale, và các chỉ số RAG trong `repaired_metrics.json` (`retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0/0.57`, `judge_accuracy = 1.0`) phục hồi 100% về bằng với mức Baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.0 |     0.667 |     1.0 | Giảm 33.3% khi corrupted do bị xoá mất 1 paper có trong testset; phục hồi 100% sau repair |
| `mean_token_f1`      |    0.5736 |    0.3824 |    0.5736 | Giảm tương ứng với tỷ lệ sụt giảm retrieval; phục hồi hoàn toàn sau repair |
| `judge_accuracy`     |    0.5208 |    0.3472 |    0.5208 | Điểm đánh giá của Judge giảm mạnh khi thiếu ngữ cảnh; phục hồi nguyên vẹn |
| `mean_judge_score`   |     3.04 |      2.12 |      3.04 | Giảm từ 3.04 xuống 2.12 do các câu hỏi mất doc bị chấm điểm tối thiểu |
| Quality checks         | 6/6 PASS | 3/6 FAIL | 6/6 PASS | Bị FAIL các tiêu chí uniqueness, summary length và freshness; phục hồi PASS 100% |
| Freshness status       | Fresh | Stale (4 rows) | Fresh (0 stale) | Giảm độ tươi dữ liệu do kịch bản ép ngày xuất bản cũ; phục hồi Fresh sau khi clean lại |

### Kết luận từ số liệu

1. **[Data corruption] → [Quality checks FAIL 3/6 & Freshness Stale] → [Retrieval Hit Rate giảm từ 1.0 xuống 0.667]:** Khi dữ liệu bị làm rỗng summary, nhiễu text và xóa mất bản ghi mới nhất, Vector Store không thể truy xuất đúng document gốc, dẫn đến chất lượng trả lời của RAG Agent bị suy giảm nghiêm trọng.
2. **[Repair action] → [Re-cleaning từ raw snapshot & Re-indexing ChromaDB] → [Metrics RAG phục hồi 100% về mức Baseline]:** Việc rebuild lại toàn bộ dữ liệu từ nguồn tin cậy (`crossref_records.json`) giúp loại bỏ hoàn toàn các vector nhiễu, đưa các chỉ số đo lường Data Quality và RAG Evaluation về trạng thái tối ưu ban đầu.

**Corruption ảnh hưởng rõ nhất:** Kịch bản **Drop latest records** có tác động nghiêm trọng nhất vì nó xóa hẳn tài liệu ra khỏi ChromaDB Index, khiến vector search không thể tìm thấy dữ liệu nguồn dưới bất kỳ hình thức nào.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Hiểu rõ tầm quan trọng của việc lưu trữ Raw Artifacts làm điểm tựa tin cậy (Single Source of Truth) để có thể khôi phục (repair) dữ liệu bất kỳ lúc nào mà không phụ thuộc vào dữ liệu bị nhiễm bẩn.
2. **Về Data Quality & Observability:** Thấy được vai trò thiết yếu của các bộ quan sát Data Quality và Freshness checks trong việc tự động phát hiện sự cố dữ liệu trước khi dữ liệu xấu đi vào hệ thống RAG.
3. **Về ảnh hưởng của Data đến RAG Agent:** Chứng minh được định lý "Garbage in, Garbage out" bằng con số cụ thể: Chất lượng của RAG Agent phụ thuộc trực tiếp vào tính đúng đắn và toàn vẹn của Vector Store Indexing.

### Nếu có thêm thời gian

Tôi sẽ nghiên cứu triển khai mô hình **Hybrid Search** (kết hợp BM25 Sparse Search và Dense Vector Search HNSW) cùng kỹ thuật **Re-ranking** (như Cross-Encoder) trong `src/retrieval/index.py` để nâng chỉ số `mean_token_f1` và độ chính xác tìm kiếm ngữ cảnh lên mức tối đa.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hữu Nhật Minh  
**Ngày xác nhận:** 2026-08-06  
