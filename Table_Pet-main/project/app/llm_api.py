"""
LLM API 模塊
處理與語言模型的API通訊
"""

import os
import requests
from typing import Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal

# 新增的
from enum import Enum
from typing import Optional, Callable

class LLMThread(QThread):
    """處理LLM API請求的執行緒"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, user_input: str, context: Optional[str] = None):
        super().__init__()
        self.user_input = user_input
        self.context = context  # 包含記憶的完整上下文
        
    def run(self):
        try:
            API_KEY = os.getenv("LLM_API_KEY")
            if not API_KEY:
                self.error_occurred.emit("找不到 LLM_API_KEY，請檢查 .env 檔案")
                return
                
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://example.com",
                "X-Title": "Smart Desktop Pet",
                "Content-Type": "application/json"
            }
            
            # 使用完整上下文而不是原始用戶輸入
            message_content = self.context if self.context else self.user_input
            
            data = {
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {"role": "user", "content": message_content}
                ]
            }
            
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            
            if resp.status_code == 200:
                response_text = resp.json()["choices"][0]["message"]["content"]
                self.response_received.emit(response_text)
            else:
                self.error_occurred.emit(f"API錯誤: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            self.error_occurred.emit(f"發生錯誤: {str(e)}")

class Backend(Enum): # 新增的！！！！！！！！！！！
    OPENROUTER = "openrouter"
    TRANSFORMERS = "transformers"
    OLLAMA = "ollama"


class LLMAPIManager:
    """LLM API管理器"""
    
    def __init__(self):
        self.current_thread = None
        self.backend = Backend.OPENROUTER
        self._tf_model = None
        self._tf_tokenizer = None
        self._ollama_model_name = None
    
    # def send_request(self, user_input: str, context: str = None, 
    #                 on_success=None, on_error=None) -> bool:
    #     """
    #     發送請求到LLM
        
    #     Args:
    #         user_input: 用戶原始輸入
    #         context: 包含記憶的完整上下文
    #         on_success: 成功回調函數
    #         on_error: 錯誤回調函數
            
    #     Returns:
    #         bool: 是否成功啟動請求
    #     """
    #     if self.current_thread and self.current_thread.isRunning():
    #         if on_error:
    #             on_error("API正在處理中，請稍候...")
    #         return False
        
    #     try:
    #         self.current_thread = LLMThread(user_input, context)
            
    #         if on_success:
    #             self.current_thread.response_received.connect(on_success)
    #         if on_error:
    #             self.current_thread.error_occurred.connect(on_error)
                
    #         self.current_thread.start()
    #         return True
            
    #     except Exception as e:
    #         if on_error:
    #             on_error(f"啟動API請求失敗: {str(e)}")
    #         return False
    
    def send_request(self, user_input: str, context: str = None, 
                    on_success: Optional[Callable[[str], None]] = None,
                    on_error: Optional[Callable[[str], None]] = None) -> bool:
        """
        依後端執行推論：
          - OPENROUTER：沿用原 Thread（遠端 API）
          - TRANSFORMERS：本地推論（同步跑，回呼成功）
          - OLLAMA：用 subprocess/ollama 套件呼叫（同步跑，回呼成功）
        """
        if self.current_thread and self.current_thread.isRunning():
            if on_error:
                on_error("API正在處理中，請稍候...")
            return False

        try:
            if self.backend == Backend.OPENROUTER:
                # 舊邏輯（保留）：用 Thread 打 OpenRouter
                self.current_thread = LLMThread(user_input, context)
                if on_success:
                    self.current_thread.response_received.connect(on_success)
                if on_error:
                    self.current_thread.error_occurred.connect(on_error)
                self.current_thread.start()
                return True

            elif self.backend == Backend.TRANSFORMERS:
                if not (self._tf_model and self._tf_tokenizer):
                    if on_error: on_error("Transformers 後端尚未設定模型")
                    return False

                prompt = context if context else user_input
                # 簡單 text-generation 推論範例：
                from transformers import pipeline
                pipe = pipeline("text-generation", model=self._tf_model, tokenizer=self._tf_tokenizer)
                out = pipe(prompt, max_new_tokens=200, do_sample=True, temperature=0.8)
                text = out[0]["generated_text"]
                # 截掉 prompt 前綴，保留回覆（視模型而定）
                if on_success: on_success(text[len(prompt):].strip() if text.startswith(prompt) else text.strip())
                return True

            elif self.backend == Backend.OLLAMA:
                if not self._ollama_model_name:
                    if on_error: on_error("Ollama 模型未設定")
                    return False
                import subprocess
                prompt = context if context else user_input
                result = subprocess.run(
                    ["ollama", "run", self._ollama_model_name, prompt],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding="utf-8", universal_newlines=True
                )
                if result.returncode == 0:
                    if on_success: on_success(result.stdout.strip())
                else:
                    if on_error: on_error(result.stderr.strip() or "Ollama 執行失敗")
                return True

        except Exception as e:
            if on_error:
                on_error(f"啟動/執行請求失敗: {str(e)}")
            return False
    
    def is_busy(self) -> bool:
        """檢查API是否忙碌中"""
        return self.current_thread and self.current_thread.isRunning()
    
    def stop_current_request(self):
        """停止當前請求（如果可能）"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
            self.current_thread.wait()

    def set_backend_openrouter(self):
        self.backend = Backend.OPENROUTER
        self._tf_model = self._tf_tokenizer = None
        self._ollama_model_name = None

    def set_backend_transformers(self, model, tokenizer):
        self.backend = Backend.TRANSFORMERS
        self._tf_model = model
        self._tf_tokenizer = tokenizer
        self._ollama_model_name = None

    def set_backend_ollama(self, model_name: str):
        self.backend = Backend.OLLAMA
        self._ollama_model_name = model_name
        self._tf_model = self._tf_tokenizer = None


def check_api_key() -> bool:
    """檢查API Key是否設置"""
    return bool(os.getenv("LLM_API_KEY"))


def get_api_status() -> str:
    """獲取API狀態資訊"""
    if check_api_key():
        return "✅ API Key已設置"
    else:
        return "❌ 未設置API Key"



