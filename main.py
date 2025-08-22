"""
智能記憶桌面寵物主程式
整合所有模塊功能
"""

import sys
import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QMessageBox

# 導入自定義模塊
from memory_system import SmartChatbotWithMemory
from llm_api import LLMAPIManager, check_api_key
from desktop_pet import DesktopPet, validate_image_folders
from chat_dialog import ChatDialog, QuickChatDialog


class SmartDesktopPetApp:
    """智能桌面寵物應用程式主類"""
    
    def __init__(self):
        # 初始化各個組件
        self.memory_bot = None
        self.llm_manager = None
        self.pet_widget = None
        self.chat_dialog = None
        
        # 初始化各個模塊
        self._init_memory_system()
        self._init_llm_manager()
        self._init_pet_widget()
        
        print("🎉 智能桌面寵物初始化完成")
    
    def _init_memory_system(self):
        """初始化記憶系統"""
        try:
            print("正在初始化記憶系統...")
            self.memory_bot = SmartChatbotWithMemory()
            print("✅ 記憶系統初始化成功")
        except Exception as e:
            print(f"❌ 記憶系統初始化失敗: {e}")
            QMessageBox.critical(None, "錯誤", f"記憶系統初始化失敗：{str(e)}")
            sys.exit(1)
    
    def _init_llm_manager(self):
        """初始化LLM管理器"""
        try:
            self.llm_manager = LLMAPIManager()
            print("✅ LLM管理器初始化成功")
        except Exception as e:
            print(f"❌ LLM管理器初始化失敗: {e}")
            self.llm_manager = None
    
    def _init_pet_widget(self):
        """初始化桌寵界面"""
        try:
            # 載入動畫資源
            idle_images, walk_images, take_images, errors = validate_image_folders("Idle", "Walk", take_folder="Take")
            
            if errors:
                for error in errors:
                    print(f"⚠️ {error}")
                if not idle_images:
                    QMessageBox.critical(None, "錯誤", "找不到必要的待機動畫圖片！\n請確保 'Idle' 資料夾存在並包含圖片。")
                    sys.exit(1)

            
            # 創建桌寵
            self.pet_widget = DesktopPet(idle_images, walk_images = walk_images,take_images=take_images)
            
            # 設置回調函數
            self.pet_widget.set_callbacks(
                on_chat=self._open_chat_dialog,
                on_quick_chat=self._handle_quick_chat,
                on_memory_command=self._handle_memory_command,
                on_exit=self._handle_exit
            )
            
            print("✅ 桌寵界面初始化成功")
            
        except Exception as e:
            print(f"❌ 桌寵界面初始化失敗: {e}")
            QMessageBox.critical(None, "錯誤", f"桌寵界面初始化失敗：{str(e)}")
            sys.exit(1)
    
    def _open_chat_dialog(self):
        """開啟對話視窗"""
        try:
            if self.chat_dialog is None:
                self.chat_dialog = ChatDialog(self.pet_widget)
                self.chat_dialog.set_callbacks(
                    on_send_message=self._handle_chat_message,
                    on_show_memories=lambda: self._handle_memory_command('列出記憶'),
                    on_show_stats=lambda: self._handle_memory_command('記憶統計')
                )
            
            self.chat_dialog.show()
            self.chat_dialog.raise_()
            self.chat_dialog.activateWindow()
            
        except Exception as e:
            print(f"開啟對話視窗失敗: {e}")
            QMessageBox.critical(self.pet_widget, "錯誤", f"開啟對話視窗失敗：{str(e)}")
    
    def _handle_quick_chat(self):
        """處理快速對話"""
        try:
            user_input = QuickChatDialog.get_user_input(self.pet_widget)
            if user_input:
                self._send_to_llm(user_input, is_quick_chat=True)
        except Exception as e:
            print(f"快速對話失敗: {e}")
            QMessageBox.critical(self.pet_widget, "錯誤", f"快速對話失敗：{str(e)}")
    
    def _handle_chat_message(self, user_input: str):
        """處理對話訊息"""
        try:
            self._send_to_llm(user_input, is_quick_chat=False)
        except Exception as e:
            print(f"處理對話訊息失敗: {e}")
            if self.chat_dialog:
                self.chat_dialog.show_error(f"處理訊息時發生錯誤：{str(e)}")
    
    def _handle_memory_command(self, command: str):
        """處理記憶管理命令"""
        try:
            result, llm_context, relevant_memories = self.memory_bot.process_input(command)
            
            if result['has_response']:
                # 在對話視窗中顯示結果
                if self.chat_dialog and self.chat_dialog.isVisible():
                    self.chat_dialog.add_system_message(result['response'])
                else:
                    # 如果對話視窗沒開，用訊息框顯示
                    QMessageBox.information(self.pet_widget, "記憶管理", result['response'])
            
        except Exception as e:
            error_msg = f"記憶管理出錯：{str(e)}"
            print(error_msg)
            QMessageBox.critical(self.pet_widget, "錯誤", error_msg)
    
    def _send_to_llm(self, user_input: str, is_quick_chat: bool = False):
        """發送訊息給LLM"""
        if not self.llm_manager:
            error_msg = "LLM服務不可用"
            self._show_error_response(error_msg, is_quick_chat)
            return
        
        if not check_api_key():
            error_msg = "未設置API Key，無法與LLM對話"
            self._show_error_response(error_msg, is_quick_chat)
            return
        
        if self.llm_manager.is_busy():
            error_msg = "桌寵還在思考中，請稍等..."
            self._show_error_response(error_msg, is_quick_chat)
            return
        
        try:
            # 使用記憶系統處理用戶輸入
            result, llm_context, relevant_memories = self.memory_bot.process_input(user_input)
            
            # 如果系統已經有回應（如記憶管理命令），直接顯示
            if result['has_response']:
                self._show_system_response(result['response'], is_quick_chat)
                return
            
            # 顯示記憶資訊（調試用）
            if relevant_memories:
                print(f"🧠 找到 {len(relevant_memories)} 條相關記憶:")
                for memory in relevant_memories:
                    print(f"   - {memory['text'][:50]}...")
            
            if result['memory_action'] == 'add':
                print(f"💾 新增記憶 ID: {result['memory_id']}")
            
            # 發送到LLM
            success = self.llm_manager.send_request(
                user_input=user_input,
                context=llm_context,
                on_success=lambda response: self._handle_llm_success(response, is_quick_chat),
                on_error=lambda error: self._handle_llm_error(error, is_quick_chat)
            )
            
            if not success:
                self._show_error_response("啟動LLM請求失敗", is_quick_chat)
            
        except Exception as e:
            error_msg = f"處理輸入時發生錯誤：{str(e)}"
            print(error_msg)
            self._show_error_response(error_msg, is_quick_chat)
    
    def _handle_llm_success(self, response: str, is_quick_chat: bool):
        """處理LLM成功回應"""
        try:
            if is_quick_chat:
                # 快速對話用訊息框顯示
                msg = QMessageBox(self.pet_widget)
                msg.setWindowTitle("桌寵的回應")
                msg.setText(response)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet("QLabel{min-width: 400px; max-width: 600px;}")
                msg.exec_()
            else:
                # 對話視窗更新
                if self.chat_dialog and self.chat_dialog.isVisible():
                    self.chat_dialog.update_last_pet_message(response)
                else:
                    # 備用顯示方式
                    msg = QMessageBox(self.pet_widget)
                    msg.setWindowTitle("桌寵的回應")
                    msg.setText(response)
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.setStyleSheet("QLabel{min-width: 400px; max-width: 600px;}")
                    msg.exec_()
        except Exception as e:
            print(f"處理LLM回應失敗: {e}")
    
    def _handle_llm_error(self, error: str, is_quick_chat: bool):
        """處理LLM錯誤"""
        error_text = f"抱歉，我現在無法回應：{error}"
        self._show_error_response(error_text, is_quick_chat)
    
    def _show_system_response(self, response: str, is_quick_chat: bool):
        """顯示系統回應"""
        if is_quick_chat:
            QMessageBox.information(self.pet_widget, "系統訊息", response)
        else:
            if self.chat_dialog and self.chat_dialog.isVisible():
                self.chat_dialog.update_last_pet_message(response)
            else:
                QMessageBox.information(self.pet_widget, "系統訊息", response)
    
    def _show_error_response(self, error_msg: str, is_quick_chat: bool):
        """顯示錯誤回應"""
        if is_quick_chat:
            QMessageBox.critical(self.pet_widget, "錯誤", error_msg)
        else:
            if self.chat_dialog and self.chat_dialog.isVisible():
                self.chat_dialog.show_error(error_msg)
            else:
                QMessageBox.critical(self.pet_widget, "錯誤", error_msg)
    
    def _handle_exit(self):
        """處理退出請求"""
        try:
            print("正在保存記憶系統...")
            if self.memory_bot:
                self.memory_bot._save_memory()
            print("記憶系統已保存")
            
            if self.chat_dialog:
                self.chat_dialog.close()
            
            QApplication.quit()
            
        except Exception as e:
            print(f"退出時發生錯誤: {e}")
            QApplication.quit()
    
    def show(self):
        """顯示桌寵"""
        if self.pet_widget:
            self.pet_widget.show()
    
    def get_memory_stats(self):
        """獲取記憶統計"""
        if self.memory_bot:
            return self.memory_bot.get_stats()
        return {"total": 0, "active": 0, "deleted": 0}


