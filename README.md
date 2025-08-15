# 有記憶的語言模型系統
## 需事先安裝
```
pip install sentence-transformers faiss-cpu numpy
```
## 各檔案說明
- `memory_system.py`：寫了memory系統的主要class，但目前對於「刪除部分相關記憶」以及「判斷使用者之輸入是否需要記憶」仍須加強
- `Find_mem_to_LLM`：一個確認`memory_system.py`中的功能外部調用是否正常的測試檔(執行下去輸入想講的話就行)
- `LLM_test2.py`：裡面寫了如何用`OpenRouter`的API去掉用免費的大語言模型(API Key需自行上`OpenRouter`申請)

## 之後會加強的方向與解決猜想
1. **判斷輸入是否需要記憶**：如果上HuggingFace 抓模型時就已經會用Llama3.2去判斷的話，感覺這一塊之後可以多下幾句prompt整合過去？
2. **刪除部分相關記憶**：目前的情況它很容易全刪，之後可能改成只能刪一條，或是要看信心分數決定