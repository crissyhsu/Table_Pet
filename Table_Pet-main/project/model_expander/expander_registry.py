# app/model_expander/expander_registry.py
import json, os, re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Literal, Type

Modality = Literal["text", "image", "audio", "video", "multi"]

ROOT = Path(__file__).resolve().parents[1]  # 指到 app/
STORE_DIR = ROOT / "expanded_models"
REGISTRY = STORE_DIR / "registry.json"

def _ensure_store():
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY.exists():
        REGISTRY.write_text("[]", encoding="utf-8")

def _load() -> List[Dict]:
    _ensure_store()
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save(items: List[Dict]):
    _ensure_store()
    REGISTRY.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def _safe_name(repo_id: str) -> str:
    # 路徑安全名字（huggingface repo 轉資料夾名）
    return re.sub(r"[^a-zA-Z0-9._-]+", "__", repo_id)

def models_dir() -> Path:
    _ensure_store()
    return STORE_DIR

def list_installed() -> List[Dict]:
    """
    回傳每個項目：
    {
      "repo_id": "org/name",
      "backend": "transformers" | "ollama",
      "task": "text-generation" | ... | "",
      "local_path": "app/expanded_models/org__name",
      "notes": ""
    }
    """
    return _load()

def register_model(repo_id: str, backend: str, task: str = "", local_path: Optional[str] = None, notes: str = ""):
    items = _load()
    # 去重（以 repo_id + backend 當 key）
    for it in items:
        if it.get("repo_id") == repo_id and it.get("backend") == backend:
            # 更新資訊
            if task: it["task"] = task
            if local_path: it["local_path"] = local_path
            if notes: it["notes"] = notes
            _save(items)
            return
    items.append({
        "repo_id": repo_id,
        "backend": backend,
        "task": task or "",
        "local_path": local_path or "",
        "notes": notes or ""
    })
    _save(items)

def remove_model(repo_id: str, backend: str) -> bool:
    items = _load()
    new_items = [it for it in items if not (it.get("repo_id")==repo_id and it.get("backend")==backend)]
    _save(new_items)
    return len(new_items) != len(items)

def suggested_local_dir(repo_id: str) -> str:
    return str(models_dir() / _safe_name(repo_id))


# 任務→模態的最小對映（後續可再擴充）
TASK_TO_MODALITY: Dict[str, Modality] = {
    # text
    "text-generation": "text",
    "text2text-generation": "text",
    "summarization": "text",
    "translation": "text",
    "question-answering": "text",
    # image
    "image-classification": "image",
    "object-detection": "image",
    "image-segmentation": "image",
    "image-to-text": "image",
    # audio
    "automatic-speech-recognition": "audio",
    "text-to-speech": "audio",
    # diffusion
    "text-to-image": "image",
    # multi
    "visual-question-answering": "multi",
    "any-to-any": "multi",
}

class Adapter(Protocol):
    """各模態/任務的統一介面"""
    def prepare(self, model_id: str, **kwargs) -> None: ...
    def load(self, model_id: str, **kwargs) -> Any: ...
    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]: ...

# ===== 基礎 Adapter 範例 =====
# Text: 直接用 transformers pipeline
class TextNLPAdapter:
    def __init__(self):
        self.pipeline = None
        self.task = None
        self.model_id = None

    def prepare(self, model_id: str, task: str, **kwargs):
        self.model_id = model_id
        self.task = task

    def load(self, model_id: str, **kwargs):
        from transformers import pipeline
        self.pipeline = pipeline(self.task, model=model_id, device_map="auto")
        return self.pipeline

    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        text = payload.get("text", "")
        out = self.pipeline(text, **kwargs)
        return {"text": out}

# Image→Text（圖像描述）: transformers image-to-text
class ImageToTextAdapter:
    def __init__(self):
        self.pipeline = None
        self.model_id = None

    def prepare(self, model_id: str, **kwargs):
        self.model_id = model_id

    def load(self, model_id: str, **kwargs):
        from transformers import pipeline
        self.pipeline = pipeline("image-to-text", model=model_id, device_map="auto")
        return self.pipeline

    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        image = payload.get("image")  # PIL, np array, or file path
        out = self.pipeline(image, **kwargs)
        return {"text": out}

# 文生圖：diffusers
class TextToImageAdapter:
    def __init__(self):
        self.pipe = None
        self.model_id = None

    def prepare(self, model_id: str, **kwargs):
        self.model_id = model_id

    def load(self, model_id: str, **kwargs):
        from diffusers import StableDiffusionPipeline
        import torch
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16 if torch.cuda.is_available() else None
        )
        if torch.cuda.is_available():
            self.pipe = self.pipe.to("cuda")
        return self.pipe

    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        prompt = payload.get("text", "")
        img = self.pipe(prompt, **kwargs).images[0]
        return {"image": img}

# ASR：語音轉文字
class ASRAdapter:
    def __init__(self):
        self.pipeline = None

    def prepare(self, model_id: str, **kwargs):
        self.model_id = model_id

    def load(self, model_id: str, **kwargs):
        from transformers import pipeline
        self.pipeline = pipeline("automatic-speech-recognition", model=model_id, device_map="auto")
        return self.pipeline

    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        audio = payload.get("audio")  # file path / array
        out = self.pipeline(audio, **kwargs)
        return {"text": out}

# TTS：文字轉語音（先留接口；實作可用 Coqui TTS 或 transformers 支援的 TTS）
class TTSAdapter:
    def __init__(self):
        self.impl = None
    def prepare(self, model_id: str, **kwargs):
        self.model_id = model_id
    def load(self, model_id: str, **kwargs):
        # TODO: integrate a TTS backend when you choose one
        self.impl = "placeholder"
        return self.impl
    def infer(self, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        text = payload.get("text", "")
        # return {"audio": <numpy array or file path>}
        return {"warning": "TTSAdapter not yet implemented"}

# ===== Adapter Registry =====
ADAPTERS_BY_TASK: Dict[str, Type[Adapter]] = {
    # text
    "text-generation": TextNLPAdapter,
    "text2text-generation": TextNLPAdapter,
    "summarization": TextNLPAdapter,
    "translation": TextNLPAdapter,
    "question-answering": TextNLPAdapter,
    # image
    "image-to-text": ImageToTextAdapter,
    # diffusion
    "text-to-image": TextToImageAdapter,
    # audio
    "automatic-speech-recognition": ASRAdapter,
    "text-to-speech": TTSAdapter,
    # multi（先導向 image-to-text / 通用處理器，之後可擴充）
    "visual-question-answering": ImageToTextAdapter,
    "any-to-any": TextNLPAdapter,
}

def get_modality(task: str) -> Optional[Modality]:
    return TASK_TO_MODALITY.get(task)

def get_adapter(task: str) -> Optional[Adapter]:
    cls = ADAPTERS_BY_TASK.get(task)
    return cls() if cls else None