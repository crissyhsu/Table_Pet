from typing import List, Dict, Optional
from hf_search import search_models

def hf_search_models(task: str, query_en: str, token: Optional[str]) -> List[Dict]:
    return search_models(task_keywords=task, user_prompt=query_en, token=token)

def hf_search_try_many(tasks: List[str], queries: List[str], token: Optional[str]) -> List[Dict]:
    seen_ids = set()
    results: List[Dict] = []
    for t in tasks:
        for q in queries:
            rows = search_models(task_keywords=t, user_prompt=q, token=token)
            rows = [r for r in rows if r.get("id") not in seen_ids]
            for r in rows:
                seen_ids.add(r.get("id"))
            if rows:
                results.extend(rows)
                return results
    return results
