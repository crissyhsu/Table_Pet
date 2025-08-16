import sys
import os
import requests
from dotenv import load_dotenv
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QMenu, QAction, 
                             QInputDialog, QMessageBox, QTextEdit, QVBoxLayout,
                             QHBoxLayout, QPushButton, QDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QCursor

# 載入環境變數
load_dotenv()

class LLMThread(QThread):
    """處理LLM API請求的執行緒"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, user_input):
        super().__init__()
        self.user_input = user_input
        
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
            
            data = {
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {"role": "user", "content": self.user_input}
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

class ChatDialog(QDialog):
    """對話視窗"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("與桌寵對話")
        self.setFixedSize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 對話記錄顯示區
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # 輸入區
        input_layout = QHBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(60)
        self.input_text.setPlaceholderText("輸入你想對桌寵說的話...")
        
        self.send_button = QPushButton("發送")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # 讓 Enter 也能發送訊息
        self.input_text.keyPressEvent = self.handle_key_press
        
    def handle_key_press(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.send_message()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
            
    def send_message(self):
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
            
        # 顯示用戶訊息
        self.chat_display.append(f"<b>你:</b> {user_input}")
        self.chat_display.append("<b>桌寵:</b> 思考中...")
        self.input_text.clear()
        
        # 發送到LLM
        if hasattr(self.parent(), 'send_to_llm'):
            self.parent().send_to_llm(user_input)

class DesktopPet(QWidget):
    def __init__(self, image_paths, move_speed=8):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 載入圖片
        self.frames = [QPixmap(img_path) for img_path in image_paths]
        self.frame_index = 0
        
        # 顯示圖片的 QLabel
        self.label = QLabel(self)
        self.label.setPixmap(self.frames[self.frame_index])
        self.resize(self.frames[0].size())
        
        # 計時器：更新動畫和移動
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pet)
        self.timer.start(100)  # 100ms 更新一次
        
        # 初始位置（靠右下）
        screen = QApplication.primaryScreen().geometry()
        self.x = screen.width()
        self.y = screen.height() - self.height()
        self.move(self.x, self.y)
        
        self.move_speed = move_speed
        
        # 對話視窗
        self.chat_dialog = None
        self.llm_thread = None
        
        # 設置右鍵選單
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)
        
        # 對話選項
        chat_action = QAction("💬 與桌寵對話", self)
        chat_action.triggered.connect(self.open_chat_dialog)
        context_menu.addAction(chat_action)
        
        # 快速對話選項
        quick_chat_action = QAction("⚡ 快速對話", self)
        quick_chat_action.triggered.connect(self.quick_chat)
        context_menu.addAction(quick_chat_action)
        
        context_menu.addSeparator()
        
        # 退出選項
        exit_action = QAction("❌ 退出", self)
        exit_action.triggered.connect(self.close_application)
        context_menu.addAction(exit_action)
        
        # 在滑鼠位置顯示選單
        context_menu.exec_(self.mapToGlobal(position))
        
    def open_chat_dialog(self):
        """開啟對話視窗"""
        if self.chat_dialog is None:
            self.chat_dialog = ChatDialog(self)
            
        self.chat_dialog.show()
        self.chat_dialog.raise_()
        self.chat_dialog.activateWindow()
        
    def quick_chat(self):
        """快速對話"""
        text, ok = QInputDialog.getText(self, '快速對話', '你想對桌寵說什麼？')
        if ok and text.strip():
            self.send_to_llm(text.strip())
            
    def send_to_llm(self, user_input):
        """發送訊息給LLM"""
        if self.llm_thread and self.llm_thread.isRunning():
            QMessageBox.information(self, "提示", "桌寵還在思考中，請稍等...")
            return
            
        self.llm_thread = LLMThread(user_input)
        self.llm_thread.response_received.connect(self.handle_llm_response)
        self.llm_thread.error_occurred.connect(self.handle_llm_error)
        self.llm_thread.start()
        
    def handle_llm_response(self, response):
        """處理LLM回應"""
        # 如果對話視窗開著，更新對話記錄
        if self.chat_dialog and self.chat_dialog.isVisible():
            # 移除 "思考中..." 的最後一行
            cursor = self.chat_dialog.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # 刪除換行符
            
            # 添加實際回應
            self.chat_dialog.chat_display.append(f"<b>桌寵:</b> {response}")
            self.chat_dialog.chat_display.append("")  # 空行分隔
        else:
            # 如果沒有對話視窗，用訊息框顯示
            msg = QMessageBox(self)
            msg.setWindowTitle("桌寵的回應")
            msg.setText(response)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
    def handle_llm_error(self, error_message):
        """處理LLM錯誤"""
        QMessageBox.critical(self, "錯誤", f"無法連接到LLM服務：\n{error_message}")
        
        # 如果對話視窗開著，也要更新
        if self.chat_dialog and self.chat_dialog.isVisible():
            cursor = self.chat_dialog.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            
            self.chat_dialog.chat_display.append(f"<b>桌寵:</b> <span style='color: red;'>抱歉，我現在無法回應 ({error_message})</span>")
            self.chat_dialog.chat_display.append("")
            
    def close_application(self):
        """關閉應用程式"""
        if self.chat_dialog:
            self.chat_dialog.close()
        QApplication.quit()
        
    def update_pet(self):
        """更新桌寵動畫和位置"""
        # 換下一張圖
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.label.setPixmap(self.frames[self.frame_index])
        
        # 向左移動
        self.x -= self.move_speed
        if self.x < -self.width():  # 出畫面就從右邊出現
            screen = QApplication.primaryScreen().geometry()
            self.x = screen.width()
        self.move(self.x, self.y)
        
    def mousePressEvent(self, event):
        """處理滑鼠點擊事件"""
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 載入圖片清單
    folder = "Walk"
    if not os.path.exists(folder):
        QMessageBox.critical(None, "錯誤", f"找不到圖片資料夾 '{folder}'！\n請確保資料夾存在並包含PNG圖片檔案。")
        sys.exit(1)
        
    image_paths = [os.path.join(folder, img) for img in sorted(os.listdir(folder)) if img.endswith(".png")]
    
    if not image_paths:
        QMessageBox.critical(None, "錯誤", f"在 '{folder}' 資料夾中找不到PNG圖片！\n請放入一些桌寵圖片。")
        sys.exit(1)
    
    # 檢查環境變數
    load_dotenv()
    if not os.getenv("LLM_API_KEY"):
        QMessageBox.warning(None, "警告", "找不到 LLM_API_KEY 環境變數！\n請在 .env 檔案中設置你的API Key。\n桌寵仍可正常顯示，但無法與LLM對話。")
    
    pet = DesktopPet(image_paths)
    pet.show()
    
    sys.exit(app.exec_())