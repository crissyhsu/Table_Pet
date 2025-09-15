import ollama
import subprocess
from typing import Any, Dict, Tuple, Optional
from .config import HF_TOKEN
from huggingface_hub import snapshot_download, HfApi
from .expander_registry import register_model, suggested_local_dir, get_adapter

from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoModelForSeq2SeqLM,
    AutoConfig, AutoTokenizer, AutoModel
)

# 一些常見 encoder–decoder 家族（遇到這些，優先走 Seq2Seq）
ENCDEC_FAMILIES = {
    "t5", "mt5", "bart", "mbart", "marian", "pegasus", "prophetnet"
}

# 某些 pipeline_tag 對應的預設 Loader
TASK_TO_LOADER = {
    "text-generation": "causal",          # 但若 cfg 是 enc-dec → 自動切 seq2seq
    "summarization": "seq2seq",
    "translation": "seq2seq",
    "text-classification": "seqcls",
    "token-classification": "tokcls",
    "feature-extraction": "auto",
    # 其餘任務（asr、image-to-text、text-to-image…）交給你的 Adapter，不用這個 loader
}

def _pick_loader_kind(pipeline_tag: Optional[str], cfg) -> str:
    """
    回傳 'causal' / 'seq2seq' / 'seqcls' / 'tokcls' / 'auto'
    """
    # 1) 先看 pipeline_tag 的直覺對應
    if pipeline_tag in TASK_TO_LOADER:
        kind = TASK_TO_LOADER[pipeline_tag]
    else:
        kind = "causal"  # 預設先試 decoder-only（最常見）

    # 2) 若模型本質是 encoder–decoder，強制改成 seq2seq
    is_encdec = getattr(cfg, "is_encoder_decoder", False)
    model_type = (getattr(cfg, "model_type", "") or "").lower()
    if is_encdec or model_type in ENCDEC_FAMILIES:
        # 只有分類任務除外（少數 enc-dec 也能分類，但你這裡主要載生成/翻譯）
        if kind not in ("seqcls", "tokcls"):
            kind = "seq2seq"
    return kind

def load_model(model_id: str, task_override: Optional[str] = None) -> Tuple[Optional[object], Optional[object]]:
    """
    - model_id: HF repo_id 字串（注意：不要傳 dict/tuple）
    - task_override: 若你已知外層任務（如 'summarization'），可明確指定；否則用 HF 標籤 + cfg 判斷
    回傳: (model, tokenizer) 或 (None, None)
    """
    if not isinstance(model_id, str):
        print("❗ Transformers 載入失敗：model_id 不是字串（請確認 UI 傳入的是 repo_id 字串）")
        return None, None

    api = HfApi()
    try:
        info = api.model_info(model_id, token=HF_TOKEN)
    except Exception as e:
        print(f"❗ 讀取模型資訊失敗：{e}")
        return None, None

    # 讀 tokenizer & config（優先用 fast；允許 remote code）
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN, use_fast=True, trust_remote_code=True)
    except Exception as e:
        print(f"⚠️ Tokenizer 載入警告：{e}，改用非 fast 嘗試")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN, use_fast=False, trust_remote_code=True)
        except Exception as e2:
            print(f"❗ Tokenizer 載入失敗：{e2}")
            tokenizer = None  # 某些任務（feature-extraction）可容忍無 tokenizer

    try:
        cfg = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
    except Exception as e:
        print(f"❗ 讀取 AutoConfig 失敗：{e}")
        return None, None

    # 先決定要用哪種 Loader
    pipe_tag = (task_override or info.pipeline_tag or "").strip()
    loader_kind = _pick_loader_kind(pipe_tag, cfg)

    try:
        if loader_kind == "seq2seq":
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)
        elif loader_kind == "seqcls":
            model = AutoModelForSequenceClassification.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)
        elif loader_kind == "tokcls":
            model = AutoModelForTokenClassification.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)
        elif loader_kind == "auto":
            model = AutoModel.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)
        else:
            # 'causal'
            # 若不小心遇到 enc-dec 仍走到這裡，再兜底一次
            if getattr(cfg, "is_encoder_decoder", False):
                model = AutoModelForSeq2SeqLM.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)
            else:
                model = AutoModelForCausalLM.from_pretrained(model_id, token=HF_TOKEN, trust_remote_code=True)

        model.eval()
        return model, tokenizer

    except Exception as e:
        msg = str(e)
        if "T5Config" in msg or "is_encoder_decoder" in msg or "BART" in msg:
            msg += "\n💡 提示：這是 encoder–decoder 模型，請用 AutoModelForSeq2SeqLM 載入。"
        print(f"❗ Transformers 載入失敗：{msg}")
        return None, None


# def load_model(model_id):
#     api = HfApi()
#     info = api.model_info(model_id, token=HF_TOKEN)

#     try:
#         tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN)

#         task = info.pipeline_tag or ""
#         if task == "text-generation":
#             model = AutoModelForCausalLM.from_pretrained(model_id, token=HF_TOKEN)
#         elif task == "text-classification":
#             model = AutoModelForSequenceClassification.from_pretrained(model_id, token=HF_TOKEN)
#         elif task == "token-classification":
#             model = AutoModelForTokenClassification.from_pretrained(model_id, token=HF_TOKEN)
#         elif task in ("translation", "summarization"):
#             model = AutoModelForSeq2SeqLM.from_pretrained(model_id, token=HF_TOKEN)
#         else:
#             print(f"⚠️ 不支援的 pipeline_tag：{task}，請選擇其他模型")
#             return None, None

#         return model, tokenizer

#     except Exception as e:
#         print(f"❗ Transformers 載入失敗：{e}")
#         return None, None

# --- 下面是新增的工具 ---

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

def load_model_by_task(model_id: str, task: str, **kwargs) -> Any:
    adapter = get_adapter(task)
    if adapter is None:
        raise ValueError(f"No adapter for task: {task}")
    adapter.prepare(model_id, task=task, **kwargs)
    return adapter.load(model_id, **kwargs)