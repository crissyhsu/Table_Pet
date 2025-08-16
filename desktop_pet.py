"""
桌面寵物控制模塊
處理桌寵的顯示、動畫和互動
"""

import os
from typing import List, Optional, Callable
from PyQt5.QtWidgets import (QWidget, QLabel, QMenu, QAction, QInputDialog, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QCursor


class PetAnimationState:
    """寵物動畫狀態枚舉"""
    IDLE = "Idle"
    WALKING = "Walk"


class DesktopPet(QWidget):
    """桌面寵物主體類"""
    
    def __init__(self, idle_images: List[str], walk_images: List[str] = None, move_speed: int = 8):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 動畫狀態管理
        self.current_state = PetAnimationState.IDLE
        self.idle_frames = [QPixmap(img_path) for img_path in idle_images]
        self.walk_frames = [QPixmap(img_path) for img_path in walk_images] if walk_images else []
        self.frame_index = 0
        
        # 顯示圖片的 QLabel
        self.label = QLabel(self)
        self.label.setPixmap(self.idle_frames[0])
        self.resize(self.idle_frames[0].size())
        
        # 移動相關
        self.move_speed = move_speed
        self.is_walking = False
        
        # 計時器：更新動畫和移動
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(150)  # 150ms 更新一次動畫
        
        self.move_timer = QTimer()
        self.move_timer.timeout.connect(self.update_position)
        
        # 初始位置（螢幕中下方）
        self._setup_initial_position()
        
        # 滑鼠拖曳相關
        self.dragging = False
        self.drag_position = QPoint()
        
        # 回調函數
        self.on_chat_request: Optional[Callable[[str], None]] = None
        self.on_quick_chat_request: Optional[Callable[[], None]] = None
        self.on_memory_command: Optional[Callable[[str], None]] = None
        self.on_exit_request: Optional[Callable[[], None]] = None
        
        # 設置右鍵選單
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def _setup_initial_position(self):
        """設置初始位置（螢幕中下方）"""
        screen = QApplication.primaryScreen().geometry()
        self.x = screen.width() // 2 - self.width() // 2
        self.y = screen.height() - self.height() - 100
        self.move(self.x, self.y)
    
    def set_callbacks(self, on_chat=None, on_quick_chat=None, on_memory_command=None, on_exit=None):
        """設置回調函數"""
        if on_chat:
            self.on_chat_request = on_chat
        if on_quick_chat:
            self.on_quick_chat_request = on_quick_chat
        if on_memory_command:
            self.on_memory_command = on_memory_command
        if on_exit:
            self.on_exit_request = on_exit
    
    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)
        
        # 對話選項
        chat_action = QAction("💬 與桌寵對話", self)
        chat_action.triggered.connect(lambda: self.on_chat_request() if self.on_chat_request else None)
        context_menu.addAction(chat_action)
        
        # 快速對話選項
        quick_chat_action = QAction("⚡ 快速對話", self)
        quick_chat_action.triggered.connect(lambda: self.on_quick_chat_request() if self.on_quick_chat_request else None)
        context_menu.addAction(quick_chat_action)
        
        context_menu.addSeparator()
        
        # 動作選項
        action_menu = context_menu.addMenu("🎭 改變動作")
        
        idle_action = QAction("🏠 待機", self)
        idle_action.triggered.connect(lambda: self.set_animation_state(PetAnimationState.IDLE))
        action_menu.addAction(idle_action)
        
        if self.walk_frames:  # 只有在有走路動畫時才顯示
            walk_action = QAction("🚶 向左走", self)
            walk_action.triggered.connect(lambda: self.set_animation_state(PetAnimationState.WALKING))
            action_menu.addAction(walk_action)
        
        context_menu.addSeparator()
        
        # 記憶管理選項
        memory_menu = context_menu.addMenu("🧠 記憶管理")
        
        show_memories_action = QAction("📋 查看記憶", self)
        show_memories_action.triggered.connect(lambda: self.on_memory_command('列出記憶') if self.on_memory_command else None)
        memory_menu.addAction(show_memories_action)
        
        memory_stats_action = QAction("📊 記憶統計", self)
        memory_stats_action.triggered.connect(lambda: self.on_memory_command('記憶統計') if self.on_memory_command else None)
        memory_menu.addAction(memory_stats_action)
        
        clear_memories_action = QAction("🗑️ 清除所有記憶", self)
        clear_memories_action.triggered.connect(self.clear_all_memories)
        memory_menu.addAction(clear_memories_action)
        
        context_menu.addSeparator()
        
        # 退出選項
        exit_action = QAction("❌ 退出", self)
        exit_action.triggered.connect(lambda: self.on_exit_request() if self.on_exit_request else None)
        context_menu.addAction(exit_action)
        
        # 在滑鼠位置顯示選單
        context_menu.exec_(self.mapToGlobal(position))
    
    def clear_all_memories(self):
        """清除所有記憶"""
        reply = QMessageBox.question(self, '確認', '確定要清除所有記憶嗎？此操作無法撤銷。',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.on_memory_command:
                self.on_memory_command('刪除所有記憶')
    
    def set_animation_state(self, state: str):
        """設置動畫狀態"""
        if state == PetAnimationState.WALKING and not self.walk_frames:
            QMessageBox.information(self, "提示", "沒有可用的走路動畫")
            return
            
        self.current_state = state
        self.frame_index = 0
        
        if state == PetAnimationState.WALKING:
            self.is_walking = True
            self.move_timer.start(50)  # 50ms 更新一次位置
        else:
            self.is_walking = False
            self.move_timer.stop()
    
    def update_animation(self):
        """更新動畫幀"""
        if self.current_state == PetAnimationState.WALKING and self.walk_frames:
            frames = self.walk_frames
        else:
            frames = self.idle_frames
        
        # 切換到下一幀
        self.frame_index = (self.frame_index + 1) % len(frames)
        self.label.setPixmap(frames[self.frame_index])
    
    def update_position(self):
        """更新位置（用於走路動畫）"""
        if not self.is_walking:
            return
            
        # 向左移動
        self.x -= self.move_speed
        if self.x < -self.width():  # 出畫面就從右邊出現
            screen = QApplication.primaryScreen().geometry()
            self.x = screen.width()
        self.move(self.x, self.y)
    
    def mousePressEvent(self, event):
        """處理滑鼠按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """處理滑鼠移動事件（拖曳）"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            new_pos = event.globalPos() - self.drag_position
            self.move(new_pos)
            # 更新位置變數
            self.x = new_pos.x()
            self.y = new_pos.y()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """處理滑鼠釋放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
        super().mouseReleaseEvent(event)
    
    def show_status_tooltip(self, message: str, duration: int = 3000):
        """顯示狀態提示"""
        tooltip = QMessageBox(self)
        tooltip.setWindowTitle("桌寵狀態")
        tooltip.setText(message)
        tooltip.setStandardButtons(QMessageBox.Ok)
        tooltip.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 設置位置在桌寵旁邊
        tooltip.move(self.x - 150, self.y - 100)
        
        # 自動關閉
        QTimer.singleShot(duration, tooltip.close)
        tooltip.show()
    
    def get_current_state(self) -> str:
        """獲取當前狀態"""
        return self.current_state
    
    def closeEvent(self, event):
        """關閉事件"""
        if self.on_exit_request:
            self.on_exit_request()
        event.accept()


def load_animation_frames(folder_path: str) -> List[str]:
    """載入動畫幀圖片路徑"""
    if not os.path.exists(folder_path):
        return []
    
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    image_files.sort()  # 按檔名排序
    
    return [os.path.join(folder_path, img) for img in image_files]


def validate_image_folders(idle_folder: str, walk_folder: str = None) -> tuple:
    """驗證圖片資料夾"""
    idle_images = load_animation_frames(idle_folder)
    walk_images = load_animation_frames(walk_folder) if walk_folder else []
    
    errors = []
    
    if not idle_images:
        errors.append(f"找不到待機動畫圖片在資料夾: {idle_folder}")
    
    if walk_folder and not walk_images:
        errors.append(f"找不到走路動畫圖片在資料夾: {walk_folder}")
    
    return idle_images, walk_images, errors