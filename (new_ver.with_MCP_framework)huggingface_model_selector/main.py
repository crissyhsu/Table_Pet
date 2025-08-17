# main.py
from core.router import Router

def main():
    r = Router()
    print("🧠 MCP Router Demo：輸入自然語句會做『分類→翻譯→搜尋』；\n   輸入『下載：<model_id>』或『執行：<model_id>』會直接載入模型。")
    while True:
        try:
            text = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            break
        if not text.strip():
            continue

        out = r.handle(text)
        t = out.get("type")
        if t == "error":
            print(f"[ERROR] {out['message']}")
        elif t == "search_results":
            print(f"[SEARCH] task={out['task']}  keywords='{out['keywords']}'  搜尋到{out['count']}筆資料")
            for i, it in enumerate(out["items"][:10]):
                print(f"  [{i}] {it['id']} | 模型大小大約是{it.get('size_mb')} | 👍：{it.get('likes')} ⬇️：{it.get('downloads')}")
        elif t == "execute":
            print(f"[EXEC] engine={out['engine']} {out['message']}")

if __name__ == "__main__":
    main()