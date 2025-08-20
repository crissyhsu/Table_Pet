import gradio as gr
import pandas as pd
from config import HF_TOKEN
from ollama_function import classify_prompt, translate_to_english
from hf_search import search_models
from model_loader import load_model

# 預設 DataFrame 欄位
DEFAULT_COLUMNS = ["id", "task", "size_mb", "likes", "downloads", "lastModified"]

def search_ui(user_prompt: str):
    """
    1. 判斷任務類型；
    2. 顯示初始狀態；
    3. 翻譯並搜尋模型；
    4. 回傳 DataFrame、下拉選單選項及狀態文字更新。
    """
    predicted = classify_prompt(user_prompt)
    if predicted == "unknown":
        msg = f"❗ 無法判斷任務類型：{user_prompt}；請再試一次或重新描述任務。"
        return (
            gr.update(value=pd.DataFrame(columns=DEFAULT_COLUMNS)),
            gr.update(choices=[], value=None),
            gr.update(value=msg)
        )
    # 翻譯並搜尋
    en = translate_to_english(user_prompt)
    # 初始狀態
    initial = f"🔍 任務是：{en}；推論任務類型為：{predicted}，正在搜尋對應模型..."
    results = search_models(
        task_keywords = predicted,
        user_prompt = en,
        token = HF_TOKEN
    )
    # 若無結果
    if not results or not isinstance(results, list):
        msg = f"{initial}\n❌ 未搜尋到任何模型。"
        return (
            gr.update(value=pd.DataFrame(columns=DEFAULT_COLUMNS)),
            gr.update(choices=[], value=None),
            gr.update(value=msg)
        )
    # 建立 DataFrame，並確保所有預設欄位
    df = pd.DataFrame(results)
    df = df.reindex(columns=DEFAULT_COLUMNS)
    # 補齊缺失值
    df = df.fillna("N/A")
    final = f"✅ 找到 {len(df)} 筆模型。請從下拉選單點擊選擇要下載的模型。"
    status = f"{initial}\n{final}"
    return (
        gr.update(value=df),
        gr.update(choices=df["id"].tolist(), value=None),
        gr.update(value=status)
    )


def load_ui(model_id: str):
    """針對選定模型進行下載並回傳狀態更新"""
    if not model_id:
        msg = "❗ 請先從下拉選單選擇一個模型。"
    else:
        model, _ = load_model(model_id)
        if model is None:
            msg = f"❗ 載入失敗：{model_id}；請選擇其他模型。"
        elif model == "ollama":
            msg = f"✅ GGUF 模型 {model_id} 已透過 Ollama 執行。"
        else:
            msg = f"✅ Transformers 模型 {model_id} 載入完成！"
    return gr.update(value=msg)


# Gradio UI 定義
with gr.Blocks() as demo:
    gr.Markdown("## 🧠 歡迎使用 Hugging Face 自動擴充模型器")
    with gr.Row():
        prompt = gr.Textbox(label="任務描述", placeholder="例如：小說生成 / 情感分析")
        btn = gr.Button("🔍 搜尋模型")

    result = gr.Dataframe(
        headers=DEFAULT_COLUMNS,
        interactive=False,
        label="搜尋結果"
    )
    selector = gr.Dropdown(
        label="可下載的模型 ID",
        choices=[],
        allow_custom_value=False
    )
    status = gr.Textbox(label="狀態", interactive=False, lines=4)

    # 綁定事件
    btn.click(
        fn=search_ui,
        inputs=[prompt],
        outputs=[result, selector, status]
    )
    selector.select(
        fn=load_ui,
        inputs=[selector],
        outputs=[status]
    )

if __name__ == "__main__":
    demo.launch()
