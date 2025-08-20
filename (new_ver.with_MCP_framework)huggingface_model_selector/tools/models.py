from typing import Dict, Any
from huggingface_hub import HfApi
from configs.config import HF_TOKEN
from model_loader import load_model as _load_tf_model

def _has_gguf(model_id: str) -> bool:
    api = HfApi()
    info = api.model_info(model_id, token=HF_TOKEN)
    return any((s.rfilename or "").endswith(".gguf") for s in (info.siblings or []))

def load_or_route_model(model_id: str) -> Dict[str, Any]:
    # 若倉庫有 .gguf 檔，提示以 Ollama 執行（先不自動 create）
    try:
        if _has_gguf(model_id):
            return {
                "ok": True,
                "engine": "ollama",
                "message": f"GGUF 模型偵測到：{model_id}，請以 Ollama 執行或建立 Modelfile。"
            }
    except Exception as e:
        # 檢測失敗也仍嘗試 transformers 載入
        pass

    try:
        model, tok = _load_tf_model(model_id)
        if model is None:
            return {"ok": False, "message": f"Transformers 載入失敗：{model_id}"}
        return {
            "ok": True,
            "engine": "transformers",
            "message": f"Transformers 模型 {model_id} 載入完成"
        }
    except Exception as e:
        return {"ok": False, "message": f"載入異常：{e}"}
