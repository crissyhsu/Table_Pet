import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")  # 直接填 OpenRouter 的 key
url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://example.com",  # 沒有網站可以隨便填
    "X-Title": "Table Pet Test",
    "Content-Type": "application/json"
}

data = {
    "model": "z-ai/glm-4.5-air:free",
    "messages": [
        {"role": "user", "content": "早安"}
    ]
}

resp = requests.post(url, headers=headers, json=data)
#print(resp.status_code)
#print(resp.text)


print(resp.json()["choices"][0]["message"]["content"])
