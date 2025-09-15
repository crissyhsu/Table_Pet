# 有記憶的語言模型系統
## 需事先安裝
```
pip install -r requirements.txt
```
此外，還需要用`.env`去設定`OpenRouter`的API_KEY

## 各檔案說明
- `app/main.py`：整合各功能套件，要執行時在project/的目錄下輸入"python -m app.Main"就行！
- `memory_system.py`：記憶系統，用Meta他們家的embedding套件，目前的版本是會在每次給LLM的API前，找出三條最相關的記憶，一起加到prompt。判斷是否記憶的部分用奇妙的方式解決了
- `llm_api.py`：處理把prompt推給LLM的code，如果想換一個model，直接改model名稱就行
- `chat_dialog.py`：控制對話框資訊(字體大小、顯示格式......那些)
- `desktop_pet.py`：控制小桌寵的動作與選單

## 之後會加強的方向與解決猜想
1. 把小桌寵的人設記憶與使用者相關的記憶分開
2. 回傳回覆時，分類情緒，切換小桌寵表情 
3. ~~增強是否記憶的判斷~~(已解決) 

---
以下是檔案的結構
project/
│
├─ app/
|  |
|  ├─ Idle/                     # 放桌寵"待機"狀態的圖
│  ├─ Walk/                     # 放桌寵"走路"狀態的圖
│  ├─ Take/                     # 放桌寵"拎起來"狀態的圖
|  |
|  ├─ __init__.py               # 空的
│  ├─ chat_dialog.py            # 控制對話框資訊(字體大小、顯示格式......那些)
|  ├─ desktop_pet.py            # 控制小桌寵的動作與選單
│  ├─ llm_api.py                # 處理把prompt推給LLM的code，如果想換一個model，直接改model名稱就行
|  ├─ memory_system.py          # 記憶系統
│  ├─ model_expander_ui.py      # 整合model_expander/中的功能操作進來
|  ├─ window_manager.py         # 專門處理丟視窗的code
|  ├─ study_timer.py            # 控制「陪讀模式」的計時器視窗
│  └─ Main.py                   # 主程式碼
│
├─ model_expander/              # 擴充的工具層：hugging face模型的搜尋、模型載入、Ollama功能等等
|  ├─ __init__.py               # 空的
│  ├─ config.py                 # 導入存放在環境變數中的token
|  ├─ expander_registry.py      # "使用"註冊過已擴充的模型
│  ├─ hf_search.py              # "搜尋"模型的相關程式碼
│  ├─ model_loader.py           # "下載"模型的相關程式碼
│  └─ ollama_function.py        # 使用本地 LLM 進行分類任務以及翻譯英文
|
├─ requirements.txt
└─ README.md