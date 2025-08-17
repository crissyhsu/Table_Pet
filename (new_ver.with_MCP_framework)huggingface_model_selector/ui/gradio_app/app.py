import gradio as gr
import pandas as pd
from config import HF_TOKEN
from ollama_function import classify_prompt, translate_to_english
from hf_search import search_models
from model_loader import load_model

from core.router import Router
router = Router()

# 預設 DataFrame 欄位
DEFAULT_COLUMNS = ["id", "task", "size_mb", "likes", "downloads", "lastModified"]

def search_ui(user_prompt: str):
    out = router.handle(user_prompt)
    if out.get("type") != "search_results":
        msg = out.get("message", "❗ 無法搜尋模型")
        return (
            gr.update(value=pd.DataFrame(columns=DEFAULT_COLUMNS)),
            gr.update(choices=[], value=None),
            gr.update(value=msg)
        )
    items = out["items"]
    df = pd.DataFrame(items).reindex(columns=DEFAULT_COLUMNS).fillna("N/A")
    status = f"🔍 任務是：{out['query_en']}；推論任務類型為：{out['task']}，正在搜尋對應模型...\n✅ 找到 {len(df)} 筆模型。請從下拉選單點擊選擇要下載的模型。"
    return (
        gr.update(value=df),
        gr.update(choices=df["id"].tolist(), value=None),
        gr.update(value=status)
    )

def load_ui(model_id: str):
    if not model_id:
        return gr.update(value="❗ 請先從下拉選單選擇一個模型。")
    out = router.handle(f"下載：{model_id}")
    if out.get("type") == "execute":
        if out.get("engine") == "ollama":
            return gr.update(value=f"✅ GGUF 模型 {model_id} 已透過 Ollama 執行（或可建立 Modelfile）。")
        return gr.update(value=f"✅ Transformers 模型 {model_id} 載入完成！")
    return gr.update(value=f"❗ 載入失敗：{out.get('message','未知錯誤')}")

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
