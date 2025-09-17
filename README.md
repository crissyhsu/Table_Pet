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

## 目前效果呈現
1. 程式執行後，小桌寵會以透明背景出現在桌面上//
<img width="1644" height="1029" alt="image" src="https://github.com/user-attachments/assets/7b0294f0-5984-402c-8326-c3d6b980dd3b" />
2. 用鼠標拖拉住小桌寵可使其播放托跩動畫，放開便會落下//
<img width="992" height="482" alt="image" src="https://github.com/user-attachments/assets/972e7d49-2c1b-4bfc-9302-1bfc45280ed4" />
3. 對小桌寵按右鍵，便會出現對話選項，點按會出現對話框//
 <img width="1038" height="728" alt="image" src="https://github.com/user-attachments/assets/03bb1968-eee6-4c65-b0c9-fd97c6c77f20" />
4. 模型會根據現有的記憶回答問題(就算重啟記憶的檔案還是會在)//
<img width="586" height="190" alt="image" src="https://github.com/user-attachments/assets/eca0c730-bc1b-4df3-bd73-84b1a9913a65" />
<img width="574" height="181" alt="image" src="https://github.com/user-attachments/assets/289da691-7341-47ba-b445-09c7658af232" />
5. 也可以主動告訴它需要記憶的內容//
<img width="558" height="255" alt="image" src="https://github.com/user-attachments/assets/051be697-679c-46f7-a1b0-6297aa26dec5" />
6. 讀書陪伴功能可設定讀書計時器，其可以任由使用者藉由鼠標移動到想要的位置//
<img width="729" height="484" alt="image" src="https://github.com/user-attachments/assets/93a7902b-fb07-45ca-8c6f-2f1811b11c6f" />
7. 究極專注模式則是會確認桌面上是否有工作無關緊要的視窗，如果你回答「不是作業需要」，小桌寵就會將視窗以拋物線丟出去關閉//
<img width="421" height="271" alt="image" src="https://github.com/user-attachments/assets/190c65c6-06d9-485b-991e-7d1b8c013c53" />
<img width="1085" height="890" alt="image" src="https://github.com/user-attachments/assets/efee5b4f-3dd6-4aef-b661-d82211af018f" />



## 之後會加強的方向與解決猜想
1. 把小桌寵的人設記憶與使用者相關的記憶分開
2. 回傳回覆時，分類情緒，切換小桌寵表情 
3. 可以藉由貝式模型加強是否記憶的判斷
4. 將system prompt分開儲存以實現多角色的效果
5. 考慮轉到Godot或使用blender建立2D角色骨架，以便未來拓展多角色可快速更換角色造型
6. 嘗試製作多角色聊天室
