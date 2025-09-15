# 有記憶的語言模型系統
## 需事先安裝
```
pip install -r requirements.txt
```
此外，還需要用`.env`去設定`OpenRouter`的API_KEY

## 各檔案說明
- `main.py`：整合各功能套件，要執行時按這個就行。(是import下面四個檔案，所以都要有才能執行)
- `memory_system.py`：記憶系統，用Meta他們家的embedding套件，目前的版本是會在每次給LLM的API前，找出三條最相關的記憶，一起加到prompt。判斷是否記憶的部分用奇妙的方式解決了
- `llm_api.py`：處理把prompt推給LLM的code，如果想換一個model，直接改model名稱就行
- `chat_dialog.py`：控制對話框資訊(字體大小、顯示格式......那些)
- `desktop_pet.py`：控制小桌寵的動作與選單
- `window_manager.py`：專門處理丟視窗的code
- `study_timer.py`：控制「陪讀模式」的計時器視窗
---
這邊是單純測試用的code：
- `Find_mem_to_LLM.py`：一個確認`memory_system.py`中的功能外部調用是否正常的測試檔(執行下去輸入想講的話就行)
- `LLM_test2.py`：裡面寫了如何用`OpenRouter`的API去掉用免費的大語言模型(API Key需自行上`OpenRouter`申請)
- `Table_Pet_to_LLM.py`：對角色右鍵就會出現對話選項，可以向LLM發送使用者的輸入

## 檔案架構
```
Table_Pet/
├── main.py              # 主程式(按這個執行就行)
├── memory_system.py     # 記憶系統核心
├── llm_api.py          # LLM API 處理
├── chat_dialog.py      # 對話框介面
├── desktop_pet.py      # 桌寵控制邏輯
├── window_manager.py   # 視窗管理(丟視窗功能主要在這)
├── study_timer.py      # 學習計時器
├── requirements.txt    # 依賴套件
└── tests/              # 測試檔案(只是每個很小的功能測試)
    ├── Find_mem_to_LLM.py
    ├── LLM_test2.py
    └── Table_Pet_to_LLM.py
```

## 之後會加強的方向與解決猜想
1. 把小桌寵的人設記憶與使用者相關的記憶分開
2. 回傳回覆時，分類情緒，切換小桌寵表情 
3. 可以藉由貝式模型加強是否記憶的判斷
4. 將system prompt分開儲存以實現多角色的效果
5. 考慮轉到Godot或使用blender建立2D角色骨架，以便未來拓展多角色可快速更換角色造型
6. 嘗試製作多角色聊天室