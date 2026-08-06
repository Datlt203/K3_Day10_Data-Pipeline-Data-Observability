# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Văn Huy             |
| MSSV               | 2A202601235                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | fiveboiz     |
| Vai trò chính    | LLM, Agent & Metrics                 |
| Repository         | https://github.com/Datlt203/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| LLM Retrieval Agent | `src/retrieval/llm.py`, `src/retrieval/agent.py` | Câu hỏi, Context (từ index) | Câu trả lời (answer) | Hoàn thành |
| Question Answering | `src/retrieval/qa.py` | Câu hỏi, Context | Câu trả lời | Hoàn thành |
| Evaluation Metrics | `src/evaluation/metrics.py` | Ground-truth, Generated-answer | Retrieval/Generation metrics | Hoàn thành |
| Reporting (co-owner) | `src/observability/reporting.py` | Metrics, Quality reports | Báo cáo markdown | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp, chạy thử nghiệm pipeline | Ngô Hữu Nghĩa (Orchestrator) | Pipeline baseline & corruption chạy ổn định |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Phát triển RAG agent | `src/retrieval/agent.py` | `data/results/*_answers.json` | Chạy `run_phase1.py` |
| Tính toán Metrics | `src/evaluation/metrics.py` | `data/results/*_metrics.json` | Chạy `run_phase1.py` |

Phần việc của tôi đóng vai trò then chốt trong việc đánh giá hiệu quả của hệ thống RAG thông qua việc đo lường các metric như `retrieval_hit_rate` và `mean_token_f1`, giúp khẳng định chất lượng của dữ liệu và hệ thống retrieval.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng logic để LLM-Agent trả lời dựa trên context được retrieve, và thiết lập công thức đánh giá độ chính xác của câu trả lời so với ground-truth.

### Cách triển khai
Sử dụng LLM (Gemini) để trả lời câu hỏi dựa trên context. Triển khai các hàm tính toán metric như `hit_rate` (dựa trên paper_id) và `token_f1` (dựa trên nội dung câu trả lời).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `test_set.json`, Retrieved context |
| Output                         | `metrics.json`, `answers.json` |
| Module phụ thuộc             | `src/retrieval/index.py` (chứa vector index) |
| Module sử dụng output        | `src/observability/reporting.py` |
| Điều kiện lỗi cần xử lý | Empty context hoặc LLM không trả lời đúng format |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Các file metric được sinh ra với giá trị 1.0 cho baseline.
- **Kết quả thực tế:** Đạt 1.0 cho tất cả metric baseline.
- **Artifact/log:** `data/results/baseline_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách đánh giá độ chính xác của câu trả lời.
- **Các phương án đã cân nhắc:** Exact match (quá khắt khe) vs Semantic evaluation qua LLM-judge (linh hoạt hơn).
- **Phương án đã chọn:** Kết hợp giữa exact-match cho ID và LLM-judge để chấm điểm nội dung câu trả lời.
- **Lý do:** Đảm bảo cả tính chính xác về dữ liệu (ID) và tính diễn đạt (nội dung), cân bằng giữa độ tin cậy và linh hoạt.
- **Bằng chứng quyết định phù hợp:** `mean_judge_score` đạt 5.0 ở baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Retrieval trả về context không liên quan đến câu hỏi.
- **Lệnh hoặc bước tái hiện:** Chạy test set ban đầu.
- **Nguyên nhân gốc:** Prompt cho agent chưa đủ ngữ cảnh để lọc kết quả retrieve.
- **Cách xử lý:** Cải thiện system prompt của agent, hướng dẫn nó ưu tiên context và trả lời "không biết" nếu không tìm thấy thông tin.
- **Cách xác minh sau khi sửa:** Chạy lại `run_phase1.py` và kiểm tra `baseline_answers.json`.
- **Điều học được:** Tầm quan trọng của prompt engineering trong RAG.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ Crossref qua cleaning, embedding vào ChromaDB. Agent sử dụng ChromaDB để tìm context, sau đó LLM trả lời dựa trên context đó.
2. `testset.json` chứa cặp (câu hỏi, ground-truth document ID). Metric so sánh (document tìm thấy vs ground-truth) và (câu trả lời vs ground-truth nội dung).
3. Quality check kiểm tra độ hợp lệ của dữ liệu (schema, uniqueness, completeness), freshness check kiểm tra xem dữ liệu có bị cũ không (`age_days` > threshold).
4. Để đảm bảo tính so sánh (apples-to-apples).
5. Metrics (`hit_rate`, `f1`, `judge_score`) quay lại baseline và Quality/freshness checks đều PASS.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired |
| ---------------------- | -------: | --------: | -------: |
| `retrieval_hit_rate` |      1.0 |       0.667 |      1.0 |
| `mean_token_f1`      |      1.0 |       0.667 |      1.0 |
| `judge_accuracy`     |      1.0 |       0.667 |      1.0 |
| `mean_judge_score`   |      5.0 |       3.778 |      5.0 |

### Kết luận từ số liệu
Corruption (drop/blank) làm suy giảm context → agent trả lời sai/không tìm thấy → metrics giảm.
Repair (rebuild từ raw) khôi phục dữ liệu sạch → index và context đầy đủ → metrics phục hồi 100%.
Kịch bản `drop_latest_records` ảnh hưởng nghiêm trọng nhất do xóa hoàn toàn document.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. Tầm quan trọng của dữ liệu sạch.
2. Mối liên hệ chặt chẽ giữa data quality và RAG metrics.
3. Cách xây dựng pipeline đánh giá end-to-end có khả năng tái lập.

### Nếu có thêm thời gian
Bật `RUN_RAGAS` để đánh giá sâu hơn về faithfulness.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Văn Huy
**Ngày xác nhận:** 2026-08-06
