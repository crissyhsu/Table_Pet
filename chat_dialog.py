"""
對話視窗模塊
處理用戶與桌寵的對話介面
"""

from typing import Optional, Callable
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ChatDialog(QDialog):
    """對話視窗"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("與桌寵對話")
        self.setFixedSize(600, 500)  # 增大視窗大小
        
        # 回調函數
        self.on_send_message: Optional[Callable[[str], None]] = None
        self.on_show_memories: Optional[Callable[[], None]] = None
        self.on_show_stats: Optional[Callable[[], None]] = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置使用者介面"""
        layout = QVBoxLayout()
        
        # 對話記錄顯示區
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        
        # 設置更大的字體
        font = QFont("Microsoft YaHei", 14)  # 增大字體到14pt
        self.chat_display.setFont(font)
        
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # 記憶管理按鈕區
        memory_layout = QHBoxLayout()
        
        self.show_memories_btn = QPushButton("📋 查看記憶")
        self.show_memories_btn.clicked.connect(self._on_show_memories)
        self.show_memories_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        
        self.memory_stats_btn = QPushButton("📊 記憶統計")
        self.memory_stats_btn.clicked.connect(self._on_show_stats)
        self.memory_stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #fd7e14;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8590c;
            }
        """)
        
        memory_layout.addWidget(self.show_memories_btn)
        memory_layout.addWidget(self.memory_stats_btn)
        memory_layout.addStretch()
        
        layout.addLayout(memory_layout)
        
        # 輸入區
        input_layout = QHBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(80)  # 稍微增加高度
        self.input_text.setPlaceholderText("輸入你想對桌寵說的話...")
        
        # 設置輸入框字體
        input_font = QFont("Microsoft YaHei", 13)  # 輸入框字體稍小一點
        self.input_text.setFont(input_font)
        
        self.input_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #86b7fe;
                box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
            }
        """)
        
        self.send_button = QPushButton("發送")
        self.send_button.clicked.connect(self._on_send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #157347;
            }
            QPushButton:pressed {
                background-color: #146c43;
            }
        """)
        
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # 使用說明
        help_text = QTextEdit()
        help_text.setMaximumHeight(60)
        help_text.setReadOnly(True)
        help_text.setText("💡 小提示：可以說「記住我叫小明」來儲存資訊，或問「我叫什麼名字？」來測試記憶功能")
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #e7f3ff;
                border: 1px solid #b3d9ff;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
                color: #0066cc;
            }
        """)
        layout.addWidget(help_text)
        
        self.setLayout(layout)
        
        # 讓 Ctrl+Enter 也能發送訊息
        self.input_text.keyPressEvent = self.handle_key_press
    
    def handle_key_press(self, event):
        """處理按鍵事件"""
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self._on_send_message()
        elif event.key() == Qt.Key_Return and not event.modifiers():
            # 普通Enter換行
            QTextEdit.keyPressEvent(self.input_text, event)
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
    
    def set_callbacks(self, on_send_message=None, on_show_memories=None, on_show_stats=None):
        """設置回調函數"""
        if on_send_message:
            self.on_send_message = on_send_message
        if on_show_memories:
            self.on_show_memories = on_show_memories
        if on_show_stats:
            self.on_show_stats = on_show_stats
    
    def _on_send_message(self):
        """處理發送訊息"""
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
        
        # 顯示用戶訊息
        self.add_user_message(user_input)
        self.add_system_message("思考中...")
        self.input_text.clear()
        
        # 調用回調函數
        if self.on_send_message:
            self.on_send_message(user_input)
    
    def _on_show_memories(self):
        """顯示記憶"""
        if self.on_show_memories:
            self.on_show_memories()
    
    def _on_show_stats(self):
        """顯示記憶統計"""
        if self.on_show_stats:
            self.on_show_stats()
    
    def add_user_message(self, message: str):
        """添加用戶訊息到對話記錄"""
        self.chat_display.append(f"<div style='color: #0066cc; font-weight: bold; margin: 8px 0 4px 0;'>🧑 你:</div>")
        self.chat_display.append(f"<div style='background-color: #e3f2fd; padding: 8px; border-radius: 6px; margin: 0 0 12px 0;'>{message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def add_pet_message(self, message: str):
        """添加桌寵回應到對話記錄"""
        self.chat_display.append(f"<div style='color: #d81b60; font-weight: bold; margin: 8px 0 4px 0;'>🐾 桌寵:</div>")
        self.chat_display.append(f"<div style='background-color: #fce4ec; padding: 8px; border-radius: 6px; margin: 0 0 12px 0;'>{message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def add_system_message(self, message: str):
        """添加系統訊息到對話記錄"""
        self.chat_display.append(f"<div style='color: #666666; font-style: italic; font-size: 12px; margin: 4px 0;'>💭 {message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def update_last_pet_message(self, message: str):
        """更新最後一條桌寵訊息（替換"思考中..."）"""
        # 取得當前內容
        current_html = self.chat_display.toHtml()
        
        # 找到最後一個"思考中..."並替換為實際回應
        if "思考中..." in current_html:
            # 移除最後的"思考中..."訊息
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            
            # 查找並移除最後的"思考中..."
            content = self.chat_display.toPlainText()
            lines = content.split('\n')
            
            # 重建內容但排除最後的"思考中..."
            new_lines = []
            skip_next = False
            for i, line in enumerate(lines):
                if "思考中..." in line:
                    skip_next = True
                    continue
                if not skip_next:
                    new_lines.append(line)
                else:
                    skip_next = False
            
            # 清空並重新設置內容
            self.chat_display.clear()
            
            # 重新添加所有內容
            for line in new_lines:
                if line.startswith("😺 你:") or line.startswith("你:"):
                    continue  # 跳過，因為會在下面重新格式化
                elif line.strip():
                    self.chat_display.append(line)
        
        # 添加桌寵回應
        self.add_pet_message(message)
    
    def show_error(self, error_message: str):
        """顯示錯誤訊息"""
        self.add_system_message(f"❌ 錯誤: {error_message}")
        if self.on_show_memories:
            self.on_show_memories()
    
    def _on_show_stats(self):
        """顯示記憶統計"""
        if self.on_show_stats:
            self.on_show_stats()
    
    def add_user_message(self, message: str):
        """添加用戶訊息到對話記錄"""
        self.chat_display.append(f"<div style='color: #0066cc; font-weight: bold; margin: 8px 0 4px 0;'>🧑 你:</div>")
        self.chat_display.append(f"<div style='background-color: #e3f2fd; padding: 8px; border-radius: 6px; margin: 0 0 12px 0;'>{message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def add_pet_message(self, message: str):
        """添加桌寵回應到對話記錄"""
        self.chat_display.append(f"<div style='color: #d81b60; font-weight: bold; margin: 8px 0 4px 0;'>🐾 桌寵:</div>")
        self.chat_display.append(f"<div style='background-color: #fce4ec; padding: 8px; border-radius: 6px; margin: 0 0 12px 0;'>{message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def add_system_message(self, message: str):
        """添加系統訊息到對話記錄"""
        self.chat_display.append(f"<div style='color: #666666; font-style: italic; font-size: 12px; margin: 4px 0;'>💭 {message}</div>")
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
    
    def update_last_pet_message(self, message: str):
        """更新最後一條桌寵訊息（替換"思考中..."）"""
        # 取得當前內容
        current_html = self.chat_display.toHtml()
        
        # 找到最後一個"思考中..."並替換為實際回應
        if "思考中..." in current_html:
            # 移除最後的"思考中..."訊息
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            
            # 查找並移除最後的"思考中..."
            content = self.chat_display.toPlainText()
            lines = content.split('\n')
            
            # 重建內容但排除最後的"思考中..."
            new_lines = []
            skip_next = False
            for i, line in enumerate(lines):
                if "思考中..." in line:
                    skip_next = True
                    continue
                if not skip_next:
                    new_lines.append(line)
                else:
                    skip_next = False
            
            # 清空並重新設置內容
            self.chat_display.clear()
            
            # 重新添加所有內容
            for line in new_lines:
                if line.startswith("🧑 你:") or line.startswith("你:"):
                    continue  # 跳過，因為會在下面重新格式化
                elif line.strip():
                    self.chat_display.append(line)
        
        # 添加桌寵回應
        self.add_pet_message(message)
    
    def show_error(self, error_message: str):
        """顯示錯誤訊息"""
        self.add_system_message(f"❌ 錯誤: {error_message}")


class QuickChatDialog:
    """快速對話對話框 - 靜態方法實現"""
    
    @staticmethod
    def get_user_input(parent=None) -> str:
        """獲取用戶快速輸入"""
        text, ok = QInputDialog.getText(
            parent, 
            "快速對話", 
            "對桌寵說點什麼吧：",
            text=""
        )
        
        if ok and text.strip():
            return text.strip()
        return ""
    
    @staticmethod
    def show_response(parent, title: str, message: str):
        """顯示快速回應"""
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 設置樣式讓文字可以自動換行
        msg_box.setStyleSheet("""
            QMessageBox {
                font-size: 13px;
            }
            QLabel {
                min-width: 400px;
                max-width: 600px;
                qproperty-wordWrap: true;
            }
        """)
        
        msg_box.exec_()