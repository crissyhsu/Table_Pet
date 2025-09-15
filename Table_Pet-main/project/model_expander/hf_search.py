import requests
from huggingface_hub import hf_hub_url, list_models
from huggingface_hub import HfApi, ModelInfo
from huggingface_hub.utils import HfHubHTTPError
from typing import List, Dict, Optional, Callable
import time, random  # 新增

def human_readable_size(size_bytes: int) -> str:
    if size_bytes >= 1024**3:            # 超過 1 GiB
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes >= 1024**2:          # 超過 1 MiB
        return f"{size_bytes / (1024**2):.2f} MB"
    elif size_bytes >= 1024:             # 超過 1 KiB
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes > 0:
        return f"{size_bytes} B"
    else:
        return "Unknown"

# 允許呼叫：search_models(task="image-to-text") 或 search_models(modality="image")
def search_models_simple(task: Optional[str] = None, modality: Optional[str] = None, query: Optional[str] = None, limit: int = 20) -> List[Dict]:
    filters = {}
    if task:
        filters["pipeline_tag"] = task
    # modality 可映射為 pipeline_tag 的集合（若未提供 task）
    if modality and not task:
        modality_to_tasks = {
            "text": ["text-generation","text2text-generation","summarization","translation","question-answering"],
            "image": ["image-classification","object-detection","image-segmentation","image-to-text","text-to-image"],
            "audio": ["automatic-speech-recognition","text-to-speech"],
            "video": ["video-classification"],
            "multi": ["visual-question-answering","any-to-any"],
        }
        # 粗略抓一種常見任務作為搜尋條件（或改為多次查詢合併）
        tasks = modality_to_tasks.get(modality, [])
        if tasks:
            filters["pipeline_tag"] = tasks[0]

    models = list_models(
        search=query or "",
        filter=filters or None,
        sort="downloads",
        direction=-1,
        limit=limit
    )
    out = []
    for m in models:
        card = m.__dict__  # 取需要欄位
        out.append({
            "modelId": card.get("modelId"),
            "pipeline_tag": card.get("pipeline_tag"),
            "downloads": card.get("downloads"),
            "likes": card.get("likes"),
        })
    return out

    """
    使用 Hugging Face API 搜尋符合任務的模型，並擷取模型大小資訊

    Args:
        task_keywords (str): 預測出的 pipeline_tag 任務類別
        user_prompt: 使用者原始輸入的模型要求
        limit (int): 回傳模型數量上限
        token (str or None): 存取私有模型的 token

    Returns:
        List[Dict]: 模型資訊字典清單（含大小）
    """

    api = HfApi()

    def _list(t):  # 小幫手
        return api.list_models(
            pipeline_tag = task_keywords,
            search = user_prompt,
            sort = "downloads",
            direction = -1,
            limit = limit,
            full = True,
            cardData = True,
            token = t
        )

    try:
        models = list(_list(token))
    except HfHubHTTPError as e:
        if "401" in str(e):
            models = list(_list(None))  # 壞 token → 匿名再試公開模型
        else:
            raise
    # models: List[ModelInfo] = api.list_models(
    #     pipeline_tag = task_keywords,
    #     search = user_prompt,
    #     sort = "downloads",
    #     direction = -1,
    #     limit = limit,
    #     full = True,
    #     cardData = True,
    #     token = token
    # )

    models_info = []

    for m in models:
        size_bytes = 0
        # 只 sum 欲顯示的檔案類型
        exts = (".bin", ".safetensors", ".onnx", ".msgpack")
        for f in (m.siblings or []):
            if any(f.rfilename.endswith(ext) for ext in exts):
                # 建立 raw 檔案 URL
                url = hf_hub_url(repo_id=m.modelId, filename=f.rfilename)
                try:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    resp = requests.head(url, allow_redirects=True, timeout=8, headers=headers)
                    size = int(resp.headers.get("content-length", 0))
                except Exception:
                    size = 0
                size_bytes += size

        size_str = human_readable_size(size_bytes)

        models_info.append({
            "id": m.modelId,
            "tags": m.tags,
            "downloads": m.downloads,
            "likes": m.likes,
            "lastModified": m.lastModified,
            "task": m.pipeline_tag,
            "private": m.private,
            "size_mb": size_str       #  加入模型大小
        })

    print(f"✅ 找到 {len(models_info)} 筆模型")

    return models_info

def search_models_with_retry(
    task_keywords: str,
    user_prompt: str,
    limit: int = 10,
    max_retries: int = 10,
    base_delay: float = 0.5,   # 秒
    token: Optional[str] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,  # (attempt, max_retries)
) -> List[Dict]:
    """
    失敗會重試到 max_retries 次；只要某次回傳非空結果立刻返回。
    若全數失敗，回傳空清單（你也可以選擇 raise 最後一次錯誤）。
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        if on_progress:
            on_progress(attempt, max_retries)
        try:
            results = search_models(  # ← 直接用同檔的一次查詢函式
                task_keywords=task_keywords,
                user_prompt=user_prompt,
                limit=limit,
                token=token
            )
            if results:   # 只要有結果就提前返回
                return results
        except Exception as e:
            last_err = e
        # 指數退避 + 抖動
        sleep_time = base_delay * (2 ** (attempt - 1)) + random.random() * 0.2
        time.sleep(min(sleep_time, 5.0))
    # 全部都沒查到
    # return []                      # 若想用空清單表示失敗就用這行
    if last_err:
        raise last_err
    return []

def search_models(
    task_keywords: str,
    user_prompt: str,
    limit: int = 10,
    token: Optional[str] = None,
) -> List[Dict]:
    api = HfApi()
    def _list(t):
        return api.list_models(
            pipeline_tag=task_keywords,
            search=user_prompt,
            sort="downloads",
            direction=-1,
            limit=limit,
            full=True,
            cardData=True,
            token=t
        )
    try:
        models = list(_list(token))
    except HfHubHTTPError as e:
        if "401" in str(e):
            models = list(_list(None))
        else:
            raise

    models_info = []
    exts = (".bin", ".safetensors", ".onnx", ".msgpack")
    for m in models:
        size_bytes = 0
        for f in (m.siblings or []):
            if any(f.rfilename.endswith(ext) for ext in exts):
                url = hf_hub_url(repo_id=m.modelId, filename=f.rfilename)
                try:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    resp = requests.head(url, allow_redirects=True, timeout=8, headers=headers)
                    size = int(resp.headers.get("content-length", 0))
                except Exception:
                    size = 0
                size_bytes += size
        size_str = human_readable_size(size_bytes)
        models_info.append({
            "id": m.modelId,
            "tags": m.tags,
            "downloads": m.downloads,
            "likes": m.likes,
            "lastModified": m.lastModified,
            "task": m.pipeline_tag,
            "private": m.private,
            "size_mb": size_str
        })
    return models_info
