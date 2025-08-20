from ollama_function import classify_prompt as _classify, translate_to_english as _translate ,extract_hf_keywords as _extract

def classify_prompt(text: str) -> str:
    return _classify(text)

def translate_to_english(text: str) -> str:
    return _translate(text)

def extract_hf_keywords(text: str) -> list[str]:
    return _extract(text)