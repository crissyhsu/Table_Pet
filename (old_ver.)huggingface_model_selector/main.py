from config import HF_TOKEN
from ollama_function import classify_prompt, translate_to_english
from hf_search import search_models
from model_loader import load_model

def main():

    print("🧠 歡迎使用 Hugging Face 自動擴充模型器")
    
    while True:
        user_prompt = input("請輸入你的任務描述（例如：中英翻譯 / 小說生成 / 情感分析）: ")
        predicted_task = classify_prompt(user_prompt)
        user_prompt = translate_to_english(user_prompt)

        if predicted_task == "unknown":
            print("❗ 無法判斷任務類型，請再試一次或重新描述任務。")
            return

        print(f"\n🔍 任務是：{user_prompt}，推論任務類型為：{predicted_task}，正在搜尋對應模型...\n")
        results = search_models(
            task_keywords = predicted_task,
            user_prompt = user_prompt,
            token = HF_TOKEN
        )

        if results:
            break
        else:
            print("❌ 沒有找到符合的模型，請重新輸入。")

    for i, r in enumerate(results):
        print(f"[{i}] 模型 ID: {r['id']}")
        print(f"     Tags: {r['tags']}")
        print(f"     📁 模型大小: {r['size_mb']}")
        print(f"     👍 喜歡數: {r['likes']}, ⬇️ 下載數: {r['downloads']}")
        print(f"     🔔 最近更新: {r['lastModified']}\n")
        
    
    while True:
        try:
            choice = int(input("請選擇一個模型的編號來載入: "))
            selected_model_id = results[choice]['id']
            break
        except (ValueError, IndexError):
            print("請輸入有效的模型編號。")

    print(f"⏬ 正在載入模型 {selected_model_id}...")
    model, tokenizer = load_model(selected_model_id)
    if model is None:
        print("❗ 載入失敗，請選擇其他模型")
        return
    elif model == "ollama":
        print("✅ GGUF 模型已經透過 Ollama 執行。")
        return
    else:
        print(f"✅ Transformers 模型 {selected_model_id} 載入完成，可開始使用！")
        print(rf"模型已存在資料夾中！➡️  C:\Users\USER\.cache\huggingface\hub")

if __name__ == "__main__":
    main()
