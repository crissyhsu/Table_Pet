import sys
import os
import requests
from dotenv import load_dotenv
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QMenu, QAction, 
                             QInputDialog, QMessageBox, QTextEdit, QVBoxLayout,
                             QHBoxLayout, QPushButton, QDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QCursor

# 导入改进的记忆系统
from memory_system import SmartChatbotWithMemory

class LLMThread(QThread):
    """处理LLM API请求的执行绪"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, user_input, context=None):
        super().__init__()
        self.user_input = user_input
        self.context = context  # 新增：包含记忆的完整上下文
        
    def run(self):
        try:
            API_KEY = os.getenv("LLM_API_KEY")
            if not API_KEY:
                self.error_occurred.emit("找不到 LLM_API_KEY，请检查 .env 档案")
                return
                
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://example.com",
                "X-Title": "Smart Desktop Pet",
                "Content-Type": "application/json"
            }
            
            # 使用完整上下文而不是原始用户输入
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
                self.error_occurred.emit(f"API错误: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            self.error_occurred.emit(f"发生错误: {str(e)}")

class ChatDialog(QDialog):
    """对话视窗"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("与桌宠对话")
        self.setFixedSize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 对话记录显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 12px;
                font-family: 'Microsoft YaHei', sans-serif;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # 输入区
        input_layout = QHBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(60)
        self.input_text.setPlaceholderText("输入你想对桌宠说的话...")
        
        self.send_button = QPushButton("发送")
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
        
        # 记忆管理按钮
        memory_layout = QHBoxLayout()
        
        self.show_memories_btn = QPushButton("📋 查看记忆")
        self.show_memories_btn.clicked.connect(self.show_memories)
        self.show_memories_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.memory_stats_btn = QPushButton("📊 记忆统计")
        self.memory_stats_btn.clicked.connect(self.show_memory_stats)
        self.memory_stats_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        memory_layout.addWidget(self.show_memories_btn)
        memory_layout.addWidget(self.memory_stats_btn)
        memory_layout.addStretch()
        
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(memory_layout)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        
        # 让 Enter 也能发送讯息
        self.input_text.keyPressEvent = self.handle_key_press
        
    def handle_key_press(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.send_message()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
    
    def show_memories(self):
        """显示当前记忆"""
        if hasattr(self.parent(), 'send_memory_command'):
            self.parent().send_memory_command('列出记忆')
    
    def show_memory_stats(self):
        """显示记忆统计"""
        if hasattr(self.parent(), 'send_memory_command'):
            self.parent().send_memory_command('记忆统计')
            
    def send_message(self):
        user_input = self.input_text.toPlainText().strip()
        if not user_input:
            return
            
        # 显示用户讯息
        self.chat_display.append(f"<b>你:</b> {user_input}")
        self.chat_display.append("<b>桌宠:</b> 思考中...")
        self.input_text.clear()
        
        # 发送到LLM
        if hasattr(self.parent(), 'send_to_llm'):
            self.parent().send_to_llm(user_input)

class DesktopPet(QWidget):
    def __init__(self, image_paths, move_speed=8):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 初始化记忆系统
        print("正在初始化记忆系统...")
        self.memory_bot = SmartChatbotWithMemory()
        print("记忆系统初始化完成")
        
        # 载入图片
        self.frames = [QPixmap(img_path) for img_path in image_paths]
        self.frame_index = 0
        
        # 显示图片的 QLabel
        self.label = QLabel(self)
        self.label.setPixmap(self.frames[self.frame_index])
        self.resize(self.frames[0].size())
        
        # 计时器：更新动画和移动
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pet)
        self.timer.start(100)  # 100ms 更新一次
        
        # 初始位置（靠右下）
        screen = QApplication.primaryScreen().geometry()
        self.x = screen.width()
        self.y = screen.height() - self.height()
        self.move(self.x, self.y)
        
        self.move_speed = move_speed
        
        # 对话视窗
        self.chat_dialog = None
        self.llm_thread = None
        
        # 设置右键选单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position):
        """显示右键选单"""
        context_menu = QMenu(self)
        
        # 对话选项
        chat_action = QAction("💬 与桌宠对话", self)
        chat_action.triggered.connect(self.open_chat_dialog)
        context_menu.addAction(chat_action)
        
        # 快速对话选项
        quick_chat_action = QAction("⚡ 快速对话", self)
        quick_chat_action.triggered.connect(self.quick_chat)
        context_menu.addAction(quick_chat_action)
        
        context_menu.addSeparator()
        
        # 记忆管理选项
        memory_menu = context_menu.addMenu("🧠 记忆管理")
        
        show_memories_action = QAction("📋 查看记忆", self)
        show_memories_action.triggered.connect(lambda: self.send_memory_command('列出记忆'))
        memory_menu.addAction(show_memories_action)
        
        memory_stats_action = QAction("📊 记忆统计", self)
        memory_stats_action.triggered.connect(lambda: self.send_memory_command('记忆统计'))
        memory_menu.addAction(memory_stats_action)
        
        clear_memories_action = QAction("🗑️ 清除所有记忆", self)
        clear_memories_action.triggered.connect(self.clear_all_memories)
        memory_menu.addAction(clear_memories_action)
        
        context_menu.addSeparator()
        
        # 退出选项
        exit_action = QAction("❌ 退出", self)
        exit_action.triggered.connect(self.close_application)
        context_menu.addAction(exit_action)
        
        # 在滑鼠位置显示选单
        context_menu.exec_(self.mapToGlobal(position))
        
    def clear_all_memories(self):
        """清除所有记忆"""
        reply = QMessageBox.question(self, '确认', '确定要清除所有记忆吗？此操作无法撤销。',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.send_memory_command('删除所有记忆')
        
    def open_chat_dialog(self):
        """开启对话视窗"""
        if self.chat_dialog is None:
            self.chat_dialog = ChatDialog(self)
            
        self.chat_dialog.show()
        self.chat_dialog.raise_()
        self.chat_dialog.activateWindow()
        
    def quick_chat(self):
        """快速对话"""
        text, ok = QInputDialog.getText(self, '快速对话', '你想对桌宠说什么？')
        if ok and text.strip():
            self.send_to_llm(text.strip())
    
    def send_memory_command(self, command):
        """发送记忆管理命令"""
        try:
            result, llm_context, relevant_memories = self.memory_bot.process_input(command)
            
            if result['has_response']:
                # 显示结果
                if self.chat_dialog and self.chat_dialog.isVisible():
                    self.chat_dialog.chat_display.append(f"<b>系统:</b> {result['response']}")
                    self.chat_dialog.chat_display.append("")
                else:
                    QMessageBox.information(self, "记忆管理", result['response'])
            
        except Exception as e:
            error_msg = f"记忆管理出错：{str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            
    def send_to_llm(self, user_input):
        """发送讯息给LLM - 改进版"""
        if self.llm_thread and self.llm_thread.isRunning():
            QMessageBox.information(self, "提示", "桌宠还在思考中，请稍等...")
            return
        
        try:
            # 使用记忆系统处理用户输入
            result, llm_context, relevant_memories = self.memory_bot.process_input(user_input)
            
            # 如果系统已经有响应（如记忆管理命令），直接显示
            if result['has_response']:
                self.handle_system_response(result['response'])
                return
            
            # 显示记忆信息（调试用）
            if relevant_memories:
                print(f"找到 {len(relevant_memories)} 条相关记忆:")
                for memory in relevant_memories:
                    print(f"  - {memory['text'][:50]}...")
            
            if result['memory_action'] == 'add':
                print(f"新增记忆 ID: {result['memory_id']}")
            
            # 发送完整上下文给LLM
            self.llm_thread = LLMThread(user_input, llm_context)
            self.llm_thread.response_received.connect(self.handle_llm_response)
            self.llm_thread.error_occurred.connect(self.handle_llm_error)
            self.llm_thread.start()
            
        except Exception as e:
            error_msg = f"处理输入时发生错误：{str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
    
    def handle_system_response(self, response):
        """处理系统响应"""
        if self.chat_dialog and self.chat_dialog.isVisible():
            # 移除 "思考中..." 的最后一行
            cursor = self.chat_dialog.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # 删除换行符
            
            # 添加实际响应
            self.chat_dialog.chat_display.append(f"<b>桌宠:</b> {response}")
            self.chat_dialog.chat_display.append("")  # 空行分隔
        else:
            # 如果没有对话视窗，用讯息框显示
            QMessageBox.information(self, "桌宠回应", response)
            
    def handle_llm_response(self, response):
        """处理LLM响应"""
        # 如果对话视窗开着，更新对话记录
        if self.chat_dialog and self.chat_dialog.isVisible():
            # 移除 "思考中..." 的最后一行
            cursor = self.chat_dialog.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # 删除换行符
            
            # 添加实际响应
            self.chat_dialog.chat_display.append(f"<b>桌宠:</b> {response}")
            self.chat_dialog.chat_display.append("")  # 空行分隔
            
            # 滚动到底部
            self.chat_dialog.chat_display.moveCursor(self.chat_dialog.chat_display.textCursor().End)
        else:
            # 如果没有对话视窗，用讯息框显示
            msg = QMessageBox(self)
            msg.setWindowTitle("桌宠的回应")
            msg.setText(response)
            msg.setStandardButtons(QMessageBox.Ok)
            # 设置讯息框大小以适应长文本
            msg.setStyleSheet("QLabel{min-width: 300px; max-width: 500px;}")
            msg.exec_()
            
    def handle_llm_error(self, error_message):
        """处理LLM错误"""
        error_text = f"抱歉，我现在无法回应：{error_message}"
        
        if self.chat_dialog and self.chat_dialog.isVisible():
            # 移除 "思考中..."
            cursor = self.chat_dialog.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
            
            self.chat_dialog.chat_display.append(f"<b>桌宠:</b> <span style='color: red;'>{error_text}</span>")
            self.chat_dialog.chat_display.append("")
        else:
            QMessageBox.critical(self, "错误", f"无法连接到LLM服务：\n{error_message}")
            
    def close_application(self):
        """关闭应用程式"""
        # 保存记忆系统
        try:
            print("正在保存记忆系统...")
            self.memory_bot._save_memory()
            print("记忆系统已保存")
        except Exception as e:
            print(f"保存记忆系统时出错: {e}")
        
        if self.chat_dialog:
            self.chat_dialog.close()
        QApplication.quit()
        
    def update_pet(self):
        """更新桌宠动画和位置"""
        # 换下一张图
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.label.setPixmap(self.frames[self.frame_index])
        
        # 向左移动
        self.x -= self.move_speed
        if self.x < -self.width():  # 出画面就从右边出现
            screen = QApplication.primaryScreen().geometry()
            self.x = screen.width()
        self.move(self.x, self.y)
        
    def mousePressEvent(self, event):
        """处理滑鼠点击事件"""
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        else:
            # 左键点击显示记忆统计
            stats = self.memory_bot.get_stats()
            stats_text = f"📊 记忆统计\n活跃记忆: {stats['active']}\n总记忆: {stats['total']}"
            
            # 创建一个临时的提示框
            tooltip = QMessageBox(self)
            tooltip.setWindowTitle("桌宠状态")
            tooltip.setText(stats_text)
            tooltip.setStandardButtons(QMessageBox.Ok)
            tooltip.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            
            # 设置位置在桌宠旁边
            tooltip.move(self.x - 150, self.y - 100)
            
            # 自动关闭
            QTimer.singleShot(3000, tooltip.close)
            tooltip.show()
            
        super().mousePressEvent(event)
    
    def closeEvent(self, event):
        """重写关闭事件以保存记忆"""
        try:
            print("应用程式关闭中，正在保存记忆...")
            self.memory_bot._save_memory()
            print("记忆系统已保存")
        except Exception as e:
            print(f"保存记忆时出错: {e}")
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 载入图片清单
    folder = "Walk"
    if not os.path.exists(folder):
        QMessageBox.critical(None, "错误", f"找不到图片资料夹 '{folder}'！\n请确保资料夹存在并包含PNG图片档案。")
        sys.exit(1)
        
    image_paths = [os.path.join(folder, img) for img in sorted(os.listdir(folder)) if img.endswith(".png")]
    
    if not image_paths:
        QMessageBox.critical(None, "错误", f"在 '{folder}' 资料夹中找不到PNG图片！\n请放入一些桌宠图片。")
        sys.exit(1)
    
    # 检查环境变数
    load_dotenv()
    if not os.getenv("LLM_API_KEY"):
        QMessageBox.warning(None, "警告", 
                          "找不到 LLM_API_KEY 环境变数！\n"
                          "请在 .env 档案中设置你的API Key。\n"
                          "桌宠仍可正常显示，但无法与LLM对话。\n"
                          "记忆系统功能仍可正常使用。")
    
    # 检查记忆系统依赖
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ 记忆系统依赖检查完成")
    except ImportError:
        QMessageBox.warning(None, "警告", 
                          "记忆系统依赖未完整安装！\n"
                          "请执行：pip install sentence-transformers faiss-cpu\n"
                          "桌宠将使用简化的记忆功能。")
    
    # 创建并显示桌宠
    pet = DesktopPet(image_paths)
    pet.show()
    
    print("🐾 智能记忆桌宠已启动")
    print("💡 使用说明：")
    print("   - 左键点击：查看记忆统计") 
    print("   - 右键点击：打开功能选单")
    print("   - 可以说 '记住我叫小明' 来存储信息")
    print("   - 可以问 '我叫什么名字？' 来测试记忆")
    print("   - 支持删除记忆、查看记忆等功能")
    
    sys.exit(app.exec_())