"""
視窗管理模塊
處理究級專注模式的視窗檢測和管理
"""

import sys
import time
from typing import List, Dict, Tuple
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QRect

# Windows平台的視窗管理
if sys.platform == "win32":
    import win32gui
    import win32process
    import win32api
    import win32con
    
    class WindowInfo:
        """視窗資訊類"""
        def __init__(self, hwnd: int, title: str, rect: tuple, process_name: str):
            self.hwnd = hwnd
            self.title = title
            self.rect = rect  # (left, top, right, bottom)
            self.process_name = process_name
        
        def get_center(self) -> Tuple[int, int]:
            """獲取視窗中心點"""
            left, top, right, bottom = self.rect
            return ((left + right) // 2, (top + bottom) // 2)
        
        def get_bottom_left(self) -> Tuple[int, int]:
            """獲取視窗左下角"""
            left, top, right, bottom = self.rect
            return (left, bottom)
        
        def get_bottom_right(self) -> Tuple[int, int]:
            """獲取視窗右下角"""
            left, top, right, bottom = self.rect
            return (right, bottom)
    
    class WindowManager:
        """Windows平台視窗管理器"""
        
        def __init__(self):
            self.excluded_processes = {
                'dwm.exe', 'explorer.exe', 'winlogon.exe', 
                'python.exe', 'pythonw.exe', 'taskmgr.exe',
                'cmd.exe', 'conhost.exe', 'dllhost.exe'
            }
            self.excluded_titles = {
                'Program Manager', 'Desktop', 'Task Switching'
            }
        
        def enum_windows_callback(self, hwnd, windows_list):
            """枚舉視窗的回調函數"""
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            # 獲取視窗標題
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title or window_title in self.excluded_titles:
                return True
            
            # 獲取視窗矩形
            try:
                rect = win32gui.GetWindowRect(hwnd)
                if rect[2] - rect[0] < 100 or rect[3] - rect[1] < 100:  # 忽略太小的視窗
                    return True
            except:
                return True
            
            # 獲取進程資訊
            try:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                process_handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, process_id)
                process_name = win32process.GetModuleFileNameEx(process_handle, 0).split('\\')[-1]
                win32api.CloseHandle(process_handle)
                
                if process_name.lower() in self.excluded_processes:
                    return True
                
            except:
                process_name = "unknown"
            
            # 添加到列表
            window_info = WindowInfo(hwnd, window_title, rect, process_name)
            windows_list.append(window_info)
            
            return True
        
        def get_visible_windows(self) -> List[WindowInfo]:
            """獲取所有可見的應用程式視窗"""
            windows_list = []
            try:
                win32gui.EnumWindows(self.enum_windows_callback, windows_list)
            except Exception as e:
                print(f"枚舉視窗時發生錯誤: {e}")
            
            return windows_list
        
        def close_window(self, hwnd: int) -> bool:
            """關閉指定視窗 - 修正版本"""
            try:
                # 先嘗試友好地關閉
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.5)
                
                # 檢查是否還存在
                if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                    # 強制關閉
                    win32gui.DestroyWindow(hwnd)
                
                return True
            except Exception as e:
                print(f"關閉視窗失敗: {e}")
                return False
        
        def minimize_window(self, window_info: WindowInfo) -> bool:
            """最小化視窗"""
            try:
                win32gui.ShowWindow(window_info.hwnd, win32con.SW_MINIMIZE)
                return True
            except Exception as e:
                print(f"最小化視窗失敗: {e}")
                return False
        
        def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
            """移動視窗位置"""
            try:
                left, top, right, bottom = window_info.rect
                width = right - left
                height = bottom - top
                win32gui.MoveWindow(window_info.hwnd, x, y, width, height, True)
                # 更新 window_info 的 rect
                window_info.rect = (x, y, x + width, y + height)
                return True
            except Exception as e:
                print(f"移動視窗失敗: {e}")
                return False

else:
    # 非Windows平台的簡化實現
    class WindowInfo:
        def __init__(self, hwnd: int, title: str, rect: tuple, process_name: str):
            self.hwnd = hwnd
            self.title = title
            self.rect = rect
            self.process_name = process_name
        
        def get_center(self) -> Tuple[int, int]:
            return (0, 0)
        
        def get_bottom_left(self) -> Tuple[int, int]:
            return (0, 0)
        
        def get_bottom_right(self) -> Tuple[int, int]:
            return (0, 0)
    
    class WindowManager:
        """非Windows平台的視窗管理器（簡化版）"""
        
        def __init__(self):
            print("⚠️ 當前平台不支持完整的視窗管理功能")
        
        def get_visible_windows(self) -> List[WindowInfo]:
            """獲取可見視窗（簡化版）"""
            return []
        
        def close_window(self, hwnd: int) -> bool:
            """關閉視窗（簡化版）"""
            return False
        
        def minimize_window(self, window_info: WindowInfo) -> bool:
            """最小化視窗（簡化版）"""
            return False
        
        def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
            """移動視窗（簡化版）"""
            return False


