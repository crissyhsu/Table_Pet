import ollama
import subprocess
from configs.config import HF_TOKEN

from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
)
from huggingface_hub import HfApi

def load_model(model_id):
    api = HfApi()
    info = api.model_info(model_id, token=HF_TOKEN)

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN)

        task = info.pipeline_tag or ""
        if task == "text-generation":
            model = AutoModelForCausalLM.from_pretrained(model_id, token=HF_TOKEN)
        elif task == "text-classification":
            model = AutoModelForSequenceClassification.from_pretrained(model_id, token=HF_TOKEN)
        elif task == "token-classification":
            model = AutoModelForTokenClassification.from_pretrained(model_id, token=HF_TOKEN)
        elif task in ("translation", "summarization"):
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id, token=HF_TOKEN)
        else:
            print(f"⚠️ 不支援的 pipeline_tag：{task}，請選擇其他模型")
            return None, None

        return model, tokenizer

    except Exception as e:
        print(f"❗ Transformers 載入失敗：{e}")
        return None, None
