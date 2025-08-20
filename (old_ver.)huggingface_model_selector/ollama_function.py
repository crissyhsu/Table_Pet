import ollama
import subprocess

def classify_prompt(prompt_text, max_retries=10):
    task_labels = [
        # Multimodal
        "Audio-Text-to-Text",
        "Image-Text-to-Text",
        "Visual Question Answering",
        "Document Question Answering",
        "Video-Text-to-Text",
        "Visual Document Retrieval",
        "Any-to-Any",
        # Computer Vision
        "Depth Estimation",
        "Image Classification",
        "Object Detection",
        "Image Segmentation",
        "Text-to-Image",
        "Image-to-Text",
        "Image-to-Image",
        "Image-to-Video",
        "Unconditional Image Generation",
        "Video Classification",
        "Text-to-Video",
        "Zero-Shot Image Classification",
        "Mask Generation",
        "Zero-Shot Object Detection",
        "Text-to-3D",
        "Image-to-3D",
        "Image Feature Extraction",
        "Keypoint Detection",
        "Video-to-Video",
        # Natural Language Processing
        "Text Classification",
        "Token Classification",
        "Table Question Answering",
        "Question Answering",
        "Zero-Shot Classification",
        "Translation",
        "Summarization",
        "Feature Extraction",
        "Text Generation",
        "Fill-Mask",
        "Sentence Similarity",
        "Text Ranking",
        # Audio
        "Text-to-Speech",
        "Text-to-Audio",
        "Automatic Speech Recognition",
        "Audio-to-Audio",
        "Audio Classification",
        "Voice Activity Detection",
        # Tabular
        "Tabular Classification",
        "Tabular Regression",
        "Time Series Forecasting",
        # Reinforcement Learning
        "Reinforcement Learning",
        "Robotics",
        # Other
        "Graph Machine Learning"
    ]

    labels_text = "\n".join(f"* {label}" for label in task_labels)

    system_instruction = f"""
        請判斷使用者描述屬於以下哪一個 Hugging Face 任務類別，
        請直接回傳以下其中一個標籤，不要加任何說明或標點。
        {labels_text}
        """
    full_prompt = f"{system_instruction.strip()}\n\n輸入如下：{prompt_text.strip()}"

    for attempt in range(max_retries):
        result = subprocess.run(
            ["ollama", "run", "phi4-mini:3.8b", full_prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            universal_newlines=True
        )

        print(f"=== DEBUG [Attempt {attempt+1}] stdout ===")
        print(repr(result.stdout))

        prediction = result.stdout.strip()

        if prediction in task_labels:
            prediction = prediction.lower().replace(" ", "-")  # → "text-classification"
            return prediction
        else:
            print(f"⚠️ 無效預測：{prediction}，重試中...")

    return prediction

def translate_to_english(text: str, model: str = "phi4-mini:3.8b", max_retries: int = 5) -> str:
    """
    使用 Ollama CLI 呼叫本地 LLM，將輸入文字翻譯成英文。

    參數:
        text: 要翻譯的原始文字 (任意語言)
        model: Ollama 上可用的本地模型名稱（預設 phi4-mini:3.8b）
        max_retries: 最多重試次數，遇到空結果時會重試

    回傳:
        翻譯後的英文文字（不含多餘說明）
    """
    # 系統指令，明確告訴模型只輸出翻譯內容
    system_instruction = """
    請將以下文字翻譯成英文，不要添加任何多餘文字或說明，僅輸出純英文翻譯：
    """
    full_prompt = system_instruction.strip() + "\n\n" + text.strip()

    translation = ""
    for attempt in range(1, max_retries + 1):
        result = subprocess.run(
            ["ollama", "run", model, full_prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            universal_newlines=True
        )
        translation = result.stdout.strip()
        if translation:
            return translation
        else:
            print(f"⚠️ 嘗試第 {attempt} 次，未產生翻譯結果，重試中…")

    # 最後一次嘗試後仍無結果就直接回傳空字串或上一次輸出
    return translation