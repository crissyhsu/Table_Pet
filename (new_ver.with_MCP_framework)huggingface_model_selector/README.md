# 專案：本地化學習且可自行擴充之語言模型陪伴軟體

## 軟體功能說明
類型 - 功能描述：
🎯 核心功能：個性記憶、模型搜尋/擴充、PyQt5 UI、Q&A（Qwen + phi）、情緒辨識、考古題生成、學習規劃
🐣 附加創新功能：手勢生成音樂、音樂轉影片、報告演練與提問模擬、學習成效預測
💻 執行方式：本地部署為桌寵式應用（PyQt5），整合本地 LLM、工具、自定任務擴充

## 專案程式碼架構
project/
├─ core/                         # MCP 中樞：路由與策略
│  └─ router.py                  # Router：判斷意圖→呼叫工具→回傳結果
│
├─ tools/                        # 工具層：HF 搜尋、模型載入、Ollama 介面
│  ├─ hf.py                      # → 包裝 hf_search.search_models()
│  ├─ models.py                  # → 包裝/路由 transformers vs. ollama
│  └─ ollama_tool.py             # → 包裝 classify / translate
│
├─ services/                     # 服務層：記憶、日誌、設定、資料層（尚未實作，但預計之後會）
│  ├─ __init__.py
│  ├─ memory.py                  # SQLite 記憶（之後要做）
│  └─ logging.py                 # 統一 logging（之後要做）
│
├─ ui/                           # 前端介面
│  ├─ gradio_app/                # 現有的 Gradio 介面
│  │  └─ app.py                  # → 由現在 gradio_ui.py 改名遷入
│  └─ pyqt_app/                  # 桌寵 PyQt5（之後新增）
│     └─ desktop_pet.py
│
├─ configs/
│  ├─ config.py                  # env 讀取（HF_TOKEN 等）
│  └─ .env                       # 範例（不含私密值）
│
├─ data/                         # 尚未實作，但預計之後會
│  ├─ app.db                     # SQLite（建立後產生）
│  └─ runs/                      # 搜尋/下載紀錄（csv/jsonl）
│
│
├─ hf_search.py
├─ model_loader.py
├─ ollama_function.py
├─ main.py                       # CLI 入口（呼叫 core.router）
├─ requirements.txt              # 各個模組套件的版本、依賴關係
└─ README.md