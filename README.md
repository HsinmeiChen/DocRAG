# DocRAG
以 Django、PostgreSQL、Qdrant 與 OpenAI 建置的 PDF 文件問答 API，支援語意檢索與來源引用。

本專案是一個基於 RAG（檢索增強生成）架構的企業文件問答系統後端服務，核心目的在於完整實作包含動態上傳、文本分段、向量化儲存、語意檢索及動態提示詞生成的完整 RAG 技術鏈；專案專注於後端架構與資料流實作，完全採用 Docker Compose 進行容器化管理，並利用 Django ORM 進行關聯式資料庫控制，以確保開發與部署環境的一致性與可擴充性。

1. 系統架構與角色分工
本系統由三個核心元件協同運作：

PostgreSQL：
關聯式資料庫，由 Django ORM 進行資料庫管理。負責儲存原始文件的元數據（Metadata，如檔名、上傳時間）與切分後的文字區塊（Chunks），作為系統的真實資料來源（Single Source of Truth）。

Qdrant：
分散式向量資料庫，儲存由文字轉化而來的向量特徵（Embedding），並採用 Cosine（餘弦相似度）演算法進行高維度向量的語意搜尋。

OpenAI API：
負責呼叫 text-embedding-3-small 產生高維度文字向量，並在問答階段調用大語言模型（LLM）生成最終的脈絡化回答。

[資料流與技術流程]

A. 知識庫建置流水線 (Data Pipeline)
上傳 PDF -> 文字擷取 -> 文本分段 (Chunking)
├──> 使用 Django ORM 寫入 PostgreSQL (儲存原始內文)
└──> 呼叫 OpenAI Embedding -> 寫入 Qdrant (儲存向量索引)

B. 使用者問答檢索流程 (RAG Flow)
使用者提問 -> 轉換為問題向量 -> Qdrant 語意搜尋 -> 撈取 Top-K 相關段落
├──> 組裝 Context + Prompt -> 傳給 OpenAI (LLM) -> 回傳答案

2. 技術棧 (Tech Stack)
程式語言與框架：Python 3.12, Django REST Framework (DRF)

資料庫與基礎設施：PostgreSQL, Qdrant (Vector Database)

AI 開發套件：OpenAI API

容器化部署：Docker, Docker Compose

3. API 端點說明
本專案為純後端 API 服務，支援透過 Postman 或 cURL 進行接口測試與資料驗證：

功能 1：上傳與解析文件

HTTP 方法：POST
URL 端點：/api/documents/
說明：驗證並解析 PDF，將文件內容切分為 Chunks，再把文件資訊與 Chunks 儲存至 PostgreSQL。

功能 2：建立向量索引

HTTP 方法：POST
URL 端點：/api/documents/{id}/index/
說明：為指定文件的 Chunks 產生 Embedding，寫入 Qdrant，並記錄文件的索引狀態。

功能 3：語意搜尋

HTTP 方法：POST
URL 端點：/api/search/
說明：將問題轉換為向量，從 Qdrant 取回相似度最高的文件段落，可限定指定文件。

功能 4：文件問答

HTTP 方法：POST
URL 端點：/api/ask/
說明：根據檢索結果生成回答，回傳頁碼、Chunk 位置與相似度；只保留回答實際使用的引用。


4. 生產環境工程實踐與健全性設計
本專案在架構設計與實作上，遵循以下生產環境工程標準：

分散式資料：嚴格劃分關聯式資料庫（儲存結構化元數據與真實內文）與向量資料庫（儲存特徵向量並專注於相似度檢索）的角色分工，確保資料庫群組的獨立擴展性。

資料庫版本控制：完全透過 Django ORM 進行一對多（One-to-Many）的文件與文字區塊（Chunks）資料模型宣告，並透過 Migration 機制確保資料庫綱要（Schema）的版本控制一致性。

環境隔離與持久化：全系統服務均配置於 Docker Container 虛擬化環境中，利用 Docker Compose 管理獨立的網路拓撲與資料磁碟卷（Volume）持久化設計，免除本機環境差異導致的運行衝突。

防禦性編程與容錯：

實作自動化 ensure_collection() 機制：系統在執行索引建立或檢索時，後端會自動檢查並動態建立符合規格的 Qdrant Collection。

具備針對外部 API（如 OpenAI）額度限制（Quota Exceeded）與網路逾時的異常攔截與錯誤處理機制，確保後端主程式的生命週期穩定。

5. 快速開始 (How to Run)
[前提條件]
電腦需安裝 Docker Desktop ( https://www.docker.com/products/docker-desktop/ )

準備一組可用的 OpenAI API Key

[Step 1: 配置環境變數]
請在專案根目錄下建立一個名為 .env 的檔案，並填入以下內容：

OPENAI_API_KEY=你的OpenAI金鑰
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=enterprise_docs

[Step 2: 啟動系統與資料庫遷移]
開啟終端機（PowerShell 或 Terminal），進入專案資料夾並執行以下指令：

1. 建立並在背景啟動所有 Docker 容器 (Django, PostgreSQL, Qdrant)
docker compose up -d

2. 執行 Django 資料庫遷移，讓 Django ORM 自動在 PostgreSQL 中建立所需的資料表
docker compose exec web python manage.py migrate

(註：若您 docker-compose 中的 Django 服務名稱不為 web，請將上面指令中的 web 替換為對應的服務名稱。)

[Step 3: 健康檢查]
系統啟動後，可透過瀏覽器或 Postman 訪問健康檢查端點：
http://localhost:8000/health/

若看見以下 JSON 回應，代表所有容器與關聯資料庫皆正常連線運行：
{"status":"ok","db":1}

6. 自動化測試

執行方式：
docker compose exec web python manage.py test

目前測試涵蓋：

- 回答使用中文引用格式【1】時，只回傳實際使用的文件段落。
- 文件無法回答問題時，不回傳無關引用。
- 測試使用 Mock 隔離 OpenAI 與 Qdrant，不會產生外部 API 費用。

預期結果：
Ran 2 tests
OK


7. 目前成果與限制

[已完成]

- 完成 PDF 上傳、文字擷取、Chunking、Embedding、向量索引與語意檢索流程。
- 問答可限定指定文件，並回傳頁碼、Chunk 位置與相似度。
- 只回傳答案實際使用的引用，無法回答時不附加無關引用。
- 使用 Docker Compose 整合 Django、PostgreSQL 與 Qdrant。
- 使用自動測試驗證引用篩選，並透過 Mock 隔離外部服務。

[目前限制]

- 僅支援具有文字層的 PDF，掃描文件尚未加入 OCR。
- 文件索引採同步處理，大型文件可能需要較長的請求時間。
- LLM 仍可能改寫文件措辭，使用者應搭配引用段落核對原文。
- 目前提供後端 API，尚未實作操作介面。