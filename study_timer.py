"""
學習計時器模塊
在螢幕中央顯示倒數計時器
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal
from PyQt5.QtGui import QFont, QPalette


class StudyTimerWidget(QWidget):
    """學習倒數計時器視窗"""
    
    # 信號
    timer_finished = pyqtSignal()
    timer_paused = pyqtSignal()
    timer_resumed = pyqtSignal()
    
    def __init__(self, total_seconds: int, parent=None):
        super().__init__(parent)
        self.total_seconds = total_seconds
        self.remaining_seconds = total_seconds
        self.is_paused = False
        
        # 拖動相關變數
        self.dragging = False
        self.drag_position = None
        
        self.setup_ui()
        self.setup_timer()
        self.center_on_screen()

    def create_timer_label(self, text="00:00"):
        """建立時間顯示標籤"""
        time_label = QLabel(text)
        time_label.setAlignment(Qt.AlignCenter)

        # 使用系統字體確保相容性
        time_font = QFont()
        time_font.setFamily("Arial")  # 使用通用字體
        time_font.setPointSize(24)    # 適中的字體大小
        time_font.setBold(True)
        time_label.setFont(time_font)

        # 設定合適大小，避免壓縮
        time_label.setFixedSize(280, 70)

        # 優化的樣式
        time_label.setStyleSheet("""
            color: #e74c3c;
            background-color: rgba(0, 0, 0, 50);
            border-radius: 10px;
            border: 2px solid rgba(231, 76, 60, 180);
            font-weight: bold;
            letter-spacing: 2px;
        """)

        return time_label
    
    def setup_ui(self):
        """設置使用者介面"""
        # 設置視窗屬性
        self.setWindowTitle("讀書陪伴計時器")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 270)
        
        # 創建主容器
        main_container = QWidget()
        main_container.setFixedSize(400, 260)
        
        # 主佈局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 設置主容器背景 - 半透明白底
        main_container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 15px;
                border: 2px solid rgba(100, 149, 237, 150);
            }
        """)
        
        # 內容佈局
        content_layout = QVBoxLayout(main_container)
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(10)
        
        # 標題
        self.title_label = QLabel("📚 讀書陪伴中")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setFixedHeight(30)
        self.title_label.setStyleSheet("""
                background-color: transparent;
                border: none;
                font-weight: bold;
        """)
        content_layout.addWidget(self.title_label)
        
        # 時間顯示
        self.time_label = self.create_timer_label(self._format_time(self.remaining_seconds))
        content_layout.addWidget(self.time_label, alignment=Qt.AlignCenter)
        
        # 控制按鈕
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.pause_button = QPushButton("⏸️ 暫停")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.pause_button.setFixedSize(90, 32)
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        
        self.stop_button = QPushButton("⏹️ 停止")
        self.stop_button.clicked.connect(self._stop_timer)
        self.stop_button.setFixedSize(90, 32)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        # 進度條
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFixedHeight(20)
        progress_font = QFont()
        progress_font.setPointSize(9)
        self.progress_label.setFont(progress_font)
        self.progress_label.setStyleSheet("""
            color: #7f8c8d; 
            background-color: transparent;
            border: none;
        """)
        content_layout.addWidget(self.progress_label)
        
        # 將主容器加入佈局
        layout.addWidget(main_container)
        self.setLayout(layout)
        
        # 更新進度
        self._update_progress()
    
    def setup_timer(self):
        """設置計時器"""
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start(1000)  # 每秒更新一次
    
    def center_on_screen(self):
        """將視窗置於螢幕中央"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _format_time(self, seconds: int) -> str:
        """格式化時間顯示"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def _update_countdown(self):
        """更新倒數計時"""
        if self.is_paused:
            return
        
        self.remaining_seconds -= 1
        self.time_label.setText(self._format_time(self.remaining_seconds))
        self._update_progress()
        
        # 時間快結束時改變顏色
        if self.remaining_seconds <= 60:  # 最後一分鐘
            self.time_label.setStyleSheet("""
                color: #ff6b6b;
                background-color: rgba(255, 107, 107, 40);
                border-radius: 10px;
                border: 2px solid #ff6b6b;
                font-weight: bold;
                letter-spacing: 2px;
            """)
            
            # 最後10秒閃爍效果
            if self.remaining_seconds <= 10:
                self.title_label.setText(f"⏰ 還剩 {self.remaining_seconds} 秒！")
                self.title_label.setStyleSheet("""
                    color: #ff6b6b; 
                    background-color: transparent;
                    border: none;
                    font-weight: bold;
                """)
        
        # 檢查是否結束
        if self.remaining_seconds <= 0:
            self._timer_finished()
    
    def _update_progress(self):
        """更新進度顯示"""
        if self.total_seconds > 0:
            progress_percent = ((self.total_seconds - self.remaining_seconds) / self.total_seconds) * 100
            elapsed_minutes = (self.total_seconds - self.remaining_seconds) // 60
            total_minutes = self.total_seconds // 60
            self.progress_label.setText(f"進度: {progress_percent:.1f}% ({elapsed_minutes}/{total_minutes} 分鐘)")
        else:
            self.progress_label.setText("進度: 100%")
    
    def _toggle_pause(self):
        """切換暫停/繼續"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_button.setText("▶️ 繼續")
            self.title_label.setText("⏸️ 已暫停")
            self.title_label.setStyleSheet("""
                color: #f39c12; 
                background-color: transparent;
                border: none;
                font-weight: bold;
            """)
            self.timer_paused.emit()
            print("⏸️ 學習計時器已暫停")
        else:
            self.pause_button.setText("⏸️ 暫停")
            self.title_label.setText("📚 讀書陪伴中")
            self.title_label.setStyleSheet("""
                color: #2c3e50; 
                background-color: transparent;
                border: none;
            """)
            self.timer_resumed.emit()
            print("▶️ 學習計時器已繼續")
    
    def _stop_timer(self):
        """停止計時器"""
        self.countdown_timer.stop()
        self.timer_finished.emit()
        #self.close()
        self._timer_finished()
        print("⏹️ 學習計時器已停止")
    
    def _timer_finished(self):
        """計時結束"""
        self.countdown_timer.stop()
        
        # 更新顯示
        self.time_label.setText("00:00")
        self.title_label.setText("🎉 時間到！")
        self.title_label.setStyleSheet("""
            color: #27ae60; 
            background-color: transparent;
            border: none;
            font-weight: bold;
        """)
        self.progress_label.setText("進度: 100% - 完成！")
        
        # 隱藏控制按鈕
        self.pause_button.hide()
        self.stop_button.setText("✅ 完成")
        
        # 發送完成信號 - 但不要立即關閉
        self.timer_finished.emit()
        
        # 3秒後自動關閉計時器窗口（但不關閉桌寵）
        QTimer.singleShot(3000, self.hide)
        
        print("🎉 學習時間結束！")
    
    def keyPressEvent(self, event):
        """處理鍵盤事件"""
        if event.key() == Qt.Key_Escape:
            self._stop_timer()
        elif event.key() == Qt.Key_Space:
            self._toggle_pause()
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """關閉事件"""
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        self.timer_finished.emit()
        event.accept()
    
    def mousePressEvent(self, event):
        """滑鼠按下事件 - 開始拖動"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """滑鼠移動事件 - 拖動視窗"""
        if event.buttons() == Qt.LeftButton and self.dragging and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """滑鼠釋放事件 - 停止拖動"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_position = None
            event.accept()