import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or None