def main():
    """主函數"""
    app = QApplication(sys.argv)
    
    # 載入環境變數
    load_dotenv()
    
    # 檢查API Key（警告而不是阻止運行）
    if not check_api_key():
        QMessageBox.warning(None, "警告", 
                          "找不到 LLM_API_KEY 環境變數！\n"
                          "請在 .env 檔案中設置你的API Key。\n"
                          "桌寵仍可正常顯示，但無法與LLM對話。\n"
                          "記憶系統功能仍可正常使用。")
    
    # 檢查記憶系統依賴
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ 記憶系統依賴檢查完成")
    except ImportError:
        QMessageBox.warning(None, "警告", 
                          "記憶系統依賴未完整安裝！\n"
                          "請執行：pip install sentence-transformers faiss-cpu\n"
                          "桌寵將使用簡化的記憶功能。")
    
    try:
        # 創建並啟動應用程式
        pet_app = SmartDesktopPetApp()
        pet_app.show()
        
        # 顯示啟動資訊
        stats = pet_app.get_memory_stats()
        print("\n" + "="*50)
        print("🐾 智能記憶桌面寵物已啟動")
        print("="*50)
        print("💡 使用說明：")
        print("   - 左鍵拖曳：移動桌寵位置") 
        print("   - 右鍵點擊：開啟功能選單")
        print("   - 可以說 '記住我叫小明' 來儲存資訊")
        print("   - 可以問 '我叫什麼名字？' 來測試記憶")
        print("   - 支援刪除記憶、查看記憶等功能")
        print(f"📊 當前記憶統計：活躍記憶 {stats['active']} 條，總記憶 {stats['total']} 條")
        print("="*50)
        
        # 運行應用程式
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ 應用程式啟動失敗: {e}")
        QMessageBox.critical(None, "嚴重錯誤", f"應用程式啟動失敗：{str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()