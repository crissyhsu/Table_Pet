# app/model_expander/expander_registry.py
import json, os, re
from pathlib import Path
from typing import Dict, List, Optional

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
