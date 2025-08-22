"""
桌面寵物控制模組 - 修正版
處理桌寵的顯示、動畫和互動
"""

import os
import time
from typing import List, Optional, Callable
from PyQt5.QtWidgets import (QWidget, QLabel, QMenu, QAction, QInputDialog, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QCursor


class PetAnimationState:
    """寵物動畫狀態枚舉"""
    IDLE = "Idle"
    WALKING = "Walk"
    STUDYING = "Study"  # 讀書陪伴模式 - 未畫好，先用Walk
    TAKE = "Take"       
    THROW = "Throw"     # 拋擲其他視窗時的動畫 - 未畫好，先用Walk


class DesktopPet(QWidget):
    """桌面寵物主體類"""
    
    # 信號
    study_time_finished = pyqtSignal()
    
    def __init__(self, idle_images: List[str], walk_images: List[str] = None, take_images: List[str] = None, move_speed: int = 8):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 動畫狀態管理
        self.current_state = PetAnimationState.IDLE
        self.previous_state = PetAnimationState.IDLE  # 保存之前的狀態
        self.idle_frames = [QPixmap(img_path) for img_path in idle_images]
        self.walk_frames = [QPixmap(img_path) for img_path in walk_images] if walk_images else []
        self.take_frames = [QPixmap(img_path) for img_path in take_images] if take_images else []

        print(f"🔍 DesktopPet 初始化除錯:")
        print(f"   take_images 參數: {take_images}")
        print(f"   take_frames 數量: {len(self.take_frames)}")
        if self.take_frames:
            print(f"   第一張圖片載入成功: {self.take_frames[0].isNull() == False}")
        
        # TODO: 以下動畫資料夾未完成繪圖，暫時使用walk_frames代替
        self.study_frames = self.walk_frames.copy()  # 將來替換為Study資料夾
        #self.take_frames = self.take_frames.copy()  
        self.throw_frames = self.walk_frames.copy()  # 將來替換為Throw資料夾
        
        self.frame_index = 0
        
        # 顯示圖片的 QLabel
        self.label = QLabel(self)
        self.label.setPixmap(self.idle_frames[0])
        self.resize(self.idle_frames[0].size())
        
        # 移動相關
        self.move_speed = move_speed
        self.is_walking = False
        self.target_x = 0
        self.target_y = 0
        self.original_x = 0
        self.original_y = 0
        
        # 計時器：更新動畫和移動
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(150)  # 150ms 更新一次動畫
        
        self.move_timer = QTimer()
        self.move_timer.timeout.connect(self.update_position)

        #Take速度要比別人快，所以單獨開一個計時器
        self.take_animation_timer = QTimer()
        self.take_animation_timer.timeout.connect(self.update_take_animation)
        
        # 讀書陪伴模式相關
        self.study_mode_active = False
        self.study_timer = QTimer()
        self.study_timer.timeout.connect(self._on_study_time_finished)
        
        # 究級專注模式相關
        self.focus_mode_active = False
        self.focus_check_timer = QTimer()
        self.focus_check_timer.timeout.connect(self._check_and_handle_windows)
        self.is_handling_window = False  # 防止同時處理多個視窗
        
        # 重力下落相關
        self.is_falling = False
        self.fall_timer = QTimer()
        self.fall_timer.timeout.connect(self.update_fall)
        self.fall_speed = 0
        self.gravity = 1
        
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
        self.original_x = self.x
        self.original_y = self.y
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
        
        # 互動模式選項
        interaction_menu = context_menu.addMenu("🎮 互動模式")
        
        # 讀書陪伴
        study_action = QAction("📚 讀書陪伴", self)
        study_action.triggered.connect(self._start_study_mode)
        interaction_menu.addAction(study_action)
        
        # 究級專注模式
        focus_action = QAction("🎯 究級專注模式", self)
        if self.focus_mode_active:
            focus_action.setText("🎯 關閉專注模式")
            focus_action.triggered.connect(self._stop_focus_mode)
        else:
            focus_action.triggered.connect(self._start_focus_mode)
        interaction_menu.addAction(focus_action)
        
        # *** 修改重點：只有在真正活動時才顯示停止選項 ***
        if self.study_mode_active:
            stop_study_action = QAction("⏹️ 停止讀書陪伴", self)
            stop_study_action.triggered.connect(self._stop_study_mode)
            interaction_menu.addAction(stop_study_action)
        
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
        
        if self.take_frames:  # 只有在有拖曳動畫時才顯示
            take_action = QAction("✋ 拖曳動作", self)
            take_action.triggered.connect(lambda: self.set_animation_state(PetAnimationState.TAKE))
            action_menu.addAction(take_action)
        
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
    
    def _start_study_mode(self):
        """開始讀書陪伴模式"""
        if self.study_mode_active:
            QMessageBox.information(self, "提示", "讀書陪伴模式已經開啟中")
            return
        
        # 詢問學習時長
        time_text, ok = QInputDialog.getText(
            self, 
            "讀書陪伴", 
            "請輸入學習時長（分鐘）：",
            text="25"
        )
        
        if ok and time_text.strip().isdigit():
            study_minutes = int(time_text.strip())
            if study_minutes <= 0:
                QMessageBox.warning(self, "警告", "學習時長必須大於0分鐘")
                return
            
            self.study_mode_active = True
            self.set_animation_state(PetAnimationState.STUDYING)
            
            # 設置計時器
            self.study_timer.start(study_minutes * 60 * 1000)  # 轉為毫秒
            
            # 創建倒數計時器視窗
            from study_timer import StudyTimerWidget
            self.study_timer_widget = StudyTimerWidget(study_minutes * 60)
            self.study_timer_widget.show()
            
            print(f"📚 開始讀書陪伴模式，時長：{study_minutes}分鐘")
        
    def _stop_study_mode(self):
        """停止讀書陪伴模式 - 修正版：不會關閉桌寵"""
        if not self.study_mode_active:
            return
        
        print("📚 停止讀書陪伴模式...")
        
        # *** 修改重點：先設置狀態為False ***
        self.study_mode_active = False
        self.study_timer.stop()
        
        # 關閉倒數計時器視窗
        if hasattr(self, 'study_timer_widget'):
            #self.study_timer_widget.close()
            delattr(self, 'study_timer_widget')
        
        # 回到待機狀態
        self.set_animation_state(PetAnimationState.IDLE)
        print("📚 讀書陪伴模式已停止")
    
    def _on_study_time_finished(self):
        """學習時間結束 - 修正版：不會關閉桌寵"""
        print("⏰ 學習時間自然結束")
        
        # *** 修改重點：先停止模式，再顯示訊息 ***
        self._stop_study_mode()
        
        # 顯示完成訊息（但不會觸發關閉）
        QMessageBox.information(self, "讀書陪伴", "學習時間結束！辛苦了～ 🎉")
        
        print("✅ 學習完成流程結束，桌寵繼續運行")
    
    def _start_focus_mode(self):
        """開始究級專注模式"""
        if self.focus_mode_active:
            return
        
        reply = QMessageBox.question(self, '確認', 
                                   '開啟究級專注模式？\n'
                                   '桌寵會自動關閉其他應用程式視窗來幫助你專注學習。',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.focus_mode_active = True
            
            # 初始化專注模式處理器
            try:
                from window_manager import FocusModeHandler
                self.focus_handler = FocusModeHandler(self)
                self.focus_check_timer.start(2000)  # 每2秒檢查一次
                print("🎯 究級專注模式已開啟")
            except ImportError as e:
                QMessageBox.warning(self, "警告", 
                                  f"專注模式功能不完整：{str(e)}\n"
                                  "可能需要安裝額外依賴或在Windows平台運行")
                self.focus_mode_active = False
    
    def _stop_focus_mode(self):
        """停止究級專注模式"""
        self.focus_mode_active = False
        self.focus_check_timer.stop()
        
        # 清除專注模式處理器
        if hasattr(self, 'focus_handler'):
            delattr(self, 'focus_handler')
        
        print("🎯 究級專注模式已關閉")
    
    def _check_and_handle_windows(self):
        """檢查並處理其他視窗 - 調試版"""
        if not self.focus_mode_active or self.is_handling_window:
            return
        
        print("🔍 專注模式：正在檢查視窗...")
        
        try:
            # 使用視窗管理器檢查分心視窗
            if hasattr(self, 'focus_handler'):
                print("🎯 呼叫 focus_handler 檢查視窗...")
                handled = self.focus_handler.check_and_handle_distracting_windows()
                if handled:
                    print("🎯 專注模式：檢測到分心視窗，桌寵開始行動")
                else:
                    print("🎯 專注模式：未檢測到分心視窗")
            else:
                print("❌ focus_handler 不存在")
                
        except Exception as e:
            print(f"❌ 檢查視窗時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    def _walk_to_window_and_throw(self, target_x: int, target_y: int, window_info):
        """走向視窗並執行拋擲動作 - 修正版"""
        print(f"🚶 開始走向視窗: {window_info.title}")
        print(f"🎯 目標位置: ({target_x}, {target_y})")
        
        if self.is_handling_window:
            print("⚠️ 已在處理其他視窗，跳過")
            return
        
        self.is_handling_window = True
        self.previous_state = self.current_state
        self.target_window = window_info
        
        # 先停止其他移動
        self.is_walking = False
        self.move_timer.stop()
        
        print(f"🎮 切換到走路狀態，當前位置: ({self.x}, {self.y})")
        
        # 走向目標位置
        self._walk_to_position(target_x, target_y, callback=self._perform_window_throw)
    
    def _walk_to_position(self, target_x: int, target_y: int, callback: Callable = None):
        """走向指定位置 - 修正版"""
        # 確保目標位置在螢幕範圍內
        screen = QApplication.primaryScreen().geometry()
        self.target_x = max(0, min(target_x, screen.width() - self.width()))
        self.target_y = max(0, min(target_y, screen.height() - self.height()))
        
        print(f"🎯 設置目標位置: ({self.target_x}, {self.target_y})")
        print(f"🔍 當前位置: ({self.x}, {self.y})")
        
        self.walk_callback = callback
        
        self.set_animation_state(PetAnimationState.WALKING)
        self.is_walking = True
        self.move_timer.start(30)  # 更頻繁的更新，讓移動更流暢
    
    def update_position(self):
        """更新位置（用於移動動畫）- 修正版"""
        if not self.is_walking:
            return
        
        # 如果有目標位置，走向目標
        if hasattr(self, 'target_x') and hasattr(self, 'target_y'):
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = (dx**2 + dy**2)**0.5
            
            # 如果接近目標位置
            if distance < self.move_speed:
                print(f"🎯 到達目標位置: ({self.target_x}, {self.target_y})")
                self.x = self.target_x
                self.y = self.target_y
                self.move(self.x, self.y)
                self.is_walking = False
                self.move_timer.stop()
                
                # 執行回調
                if hasattr(self, 'walk_callback') and self.walk_callback:
                    print("📞 執行到達回調函數")
                    callback = self.walk_callback
                    self.walk_callback = None
                    callback()
                return
            
            # 計算移動方向
            if distance > 0:
                move_x = (dx / distance) * self.move_speed
                move_y = (dy / distance) * self.move_speed
                self.x += int(move_x)
                self.y += int(move_y)
        
        else:
            # 自由移動（原來的邏輯）
            self.x -= self.move_speed
            if self.x < -self.width():  # 出畫面就從右邊出現
                screen = QApplication.primaryScreen().geometry()
                self.x = screen.width()
        
        self.move(self.x, self.y)

    def _perform_window_throw(self):
        """執行視窗拋擲動作 - 完整重寫版"""
        print("🎭 開始執行拋擲動作")
        
        if not hasattr(self, 'target_window'):
            print("❌ 找不到目標視窗")
            self._finish_window_handling()
            return
        
        # 切換到拋擲動畫
        self.set_animation_state(PetAnimationState.THROW)
        
        # 初始化視窗管理器
        try:
            from window_manager import WindowManager
            window_manager = WindowManager()
            
            # 設置拋物線動畫參數
            self._setup_throw_animation()
            
            # 開始拋物線動畫
            self.throw_animation_timer = QTimer()
            self.throw_animation_timer.timeout.connect(
                lambda: self._update_throw_animation(window_manager)
            )
            self.throw_animation_timer.start(50)  # 50ms更新一次，讓動畫流暢
            
        except Exception as e:
            print(f"❌ 初始化拋擲動畫失敗: {e}")
            # 直接關閉視窗作為後備方案
            self._direct_close_window()
    
    def _setup_throw_animation(self):
        """設置拋物線動畫參數"""
        screen = QApplication.primaryScreen().geometry()
        window_rect = self.target_window.rect
        left, top, right, bottom = window_rect
        
        # 動畫起始點：視窗當前位置
        self.throw_start_x = left
        self.throw_start_y = top
        
        # 動畫結束點：根據拋擲方向決定
        window_center_x = (left + right) // 2
        if self.x < window_center_x:
            # 桌寵在左邊，向右拋
            self.throw_end_x = screen.width() + 200
        else:
            # 桌寵在右邊，向左拋
            self.throw_end_x = -200
        
        self.throw_end_y = -200  # 拋到螢幕上方外
        
        # 拋物線控制點（創造弧形軌跡）
        self.throw_control_x = (self.throw_start_x + self.throw_end_x) // 2
        self.throw_control_y = min(self.throw_start_y, self.throw_end_y) - 150
        
        # 動畫參數
        self.throw_animation_step = 0
        self.throw_total_steps = 40  # 總步數，控制動畫速度
        
        print(f"🎬 拋物線動畫設置完成:")
        print(f"   起點: ({self.throw_start_x}, {self.throw_start_y})")
        print(f"   終點: ({self.throw_end_x}, {self.throw_end_y})")
        print(f"   控制點: ({self.throw_control_x}, {self.throw_control_y})")
    
    def _update_throw_animation(self, window_manager):
        """更新拋物線動畫 - 修正版"""
        if not hasattr(self, 'target_window') or not hasattr(self, 'throw_animation_step'):
            print("❌ 動畫參數缺失，停止動畫")
            self._cleanup_throw_animation()
            return
        
        try:
            # 計算動畫進度 (0.0 到 1.0)
            progress = self.throw_animation_step / self.throw_total_steps
            
            if progress >= 1.0:
                print("🎬 拋物線動畫完成，關閉視窗")
                # 動畫完成，關閉視窗
                close_success = window_manager.close_window(self.target_window.hwnd)
                if close_success:
                    print(f"✅ 成功關閉視窗: {self.target_window.title}")
                else:
                    print(f"⚠️ 關閉視窗可能失敗: {self.target_window.title}")
                
                # 清理動畫相關變數
                self._cleanup_throw_animation()
                
                # 完成動作
                QTimer.singleShot(500, self._finish_window_handling)
                return
            
            # 貝茲曲線計算（二次貝茲曲線，創造拋物線效果）
            t = progress
            one_minus_t = 1 - t
            
            # 計算當前位置
            current_x = int(
                one_minus_t * one_minus_t * self.throw_start_x +
                2 * one_minus_t * t * self.throw_control_x +
                t * t * self.throw_end_x
            )
            
            current_y = int(
                one_minus_t * one_minus_t * self.throw_start_y +
                2 * one_minus_t * t * self.throw_control_y +
                t * t * self.throw_end_y
            )
            
            # 移動視窗
            move_success = window_manager.move_window(self.target_window, current_x, current_y)
            
            if not move_success and self.throw_animation_step < 5:
                print(f"⚠️ 移動視窗失敗 (步驟 {self.throw_animation_step})")
            
            # 更新步數
            self.throw_animation_step += 1
            
            # 加速效果（重力模擬）
            if progress > 0.6:
                self.throw_animation_step += 0.8  # 後段加速
            
            if self.throw_animation_step % 5 == 0:  # 每5步輸出一次進度
                print(f"🎬 拋物線進度: {progress:.1%}, 位置: ({current_x}, {current_y})")
            
        except Exception as e:
            print(f"❌ 拋物線動畫更新失敗: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup_throw_animation()
            self._direct_close_window()
    
    def _direct_close_window(self):
        """直接關閉視窗（後備方案）"""
        print("🔧 使用後備方案直接關閉視窗")
        try:
            from window_manager import WindowManager
            window_manager = WindowManager()
            close_success = window_manager.close_window(self.target_window.hwnd)
            if close_success:
                print(f"✅ 後備方案成功關閉視窗: {self.target_window.title}")
            else:
                print(f"❌ 後備方案也無法關閉視窗: {self.target_window.title}")
        except Exception as e:
            print(f"❌ 後備方案失敗: {e}")
        
        # 無論成功與否都要完成處理流程
        self._finish_window_handling()
    
    def _cleanup_throw_animation(self):
        """清理拋物線動畫相關變數"""
        print("🧹 清理拋物線動畫參數")
        
        if hasattr(self, 'throw_animation_timer'):
            self.throw_animation_timer.stop()
            delattr(self, 'throw_animation_timer')
            print("🛑 拋物線計時器已停止")
        
        # 清理動畫參數
        attrs_to_remove = [
            'throw_animation_step', 'throw_total_steps',
            'throw_start_x', 'throw_start_y', 'throw_end_x', 'throw_end_y',
            'throw_control_x', 'throw_control_y'
        ]
        
        for attr in attrs_to_remove:
            if hasattr(self, attr):
                delattr(self, attr)
        
        print("✅ 動畫參數清理完成")
    
    def _finish_window_handling(self):
        """完成視窗處理，返回原位 - 修正版"""
        print("🏠 準備返回原位")
        print(f"🔍 原位座標: ({self.original_x}, {self.original_y})")
        print(f"🔍 當前座標: ({self.x}, {self.y})")
        
        # 走回原位
        self._walk_to_position(self.original_x, self.original_y, callback=self._return_to_previous_state)
        
        # 清除目標視窗
        if hasattr(self, 'target_window'):
            print(f"🗑️ 清除目標視窗: {self.target_window.title}")
            delattr(self, 'target_window')
    
    def _return_to_previous_state(self):
        """返回之前的狀態 - 修正版"""
        print(f"🔄 返回之前的狀態: {self.previous_state}")
        self.is_handling_window = False
        self.set_animation_state(self.previous_state)
        print("✅ 視窗處理流程完成")
    
    def clear_all_memories(self):
        """清除所有記憶"""
        reply = QMessageBox.question(self, '確認', '確定要清除所有記憶嗎？此操作無法撤銷。',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.on_memory_command:
                self.on_memory_command('刪除所有記憶')
    
    def set_animation_state(self, state: str):
        """設置動畫狀態"""
        #print(f"設置動畫狀態: {state}")
        #print(f"   take_frames 數量: {len(self.take_frames) if hasattr(self, 'take_frames') else '屬性不存在'}")

        # 檢查是否有對應的動畫幀
        if state == PetAnimationState.WALKING and not self.walk_frames:
            QMessageBox.information(self, "提示", "沒有可用的走路動畫")
            return
        elif state == PetAnimationState.STUDYING and not self.study_frames:
            QMessageBox.information(self, "提示", "沒有可用的學習動畫")
            return
        elif state == PetAnimationState.TAKE and not self.take_frames:
            QMessageBox.information(self, "提示", "沒有可用的拖動動畫")
            return
            
        self.current_state = state
        self.frame_index = 0
        
        # 根據狀態設置移動行為
        if state == PetAnimationState.WALKING and not self.is_walking:
            # 只有在手動設置走路狀態時才開始自由移動
            self.is_walking = True
            self.move_timer.start(50)
        elif state != PetAnimationState.WALKING:
            self.is_walking = False
            self.move_timer.stop()
    
        if state == PetAnimationState.TAKE and self.take_frames:
                self.animation_timer.stop()
                self.take_animation_timer.start(50) 
        else:
                self.take_animation_timer.stop()
                if not self.animation_timer.isActive():
                    self.animation_timer.start(150)

    def update_take_animation(self):
        if self.current_state == PetAnimationState.TAKE and self.take_frames:
            self.frame_index = (self.frame_index + 1) % len(self.take_frames)
            self.label.setPixmap(self.take_frames[self.frame_index])

    def update_animation(self):
        """更新動畫幀"""
        if self.current_state == PetAnimationState.WALKING and self.walk_frames:
            frames = self.walk_frames
        elif self.current_state == PetAnimationState.STUDYING and self.study_frames:
            frames = self.study_frames
        elif self.current_state == PetAnimationState.TAKE and self.take_frames:
            frames = self.take_frames
            #self.frame_index += 10
        elif self.current_state == PetAnimationState.THROW and self.throw_frames:
            frames = self.throw_frames
        else:
            frames = self.idle_frames
        
        # 切換到下一幀
        if frames:

            self.frame_index = (self.frame_index + 1) % len(frames)
            self.label.setPixmap(frames[self.frame_index])
    
    def update_fall(self):
        """更新下落動畫"""
        if not self.is_falling:
            return
        
        # 重力加速度
        self.fall_speed += self.gravity
        self.y += self.fall_speed
        
        # 檢查是否著地
        screen = QApplication.primaryScreen().geometry()
        ground_y = screen.height() - self.height()
        
        if self.y >= ground_y:
            self.y = ground_y
            self.is_falling = False
            self.fall_speed = 0
            self.fall_timer.stop()
            
            # 回到待機狀態
            self.set_animation_state(PetAnimationState.IDLE)
        
        self.move(self.x, self.y)
    
    def start_falling(self):
        """開始下落"""
        if not self.is_falling:
            self.is_falling = True
            self.fall_speed = 0
            self.fall_timer.start(30)  # 30ms 更新一次，讓下落看起來流暢
    
    def mousePressEvent(self, event):
        """處理滑鼠按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            
            # 被拖拽時切換動畫 (TODO: 將來替換為Take資料夾)
            self.previous_state = self.current_state
            self.set_animation_state(PetAnimationState.TAKE)
            
            # 停止下落
            self.is_falling = False
            self.fall_timer.stop()
            
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """處理滑鼠移動事件（拖拽）"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            new_pos = event.globalPos() - self.drag_position
            self.move(new_pos)
            # 更新位置變數
            self.x = new_pos.x()
            self.y = new_pos.y()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """處理滑鼠釋放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            
            # 檢查是否需要下落
            screen = QApplication.primaryScreen().geometry()
            ground_y = screen.height() - self.height()
            
            if self.y < ground_y:
                # 開始下落
                self.start_falling()
            else:
                # 已經在地面，回到之前的狀態
                self.set_animation_state(self.previous_state)
                
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
        # 停止所有模式
        self._stop_study_mode()
        self._stop_focus_mode()
        
        if self.on_exit_request:
            self.on_exit_request()
        event.accept()
    
    def show_confirm_dialog(self, message: str) -> bool:
        """顯示一個確認對話框並返回使用者的選擇 (True=是, False=否)"""
        reply = QMessageBox.question(
            self,
            "專注模式",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes


def load_animation_frames(folder_path: str) -> List[str]:
    """載入動畫幀圖片路徑"""
    print(f"🔍 載入動畫資料夾: {folder_path}")
    
    if not os.path.exists(folder_path):
        print(f"❌ 資料夾不存在: {folder_path}")
        return []
    
    
    all_files = os.listdir(folder_path)
    #print(f"📁 資料夾中所有檔案: {all_files}")
    
    image_files = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    #print(f"🖼️ 過濾後的圖片檔案: {image_files}")
    
    image_files.sort()  # 按檔名排序
    #print(f"📋 排序後的圖片檔案: {image_files}")
    
    full_paths = [os.path.join(folder_path, img) for img in image_files]
    print(f"📍 完整路徑: {full_paths}")
    
    return full_paths


def validate_image_folders(idle_folder: str, walk_folder: str = None, study_folder: str = None, 
                          take_folder: str = None, throw_folder: str = None) -> tuple:
    """驗證圖片資料夾"""
    idle_images = load_animation_frames(idle_folder)
    walk_images = load_animation_frames(walk_folder) if walk_folder else []
    study_images = load_animation_frames(study_folder) if study_folder else []
    take_images = load_animation_frames(take_folder) if take_folder else []
    throw_images = load_animation_frames(throw_folder) if throw_folder else []
    
    errors = []
    
    if not idle_images:
        errors.append(f"找不到待機動畫圖片在資料夾: {idle_folder}")
    
    if walk_folder and not walk_images:
        errors.append(f"找不到走路動畫圖片在資料夾: {walk_folder}")
    
    # 其他資料夾是可選的，不強制要求
    if study_folder and not study_images:
        print(f"⚠️ 找不到學習動畫圖片在資料夾: {study_folder}，將使用Walk動畫代替")
    
    if take_folder and not take_images:
        print(f"⚠️ 找不到拖拽動畫圖片在資料夾: {take_folder}，將使用Walk動畫代替")
    
    if throw_folder and not throw_images:
        print(f"⚠️ 找不到拋擲動畫圖片在資料夾: {throw_folder}，將使用Walk動畫代替")
    
    return idle_images, walk_images, take_images, errors