class FocusModeHandler:
    """專注模式處理器 - 修正版"""
    
    def __init__(self, pet_widget):
        self.pet_widget = pet_widget
        self.window_manager = WindowManager()
        self.last_check_time = 0
        self.check_interval = 3  # 秒
        # 僅處理列表中指定的應用程式
        self.target_processes = {
            'chrome.exe', 'msedge.exe', 'brave.exe', 'firefox.exe',
            'discord.exe', 'telegram.exe', 'line.exe', 'wechat.exe',
            'spotify.exe', 'vlc.exe', 'potplayer.exe','HoYoPlay.exe'
        }
        # 已忽略的視窗列表，避免重複詢問
        self.ignored_windows = set()
        # 已處理過的視窗，避免重複處理
        self.processed_windows = set()

    def should_check_windows(self) -> bool:
        """判斷是否需要檢查視窗"""
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval:
            self.last_check_time = current_time
            return True
        return False

    def check_and_handle_distracting_windows(self) -> bool:
        """檢查並處理分心視窗 - 修正版"""
        if not self.should_check_windows():
            return False
            
        windows = self.window_manager.get_visible_windows()
        print(f"🔍 檢測到 {len(windows)} 個視窗")
        
        # 遍歷所有視窗
        for window in windows:
            # 排除桌寵自己的視窗
            if 'python' in window.process_name.lower():
                continue
            
            # 僅處理目標列表中的應用程式
            if window.process_name.lower() not in self.target_processes:
                continue
            
            # 如果這個視窗已經被忽略過，則跳過
            if window.hwnd in self.ignored_windows:
                continue
                
            # 如果這個視窗已經處理過，則跳過
            if window.hwnd in self.processed_windows:
                continue
            
            # 檢測到需要處理的視窗
            print(f"⚠️ 檢測到目標視窗：'{window.title}' ({window.process_name})")
            
            # 詢問使用者
            reply_is_yes = self.pet_widget.show_confirm_dialog(
                f"這是寫作業會用到的嗎？\n(應用程式: {window.title})"
            )
            
            if reply_is_yes:  # 使用者選擇「是」
                print("✅ 使用者選擇是，將此視窗加入忽略列表")
                self.ignored_windows.add(window.hwnd)
            else:  # 使用者選擇「否」
                print("❌ 使用者選擇否，開始處理視窗")
                self.processed_windows.add(window.hwnd)
                self._handle_single_window(window)
                return True
                
        return False
    
    def _handle_single_window(self, window_info: WindowInfo):
        """處理單個視窗 - 修正版"""
        print(f"🎯 開始處理分心視窗: {window_info.title}")
        
        try:
            # 獲取視窗位置
            left, top, right, bottom = window_info.rect
            window_center_x = (left + right) // 2
            
            # 獲取螢幕尺寸
            screen = QApplication.primaryScreen().geometry()
            pet_width = self.pet_widget.width()
            pet_height = self.pet_widget.height()
            
            # 根據桌寵與視窗的相對位置決定走向
            if self.pet_widget.pos().x() < window_center_x:
                # 桌寵在視窗左邊，走向視窗左側
                target_x = max(0, left - pet_width - 20)  # 確保不走出螢幕
                print("📍 目標：視窗左側")
            else:
                # 桌寵在視窗右邊，走向視窗右側
                target_x = min(screen.width() - pet_width, right + 20)  # 確保不走出螢幕
                print("📍 目標：視窗右側")
            
            # Y軸位置設在視窗底部附近
            target_y = min(screen.height() - pet_height, bottom - 50)
            
            print(f"🎯 桌寵目標位置: ({target_x}, {target_y})")
            print(f"📏 螢幕範圍: {screen.width()}x{screen.height()}")
            
            # 桌寵開始行動
            self.pet_widget._walk_to_window_and_throw(target_x, target_y, window_info)
            
        except Exception as e:
            print(f"❌ 處理視窗時發生錯誤: {e}")
            import traceback
            traceback.print_exc()


def get_screen_bounds() -> QRect:
    """獲取螢幕邊界"""
    screen = QApplication.primaryScreen().geometry()
    return QRect(0, 0, screen.width(), screen.height())