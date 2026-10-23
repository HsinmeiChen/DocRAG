# DocRAG

以 Django、PostgreSQL、Qdrant 與 OpenAI 建置的 PDF 文件問答 API，支援語意檢索與來源引用。

這是一個用來練習 RAG（檢索增強生成）流程的後端專案。使用者可以上傳具有文字層的 PDF，系統會擷取文字、切分內容並建立向量索引，再根據提問找出相關段落，交由語言模型整理回答並附上引用來源。

專案以 Django REST Framework 提供 API，本機開發使用 Docker Compose，線上版本部署於 Railway。

## 線上部署

- API：https://docrag-production-4c8d.up.railway.app/
- Health Check：https://docrag-production-4c8d.up.railway.app/health/
- 線上環境使用 Railway 執行 Django、Gunicorn 與 PostgreSQL，向量資料儲存於 Qdrant Cloud。

健康檢查回應：

```json
{
  "status": "ok",
  "db": 1
}
```

## 1. 系統架構

系統包含三個主要元件：

**PostgreSQL**

儲存文件資訊與切分後的文字內容，並透過 Django ORM 管理資料。

**Qdrant**

儲存文字的 embedding，並使用餘弦相似度找出與問題相關的段落。

**OpenAI API**

產生文件與問題的 embedding，並根據檢索出的內容生成回答。

### 文件索引流程

```text
上傳 PDF
  -> 擷取文字
  -> 切分內容（Chunking）
  -> 將文件與 Chunks 儲存至 PostgreSQL
  -> 產生 Embedding
  -> 將向量寫入 Qdrant
```

### 問答流程

```text
使用者提問
  -> 產生問題向量
  -> 從 Qdrant 取回相關段落
  -> 組合 Context 與 Prompt
  -> 呼叫語言模型
  -> 回傳答案與引用來源
```

## 2. 使用技術

- Python 3.12
- Django、Django REST Framework
- PostgreSQL
- Qdrant
- OpenAI API
- Docker、Docker Compose
- Railway、Gunicorn
- GitHub Actions

## 3. API 端點

本專案目前提供後端 API，可使用 Postman 或 cURL 測試。

| 功能 | HTTP 方法 | 路徑 | 說明 |
| --- | --- | --- | --- |
| 上傳文件 | POST | `/api/documents/` | 驗證並解析 PDF，將文件與切分後的內容儲存至 PostgreSQL。 |
| 建立索引 | POST | `/api/documents/{id}/index/` | 為指定文件產生 embedding，寫入 Qdrant，並更新索引狀態。 |
| 語意搜尋 | POST | `/api/search/` | 從 Qdrant 取回與問題相關的段落，可限定指定文件。 |
| 文件問答 | POST | `/api/ask/` | 根據檢索結果生成回答，並回傳頁碼、Chunk 位置與相似度。 |

## 4. 實作上的考量

- PostgreSQL 儲存文件與文字內容，Qdrant 負責向量搜尋，兩者分別處理不同類型的資料。
- 使用 Django Migration 管理資料表結構。
- 本機使用 Docker Compose 啟動 Django、PostgreSQL 與 Qdrant；線上環境使用 Railway、PostgreSQL 與 Qdrant Cloud。
- 建立文件索引時，程式會檢查 Qdrant collection 的向量維度，並建立 `document_id` payload index，讓查詢可以限定文件。
- 呼叫 OpenAI 或 Qdrant 失敗時，API 會回傳統一的 `503` 回應，詳細錯誤只記錄在伺服器 log。

## 5. 快速開始

### 前提條件

- 安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 準備可使用的 OpenAI API Key

### Step 1：設定環境變數

在專案根目錄複製範例設定檔：

```powershell
Copy-Item .env.example .env
```

接著編輯 `.env`，至少填入本機 PostgreSQL 密碼與 OpenAI API Key。其他設定可先沿用範例值。

### Step 2：啟動服務

```powershell
docker compose up -d
```

執行 Django migration：

```powershell
docker compose exec web python manage.py migrate
```

### Step 3：健康檢查

開啟：

```text
http://localhost:8000/health/
```

若看到以下回應，代表 Django 已啟動，且可以連線至 PostgreSQL：

```json
{
  "status": "ok",
  "db": 1
}
```

## 6. 自動化測試

執行方式：

```powershell
docker compose exec web python manage.py test
```

目前測試涵蓋：

- 回答使用中文引用格式 `【1】` 時，只回傳實際使用的文件段落。
- 文件無法回答問題時，不回傳無關引用。
- 使用 Mock 隔離 OpenAI 與 Qdrant，測試過程不會呼叫外部 API。

預期結果：

```text
Ran 2 tests
OK
```

## 7. 目前成果與限制

### 已完成

- 完成 PDF 上傳、文字擷取、Chunking、Embedding、向量索引與語意檢索流程。
- 問答可限定指定文件，並回傳頁碼、Chunk 位置與相似度。
- 只回傳答案實際使用的引用，無法回答時不附加無關引用。
- 使用 Docker Compose 整合本機開發所需服務。
- 使用自動化測試驗證引用篩選，並透過 Mock 隔離外部服務。
- 部署至 Railway，並連接 PostgreSQL、Qdrant Cloud 與 OpenAI API。
- 使用健康檢查確認 Web 服務與 PostgreSQL 連線狀態。
- 為 Qdrant 的 `document_id` 建立 payload index，支援依文件過濾的向量查詢。

### 目前限制

- 僅支援具有文字層的 PDF，掃描文件尚未加入 OCR。
- 文件索引採同步處理，大型文件可能需要較長的請求時間。
- LLM 仍可能改寫文件措辭，使用者需要搭配引用段落核對原文。
- 目前只提供後端 API，尚未實作操作介面。
- Railway 應用容器內的上傳檔案屬於暫存資料；若要長期保存，需要改用 S3 相容的物件儲存。
