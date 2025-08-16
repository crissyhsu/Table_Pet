"""
LLM API 模塊
處理與語言模型的API通訊
"""

import os
import requests
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal


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


class LLMAPIManager:
    """LLM API管理器"""
    
    def __init__(self):
        self.current_thread = None
    
    def send_request(self, user_input: str, context: str = None, 
                    on_success=None, on_error=None) -> bool:
        """
        發送請求到LLM
        
        Args:
            user_input: 用戶原始輸入
            context: 包含記憶的完整上下文
            on_success: 成功回調函數
            on_error: 錯誤回調函數
            
        Returns:
            bool: 是否成功啟動請求
        """
        if self.current_thread and self.current_thread.isRunning():
            if on_error:
                on_error("API正在處理中，請稍候...")
            return False
        
        try:
            self.current_thread = LLMThread(user_input, context)
            
            if on_success:
                self.current_thread.response_received.connect(on_success)
            if on_error:
                self.current_thread.error_occurred.connect(on_error)
                
            self.current_thread.start()
            return True
            
        except Exception as e:
            if on_error:
                on_error(f"啟動API請求失敗: {str(e)}")
            return False
    
    def is_busy(self) -> bool:
        """檢查API是否忙碌中"""
        return self.current_thread and self.current_thread.isRunning()
    
    def stop_current_request(self):
        """停止當前請求（如果可能）"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
            self.current_thread.wait()


def check_api_key() -> bool:
    """檢查API Key是否設置"""
    return bool(os.getenv("LLM_API_KEY"))


def get_api_status() -> str:
    """獲取API狀態資訊"""
    if check_api_key():
        return "✅ API Key已設置"
    else:
        return "❌ 未設置API Key"