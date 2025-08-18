"""
視窗管理模塊
處理究極專注模式的視窗檢測和管理
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
        
        def close_window(self, window_info: WindowInfo) -> bool:
            """關閉指定視窗"""
            try:
                # 先嘗試友好地關閉
                win32gui.PostMessage(window_info.hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.5)
                
                # 檢查是否還存在
                if win32gui.IsWindow(window_info.hwnd) and win32gui.IsWindowVisible(window_info.hwnd):
                    # 強制關閉
                    win32gui.DestroyWindow(window_info.hwnd)
                
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
            print("⚠️ 當前平台不支援完整的視窗管理功能")
        
        def get_visible_windows(self) -> List[WindowInfo]:
            """獲取可見視窗（簡化版）"""
            return []
        
        def close_window(self, window_info: WindowInfo) -> bool:
            """關閉視窗（簡化版）"""
            return False
        
        def minimize_window(self, window_info: WindowInfo) -> bool:
            """最小化視窗（簡化版）"""
            return False
        
        def move_window(self, window_info: WindowInfo, x: int, y: int) -> bool:
            """移動視窗（簡化版）"""
            return False


class FocusModeHandler:
    """專注模式處理器 - 改進版"""
    def __init__(self, pet_widget):
        self.pet_widget = pet_widget
        self.window_manager = WindowManager()
        self.last_check_time = 0
        self.check_interval = 3 # 秒
        # 僅處理列表中指定的應用程式
        self.target_list = {'chrome.exe', 'msedge.exe', 'brave.exe'}
        # 新增已忽略的視窗列表，避免重複詢問
        self.ignored_windows = set()

    def check_and_handle_distracting_windows(self):
        """檢查並處理分心視窗"""
        if not self.should_check_windows():
            return False
            
        windows = self.window_manager.get_visible_windows()
        
        # 遍歷所有非當前應用程式的視窗
        for window in windows:
            # 排除桌寵自己的視窗
            if window.title == self.pet_widget.windowTitle():
                continue
            
            # 僅處理目標列表中的應用程式
            if window.process_name.lower() not in self.target_list:
                print(f"✅ 視窗 '{window.title}' 不在目標列表中，跳過。")
                continue
            
            # 如果這個視窗已經被忽略過，則跳過
            if window.hwnd in self.ignored_windows:
                print(f"✅ 視窗 '{window.title}' 已被使用者忽略，跳過。")
                continue
            
            # 偵測到需要處理的視窗
            print(f"⚠️ 偵測到目標視窗：'{window.title}'")
            left, top, right, bottom = window.rect
            window_center_x = left + (right - left) // 2
            
            # 詢問使用者，並根據回答決定是否要處理
            reply_is_yes = self.pet_widget.show_confirm_dialog(f"這是寫作業會用到的嗎？\n(應用程式: {window.title})")
            
            if not reply_is_yes: # 使用者選擇「否」
                print("❌ 使用者選擇否，開始處理視窗")
                
                # 決定桌寵要走向的位置
                screen = QApplication.primaryScreen().geometry()
                pet_width = self.pet_widget.width()
                pet_height = self.pet_widget.height()
                
                if self.pet_widget.pos().x() < window_center_x:
                    target_x = max(0, left - pet_width)
                else:
                    target_x = min(screen.width() - pet_width, right)
                target_y = min(screen.height() - pet_height, bottom)

                self.pet_widget._walk_to_window_and_throw(target_x, target_y, window)
                return True
            else: # 使用者選擇「是」
                print("✅ 使用者選擇是，將此視窗加入忽略列表")
                self.ignored_windows.add(window.hwnd) # 將視窗句柄加入忽略列表
                
        self.last_check_time = time.time()
        return False
    
    def should_check_windows(self) -> bool:
        """判斷是否需要檢查視窗"""
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval:
            self.last_check_time = current_time
            return True
        return False
    
    
    
    def _filter_target_windows(self, windows: List[WindowInfo]) -> List[WindowInfo]:
        """篩選需要處理的目標視窗 - 改進版"""
        target_windows = []
        
        # 定義分心應用程式關鍵字（更全面）
        distracting_keywords = [
            # 瀏覽器
            'chrome', 'firefox', 'edge', 'browser', 'opera', 'safari',
            # 影片娛樂
            'youtube', 'netflix', 'twitch', 'bilibili', 'disney',
            # 遊戲
            'game', 'steam', 'epic', 'origin', 'uplay', 'battle.net',
            # 社交軟體
            'discord', 'telegram', 'wechat', 'line', 'whatsapp', 
            'facebook', 'instagram', 'tiktok', 'twitter', 'weibo',
            # 其他娛樂
            'spotify', 'music', 'video', 'vlc', 'media'
        ]
        
        # 排除的程式（不應該被關閉的）
        excluded_processes = {
            'python.exe', 'pythonw.exe', 'explorer.exe', 'dwm.exe',
            'taskmgr.exe', 'notepad.exe', 'cmd.exe', 'powershell.exe',
            'code.exe', 'devenv.exe'  # 開發工具
        }
        
        print("🔍 開始篩選分心視窗...")
        
        for window in windows:
            # 跳過排除的程式
            if window.process_name.lower() in excluded_processes:
                continue
            
            # 跳過桌寵自己的視窗
            if 'python' in window.process_name.lower() and '計時器' in window.title:
                continue
            
            window_text = (window.title + " " + window.process_name).lower()
            print(f"🔍 檢查視窗: {window.title} ({window.process_name})")
            
            # 檢查是否包含分心關鍵字
            for keyword in distracting_keywords:
                if keyword in window_text:
                    print(f"🎯 發現分心視窗 (關鍵字: {keyword}): {window.title}")
                    target_windows.append(window)
                    break
        
        return target_windows
    
    def _handle_single_window(self, window_info: WindowInfo):
        """處理單個視窗 - 改進版"""
        print(f"🎯 開始處理分心視窗: {window_info.title}")
        
        try:
            # 獲取視窗位置
            left, top, right, bottom = window_info.rect
            window_width = right - left
            window_height = bottom - top
            
            print(f"📏 視窗尺寸: {window_width}x{window_height}")
            print(f"📍 視窗位置: ({left}, {top}) 到 ({right}, {bottom})")
            
            # 計算視窗中心點
            window_center_x = left + window_width // 2
            window_center_y = top + window_height // 2
            
            screen = QApplication.primaryScreen().geometry()
            print(f"📺 螢幕尺寸: {screen.width()}x{screen.height()}")
            
            # 決定桌寵要走向的位置（視窗的角落）
            # ...
            # 獲取螢幕尺寸
            screen = QApplication.primaryScreen().geometry()
            pet_width = self.pet_widget.width()
            pet_height = self.pet_widget.height()
            
            # 根據視窗與寵物的相對位置決定走向
            if window_center_x < self.pet_widget.x:
                # 視窗在桌寵左邊，走向視窗的左下角
                target_x = max(0, left - pet_width)
                target_y = min(screen.height() - pet_height, bottom)
                print("📍 目標：視窗左側")
            else:
                # 視窗在桌寵右邊，走向視窗的右下角
                target_x = min(screen.width() - pet_width, right)
                target_y = min(screen.height() - pet_height, bottom)
                print("📍 目標：視窗右側")
            # ...
            print(f"🎯 桌寵目標位置: ({target_x}, {target_y})")
            
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