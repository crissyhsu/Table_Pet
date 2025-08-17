import re
from typing import Any, Dict, List, Optional

from configs.config import HF_TOKEN
from tools.ollama_tool import classify_prompt, translate_to_english, extract_hf_keywords
from tools.hf import hf_search_models, hf_search_try_many
from tools.models import load_or_route_model

# 支援「下載：<model_id>」或「執行：<model_id>」的快捷命令
DOWNLOAD_CMD = re.compile(r"^(下載|執行)\s*[:：]\s*(\S+)$", re.IGNORECASE)

class Router:
    def handle(self, user_text: str) -> Dict[str, Any]:
        """
        入口：如果是下載指令→直接載入；否則走「分類→翻譯→HF搜尋」。
        回傳結構：
          - 搜尋: {"type":"search_results","task":..., "query_en":..., "count":..., "items":[...]}
          - 載入: {"type":"execute","engine":"transformers"|"ollama","message":...}
          - 錯誤: {"type":"error","message":...}
        """
        # 1) 直接下載指令
        m = DOWNLOAD_CMD.match(user_text.strip())
        if m:
            return self._execute_model(m.group(2))

        # 2) NLU：任務分類 + 英譯 + 關鍵詞
        task = classify_prompt(user_text) or "unknown"
        if task == "unknown":
            return {"type": "error", "message": f"無法判斷任務類型：{user_text}"}

        query_en = translate_to_english(user_text)
        keywords = extract_hf_keywords(query_en)

        # 4) 依序嘗試同一任務（如 text-generation），若為 0 → 試「備援任務」
        #    很多「新聞標題/生成」其實常掛在 summarization 或 translation 相關
        fallback_tasks = [task]
        if task != "summarization":
            fallback_tasks.append("summarization")
        if task != "text-generation":
            fallback_tasks.append("text-generation")

        items = hf_search_try_many(
            tasks=fallback_tasks,
            queries=keywords,
            token=HF_TOKEN
        )

        return {
            "type": "search_results",
            "task": task,
            "keywords":keywords,
            "query_en": query_en,
            "count": len(items or []),
            "items": items or [],
        }

    def _execute_model(self, model_id: str) -> Dict[str, Any]:
        res = load_or_route_model(model_id)
        if not res.get("ok"):
            return {"type": "error", "message": res.get("message", "載入失敗")}
        return {"type": "execute", "engine": res.get("engine"), "message": res["message"]}
