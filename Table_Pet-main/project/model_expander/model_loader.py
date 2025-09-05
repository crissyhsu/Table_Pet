import ollama
import subprocess
from .config import HF_TOKEN

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

# --- 下面是新增的工具 ---
from huggingface_hub import snapshot_download
from .expander_registry import register_model, suggested_local_dir

def ensure_local_copy(repo_id: str) -> str:
    """
    下載整個 repo 到 project/expanded_models/<安全名>，回傳本地路徑。
    """
    local_dir = suggested_local_dir(repo_id)  # 例如 project/expanded_models/org__name
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # 寫實體檔，避免 symlink 踩雷
        ignore_patterns=[]              # 也可保留空，完整下載
    )
    return local_dir

def register_transformers(repo_id: str, task: str, local_dir: str):
    register_model(
        repo_id=repo_id,
        backend="transformers",
        task=task or "",
        local_path=local_dir,
        notes=""
    )
