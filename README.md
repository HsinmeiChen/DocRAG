# DocRAG

以 **Django REST Framework、PostgreSQL、Qdrant 與 OpenAI API** 建置的 PDF 文件檢索問答後端專案，支援文件索引、語意搜尋、根據文件內容生成回答，以及來源引用。

專案提供 REST API，適合透過 Postman 或 cURL 操作。目前支援具有文字層的 PDF，掃描型 PDF 尚未加入 OCR。

## 線上展示

- [Railway API](https://docrag-production-4c8d.up.railway.app/)
- [Health Check](https://docrag-production-4c8d.up.railway.app/health/)

線上使用 Railway 執行 Django、Gunicorn 與 PostgreSQL，向量儲存使用 Qdrant Cloud。服務可能因閒置進入休眠，首次請求需等待啟動。

健康檢查成功時：

```json
{
  "status": "ok",
  "db": 1
}
```

健康檢查會查詢 PostgreSQL；它無法單獨證明 OpenAI 或 Qdrant 連線正常。

## 系統架構

| 元件 | 職責 |
| --- | --- |
| Django REST Framework | 文件上傳、索引、搜尋、問答 API 與請求驗證 |
| PostgreSQL | 保存文件中繼資料、文字 Chunk、索引狀態與 Qdrant Point ID |
| Qdrant | 保存 Embedding 向量，使用 Cosine similarity 檢索 |
| OpenAI API | 建立文字／問題向量，並根據檢索內容生成回答 |
| Docker Compose | 本機啟動 Django、PostgreSQL 與 Qdrant |
| Railway / Gunicorn | 雲端執行 Django API |
| GitHub Actions | 執行 Django 檢查、Migration 檢查與單元測試 |

### 文件處理流程

```text
上傳 PDF
  → pypdf 擷取每頁文字
  → 以固定字元長度切分 Chunk
  → PostgreSQL 儲存 Document 與 Chunk
  → 呼叫索引 API
  → OpenAI 產生每個 Chunk 的 Embedding
  → Qdrant 儲存向量與 document_id / page / chunk_index
  → PostgreSQL 更新 Point ID 與索引狀態
```

**注意：** 上傳與建立向量索引是兩個獨立的 API 操作。上傳成功後，仍需呼叫索引端點。

### 問答流程

```text
使用者提問
  → 產生問題 Embedding
  → Qdrant 搜尋相似向量（可指定 document_id）
  → 依 Point ID 從 PostgreSQL 取得 Chunk 文字
  → 組合 Context 與引用編號
  → OpenAI 生成答案
  → 擷取答案實際引用的編號
  → 回傳答案與對應的頁碼、Chunk 位置、相似度
```

### 資料模型

- **Document**：`title`、上傳檔案、上傳時間、`index_status`、索引完成時間。
- **Chunk**：所屬 `document`、`page`、`chunk_index`、`content`、`qdrant_point_id`、建立時間。
- 一份 Document 對應多個 Chunk，透過 Django ForeignKey 關聯。
- `(document, page, chunk_index)` 具有唯一性約束。
- Qdrant Point ID 對應 PostgreSQL Chunk，檢索時由 Point ID 找回原始文字。

索引狀態包含 `uploaded`、`indexing`、`indexed`、`failed`。索引失敗時可重新呼叫索引 API。

## API

| 方法 | 路徑 | 功能 |
| --- | --- | --- |
| GET | `/health/` | 檢查 Django 與 PostgreSQL |
| GET | `/api/documents/` | 分頁列出文件 |
| POST | `/api/documents/` | 上傳並切分 PDF |
| GET | `/api/documents/{id}/` | 查看文件與索引狀態 |
| POST | `/api/documents/{id}/index/` | 建立或重建向量索引 |
| POST | `/api/search/` | 依問題檢索相關 Chunk |
| POST | `/api/ask/` | 生成答案並回傳來源引用 |

正式環境要求 `X-API-Key` Header。以下範例使用本機環境；若設定了 `PROJECT_API_KEY`，請在請求中加入對應 Header。

### 上傳 PDF

```powershell
# 上傳具有文字層的 PDF；預設檔案大小上限為 10 MiB
curl.exe -X POST "http://localhost:8000/api/documents/" -F "title=測試文件" -F "file=@sample.pdf"
```

回應中的 `id` 是後續建立索引所需的文件 ID。

### 建立索引

```powershell
# 將 1 改為上傳回應的文件 ID
curl.exe -X POST "http://localhost:8000/api/documents/1/index/"
```

### 語意搜尋

```powershell
# 搜尋指定文件的相關段落
curl.exe -X POST "http://localhost:8000/api/search/" -H "Content-Type: application/json" -d '{\"query\":\"這份文件的請假規定是什麼？\",\"document_id\":1,\"top_k\":5}'
```

### 文件問答

```powershell
# 問答回傳 answer 與 citations；請依實際文件內容提問
curl.exe -X POST "http://localhost:8000/api/ask/" -H "Content-Type: application/json" -d '{\"query\":\"這份文件的請假規定是什麼？\",\"document_id\":1}'
```

搜尋與問答均可設定 `top_k`、`score_threshold` 與選用的 `document_id`。問答端點會從生成文字中的 `[1]` 或 `【1】` 等引用編號，篩選對應的引用資訊。若沒有檢索結果，會回傳 `citations: []`。

## 本機執行

### 前提條件

- Docker Desktop 與 Docker Compose
- 可使用的 OpenAI API Key

```powershell
# 1. 複製環境變數範本
Copy-Item .env.example .env

# 2. 編輯 .env，至少設定 POSTGRES_PASSWORD 與 OPENAI_API_KEY
#    若要啟用 API Key 驗證，可另外設定 PROJECT_API_KEY

# 3. 建置並啟動 Django、PostgreSQL、Qdrant
docker compose up -d --build

# 4. 執行資料庫 Migration
docker compose exec web python manage.py migrate

# 5. 驗證服務
curl.exe http://localhost:8000/health/
```

本機 Docker Compose 使用 Django 開發伺服器；正式映像的 Dockerfile 使用 Gunicorn。請勿將 `.env` 或真實 API Key 提交至 GitHub。

## 自動化測試與 CI

```powershell
# 執行 Django 單元測試
docker compose exec web python manage.py test
```

目前有兩個問答引用測試：

1. 模型使用中文括號引用 `【1】` 時，只回傳實際引用的 Chunk。
2. 回答沒有引用編號時，回傳空的 `citations`。

測試以 Mock 隔離 OpenAI 與 Qdrant，未涵蓋所有外部服務的端到端整合。GitHub Actions 在 push 與 pull request 時執行：

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test --verbosity 2`

CI 使用 PostgreSQL 16 服務執行 Django 檢查與測試。

## 安全性與錯誤處理

- 上傳僅接受 `.pdf` 副檔名，預設上限 10 MiB，解析失敗會回傳 400。
- 正式環境要求長度至少 32 字元的 `PROJECT_API_KEY`，透過 `X-API-Key` 驗證。
- Django REST Framework 設有匿名請求節流設定（`30/min`）；此限制不應視為完整的成本防護。
- OpenAI 或 Qdrant 操作失敗時，相關 API 回傳 503，詳細例外記錄在伺服器日誌。
- 正式環境要求關閉 Debug 並設定安全的 Django Secret Key。
- 請勿將機密文件上傳至公開展示環境。

## 已知限制

- 僅支援可擷取文字的 PDF，尚無 OCR。
- Chunking 依固定字元長度切分，尚未加入語意段落切分。
- Embedding 與索引在同步 HTTP 請求中執行，大型文件可能較耗時。
- PostgreSQL 與 Qdrant 分屬不同儲存系統，索引失敗時需要依狀態重新執行；跨系統沒有單一資料庫交易。
- 引用篩選依模型輸出的編號判斷，引用存在仍需核對原始內容。
- 專案目前提供後端 API，尚無獨立操作介面。
- Railway 應用容器內的上傳檔案可能隨重新部署或重啟消失；長期保存需額外的持久化儲存方案。

## 程式碼導覽

| 路徑 | 用途 |
| --- | --- |
| `backend/documents/models.py` | Document、Chunk 資料模型 |
| `backend/documents/serializers.py` | 上傳與查詢參數驗證 |
| `backend/documents/views.py` | 上傳、索引、搜尋與問答 API |
| `backend/documents/permissions.py` | API Key 權限檢查 |
| `backend/services/pdf_chunker.py` | PDF 文字擷取與切分 |
| `backend/services/embedding.py` | OpenAI Embedding |
| `backend/services/qdrant_store.py` | Qdrant Collection、索引與搜尋 |
| `backend/services/retrieval.py` | 向量檢索與 Chunk 對應 |
| `backend/services/llm.py` | 問答 Prompt 與模型呼叫 |
| `backend/documents/tests.py` | 問答引用單元測試 |
| `.github/workflows/tests.yml` | GitHub Actions CI |
