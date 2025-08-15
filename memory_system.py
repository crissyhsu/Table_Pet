"""
智能記憶聊天機器人系統
整合記憶存儲、搜索、刪除和自動檢測功能

依賴套件:
pip install sentence-transformers faiss-cpu numpy pickle-mixin

如需 GPU 加速：
pip install faiss-gpu
"""

import os
import re
import time
import json
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from sentence_transformers import SentenceTransformer

try:
    import faiss
except ImportError:
    print("請安裝 faiss: pip install faiss-cpu")
    raise


class AdvancedMemorySystem:
    """進階記憶系統 - 支援向量檢索和記憶管理"""
    
    def __init__(self, embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        print(f"初始化記憶系統，載入模型: {embedding_model_name}")
        self.model = SentenceTransformer(embedding_model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)
        self.memories = []
        self.metadata = []
        self.memory_ids = []
        self.next_id = 0
        self.deleted_ids = set()
        
    def add_memory(self, text: str, metadata: Dict = None) -> int:
        """添加記憶並返回記憶 ID"""
        if not text.strip():
            return -1
            
        embedding = self.model.encode([text])
        self.index.add(embedding.astype('float32'))
        
        memory_id = self.next_id
        self.memories.append(text)
        
        # 添加時間戳
        if metadata is None:
            metadata = {}
        metadata['timestamp'] = metadata.get('timestamp', time.time())
        metadata['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        self.metadata.append(metadata)
        self.memory_ids.append(memory_id)
        self.next_id += 1
        
        return memory_id
    
    def delete_memory_by_id(self, memory_id: int) -> bool:
        """根據 ID 刪除記憶"""
        try:
            index_position = self.memory_ids.index(memory_id)
            self.deleted_ids.add(memory_id)
            self.memories[index_position] = "[DELETED]"
            self.metadata[index_position] = {
                "deleted": True, 
                "deleted_at": time.time(),
                "deleted_at_str": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            return True
        except ValueError:
            return False
    
    def delete_memories_by_content(self, search_text: str, threshold: float = 0.8) -> List[int]:
        """根據內容相似度刪除記憶"""
        deleted_ids = []
        similar_memories = self.search_memories(search_text, top_k=10, threshold=threshold)
        
        for memory in similar_memories:
            memory_idx = memory['index']
            memory_id = self.memory_ids[memory_idx]
            
            if self.delete_memory_by_id(memory_id):
                deleted_ids.append(memory_id)
        
        return deleted_ids
    
    def delete_memories_by_criteria(self, criteria: Dict) -> List[int]:
        """根據元資料條件刪除記憶"""
        deleted_ids = []
        
        for memory_id, metadata in zip(self.memory_ids, self.metadata):
            if memory_id in self.deleted_ids:
                continue
                
            should_delete = True
            for key, value in criteria.items():
                if key not in metadata or metadata[key] != value:
                    should_delete = False
                    break
            
            if should_delete and self.delete_memory_by_id(memory_id):
                deleted_ids.append(memory_id)
        
        return deleted_ids
    
    def delete_recent_memories(self, hours: int = 24) -> List[int]:
        """刪除最近指定時間內的記憶"""
        cutoff_time = time.time() - (hours * 3600)
        deleted_ids = []
        
        for memory_id, metadata in zip(self.memory_ids, self.metadata):
            if memory_id in self.deleted_ids:
                continue
                
            if metadata.get('timestamp', 0) > cutoff_time:
                if self.delete_memory_by_id(memory_id):
                    deleted_ids.append(memory_id)
        
        return deleted_ids
    
    def cleanup_deleted_memories(self):
        """清理已刪除的記憶，重建索引"""
        if not self.deleted_ids:
            return
        
        valid_memories = []
        valid_metadata = []
        valid_ids = []
        
        for memory, metadata, memory_id in zip(self.memories, self.metadata, self.memory_ids):
            if memory_id not in self.deleted_ids and memory != "[DELETED]":
                valid_memories.append(memory)
                valid_metadata.append(metadata)
                valid_ids.append(memory_id)
        
        self.memories = valid_memories
        self.metadata = valid_metadata
        self.memory_ids = valid_ids
        self.deleted_ids.clear()
        
        # 重建 FAISS 索引
        self.index = faiss.IndexFlatIP(self.dimension)
        if self.memories:
            embeddings = self.model.encode(self.memories)
            self.index.add(embeddings.astype('float32'))
        
        print(f"清理完成，剩餘 {len(self.memories)} 條記憶")
    
    def search_memories(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """搜索記憶（排除已刪除的）"""
        if len(self.memories) == 0:
            return []
        
        query_embedding = self.model.encode([query])
        scores, indices = self.index.search(
            query_embedding.astype('float32'), 
            min(top_k * 2, len(self.memories))
        )
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= len(self.memories):
                continue
                
            memory_id = self.memory_ids[idx]
            
            if memory_id in self.deleted_ids or self.memories[idx] == "[DELETED]":
                continue
                
            if score >= threshold:
                results.append({
                    'id': memory_id,
                    'text': self.memories[idx],
                    'score': float(score),
                    'metadata': self.metadata[idx],
                    'index': idx
                })
                
                if len(results) >= top_k:
                    break
        
        return results
    
    def format_memories_for_prompt(self, memories: List[Dict]) -> str:
        """將記憶格式化為自然語言加入 prompt"""
        if not memories:
            return ""
        
        formatted_memories = []
        for memory in memories:
            formatted_memories.append(f"- {memory['text']}")
        
        return f"""
相關記憶：
{chr(10).join(formatted_memories)}

請基於以上記憶內容來回答問題。
"""
    
    def get_memory_stats(self) -> Dict:
        """取得記憶統計資訊"""
        total_memories = len(self.memory_ids)
        deleted_memories = len(self.deleted_ids)
        active_memories = total_memories - deleted_memories
        
        return {
            'total': total_memories,
            'active': active_memories,
            'deleted': deleted_memories,
            'cleanup_needed': deleted_memories > 0
        }
    
    def save_to_disk(self, filepath: str):
        """保存記憶系統到本地端"""
        try:
            # 保存 FAISS 索引
            faiss.write_index(self.index, f"{filepath}.index")
            
            # 保存其他資料
            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump({
                    'memories': self.memories,
                    'metadata': self.metadata,
                    'memory_ids': self.memory_ids,
                    'next_id': self.next_id,
                    'deleted_ids': self.deleted_ids
                }, f)
            
            print(f"記憶系統已保存到 {filepath}")
            
        except Exception as e:
            print(f"保存失敗: {e}")
    
    def load_from_disk(self, filepath: str):
        """從本地端載入記憶系統"""
        try:
            # 載入 FAISS 索引
            if os.path.exists(f"{filepath}.index"):
                self.index = faiss.read_index(f"{filepath}.index")
            
            # 載入其他資料
            if os.path.exists(f"{filepath}.pkl"):
                with open(f"{filepath}.pkl", 'rb') as f:
                    data = pickle.load(f)
                    self.memories = data.get('memories', [])
                    self.metadata = data.get('metadata', [])
                    self.memory_ids = data.get('memory_ids', [])
                    self.next_id = data.get('next_id', 0)
                    self.deleted_ids = data.get('deleted_ids', set())
                
                print(f"已載入 {len(self.memories)} 條記憶")
            
        except Exception as e:
            print(f"載入失敗: {e}")


class MemoryTriggerDetector:
    """記憶觸發檢測器 - 識別用戶是否要求記住內容"""
    
    def __init__(self):
        self.memory_keywords = {
            'explicit': [
                r'記住', r'記下', r'記錄', r'存起來', r'保存', r'儲存',
                r'記在', r'別忘記', r'不要忘記', r'記一下', r'記住這個',
                r'幫我記住', r'請記住', r'要記得', r'記得我',
                r'remember', r'save this', r'keep in mind', r'don\'t forget'
            ],
            'implicit': [
                r'我叫', r'我的名字是', r'我住在', r'我的生日是',
                r'我喜歡', r'我不喜歡', r'我的工作是', r'我是一個',
                r'提醒我', r'我告訴過你', r'我之前說過'
            ]
        }
        
        self.explicit_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.memory_keywords['explicit']
        ]
        self.implicit_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.memory_keywords['implicit']
        ]
    
    def detect_memory_request(self, text: str) -> Tuple[bool, str, Optional[str]]:
        """檢測是否需要記憶"""
        # 檢查明確的記憶請求
        for pattern in self.explicit_patterns:
            if pattern.search(text):
                return True, "explicit", self._extract_content_after_keyword(text, pattern)
        
        # 檢查隱含的記憶請求
        for pattern in self.implicit_patterns:
            if pattern.search(text):
                return True, "implicit", self._extract_personal_info(text, pattern)
        
        # 檢測特殊模式
        if self._detect_special_patterns(text):
            return True, "contextual", text
        
        return False, "none", None
    
    def _extract_content_after_keyword(self, text: str, pattern) -> str:
        """提取關鍵字後的內容"""
        match = pattern.search(text)
        if match:
            start_pos = match.end()
            content = text[start_pos:].strip()
            content = re.sub(r'^[：:，,。.！!？?]+', '', content).strip()
            return content if content else text
        return text
    
    def _extract_personal_info(self, text: str, pattern) -> str:
        """提取個人資訊"""
        return text
    
    def _detect_special_patterns(self, text: str) -> bool:
        """檢測特殊模式"""
        special_patterns = [
            r'我是.*，', r'我來自', r'我在.*工作',
            r'我比較喜歡', r'我通常', r'我習慣',
            r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{1,2}/\d{1,2}/\d{4}',
            r'\w+@\w+\.\w+', r'\+?\d{10,}'
        ]
        
        for pattern in special_patterns:
            if re.search(pattern, text):
                return True
        return False


class MemoryDeletionDetector:
    """記憶刪除檢測器 - 識別刪除請求"""
    
    def __init__(self):
        self.deletion_keywords = {
            'explicit': [
                r'刪除', r'刪掉', r'移除', r'忘記', r'忘掉', r'清除',
                r'去掉', r'別記得', r'不要記得', r'取消記憶',
                r'delete', r'remove', r'forget', r'erase', r'clear'
            ],
            'specific_patterns': [
                r'刪除.*記憶', r'忘記我說過.*', r'不要記得.*',
                r'清除.*資訊', r'刪掉.*內容', r'忘記我的.*'
            ]
        }
        
        self.deletion_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.deletion_keywords['explicit'] + self.deletion_keywords['specific_patterns']
        ]
    
    def detect_deletion_request(self, text: str) -> Dict:
        """檢測刪除請求"""
        result = {
            'is_deletion_request': False,
            'deletion_type': 'none',
            'target_content': None,
            'deletion_scope': 'none'
        }
        
        for pattern in self.deletion_patterns:
            match = pattern.search(text)
            if match:
                result['is_deletion_request'] = True
                result['deletion_type'] = 'explicit'
                
                target = self._extract_deletion_target(text, match)
                result['target_content'] = target
                
                if any(word in text.lower() for word in ['全部', '所有', 'all', 'everything']):
                    result['deletion_scope'] = 'all'
                elif any(word in text.lower() for word in ['最近', 'recent', '剛才', '今天']):
                    result['deletion_scope'] = 'recent'
                else:
                    result['deletion_scope'] = 'specific'
                
                break
        
        return result
    
    def _extract_deletion_target(self, text: str, match) -> Optional[str]:
        """提取要刪除的目標內容"""
        start_pos = match.end()
        remaining_text = text[start_pos:].strip()
        
        remaining_text = re.sub(r'^[關於about]*', '', remaining_text, flags=re.IGNORECASE).strip()
        remaining_text = re.sub(r'^[：:，,。.！!？?]+', '', remaining_text).strip()
        
        return remaining_text if remaining_text else None


class SmartMemoryManager:
    """智能記憶管理器 - 統合所有記憶功能"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        self.memory_system = AdvancedMemorySystem(model_name)
        self.trigger_detector = MemoryTriggerDetector()
        self.deletion_detector = MemoryDeletionDetector()
        print("智能記憶管理器初始化完成")
    
    def should_remember(self, user_input: str) -> Dict:
        """判斷是否需要記憶"""
        should_remember, memory_type, content = self.trigger_detector.detect_memory_request(user_input)
        
        return {
            'should_remember': should_remember,
            'memory_type': memory_type,
            'extracted_content': content,
            'confidence': 0.9 if memory_type == 'explicit' else 0.7 if memory_type == 'implicit' else 0.6,
            'reason': 'keyword_detected' if should_remember else 'no_trigger'
        }
    
    def process_deletion_request(self, user_input: str) -> Dict:
        """處理刪除請求"""
        deletion_info = self.deletion_detector.detect_deletion_request(user_input)
        
        if not deletion_info['is_deletion_request']:
            return {'success': False, 'message': '未檢測到刪除請求'}
        
        deleted_count = 0
        deleted_ids = []
        
        if deletion_info['deletion_scope'] == 'all':
            deleted_ids = self._delete_all_memories()
            deleted_count = len(deleted_ids)
            message = f"已刪除所有 {deleted_count} 條記憶"
            
        elif deletion_info['deletion_scope'] == 'recent':
            deleted_ids = self.memory_system.delete_recent_memories(24)
            deleted_count = len(deleted_ids)
            message = f"已刪除最近 {deleted_count} 條記憶"
            
        elif deletion_info['target_content']:
            deleted_ids = self.memory_system.delete_memories_by_content(
                deletion_info['target_content'], 
                threshold=0.7
            )
            deleted_count = len(deleted_ids)
            message = f"已刪除 {deleted_count} 條與「{deletion_info['target_content']}」相關的記憶"
            
        else:
            return {'success': False, 'message': '無法確定要刪除的內容'}
        
        if deleted_count > 0:
            self.memory_system.cleanup_deleted_memories()
        
        return {
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'deleted_ids': deleted_ids
        }
    
    def _delete_all_memories(self) -> List[int]:
        """刪除所有記憶"""
        all_ids = [mid for mid in self.memory_system.memory_ids 
                  if mid not in self.memory_system.deleted_ids]
        
        for memory_id in all_ids:
            self.memory_system.delete_memory_by_id(memory_id)
        
        return all_ids
    
    def list_memories(self, limit: int = 10) -> List[Dict]:
        """列出當前的記憶"""
        memories = []
        count = 0
        
        for memory_id, memory, metadata in zip(
            self.memory_system.memory_ids, 
            self.memory_system.memories, 
            self.memory_system.metadata
        ):
            if memory_id not in self.memory_system.deleted_ids and memory != "[DELETED]":
                memories.append({
                    'id': memory_id,
                    'text': memory[:100] + "..." if len(memory) > 100 else memory,
                    'timestamp': metadata.get('created_at', 'unknown'),
                    'type': metadata.get('type', 'unknown')
                })
                count += 1
                if count >= limit:
                    break
        
        return memories


class SmartChatbotWithMemory:
    """智能記憶聊天機器人"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', memory_file='chatbot_memory'):
        self.memory_manager = SmartMemoryManager(model_name)
        self.memory_file = memory_file
        
        # 嘗試載入現有記憶
        try:
            self.memory_manager.memory_system.load_from_disk(self.memory_file)
            print("已載入現有記憶系統")
        except:
            print("建立新的記憶系統")
    
    def process_input(self, user_input: str, return_memories: bool = False) -> Union[str, Tuple[str, List[Dict]]]:
        """
        處理用戶輸入
        
        Args:
            user_input: 用戶輸入文字
            return_memories: 是否返回相關記憶
            
        Returns:
            如果 return_memories=False: 返回回應字串
            如果 return_memories=True: 返回 (回應字串, 相關記憶列表)
        """
        user_input = user_input.strip()
        
        # 1. 檢查刪除請求
        deletion_result = self.memory_manager.process_deletion_request(user_input)
        if deletion_result['success']:
            self._save_memory()
            if return_memories:
                return deletion_result['message'], []
            return deletion_result['message']
        
        # 2. 檢查特殊指令
        if user_input.lower() in ['列出記憶', 'list memories', '顯示記憶', '記憶列表']:
            memories = self.memory_manager.list_memories()
            if not memories:
                message = "目前沒有任何記憶。"
            else:
                memory_list = "\n".join([
                    f"[ID:{m['id']}] {m['timestamp']} - {m['text']}" 
                    for m in memories
                ])
                message = f"當前記憶:\n{memory_list}"
            
            if return_memories:
                return message, memories
            return message
        
        if user_input.lower() in ['記憶統計', 'memory stats', '統計']:
            stats = self.memory_manager.memory_system.get_memory_stats()
            message = (f"📊 記憶統計:\n"
                      f"活躍記憶: {stats['active']}\n"
                      f"已刪除: {stats['deleted']}\n"
                      f"總計: {stats['total']}\n"
                      f"需要清理: {'是' if stats['cleanup_needed'] else '否'}")
            
            if return_memories:
                return message, []
            return message
        
        if user_input.lower() in ['清理記憶', 'cleanup', '整理']:
            self.memory_manager.memory_system.cleanup_deleted_memories()
            message = "記憶清理完成！"
            if return_memories:
                return message, []
            return message
        
        # 3. 檢測記憶請求
        memory_decision = self.memory_manager.should_remember(user_input)
        
        # 4. 搜索相關記憶
        relevant_memories = self.memory_manager.memory_system.search_memories(
            user_input, top_k=3, threshold=0.6
        )
        
        # 5. 格式化記憶內容
        memory_context = self.memory_manager.memory_system.format_memories_for_prompt(relevant_memories)
        
        # 6. 建構完整 prompt
        full_prompt = f"""
{memory_context}

用戶問題：{user_input}

請回答：
"""
        
        # 7. 調用語言模型（這裡需要你自己實現）
        response = self.call_language_model(full_prompt, user_input, relevant_memories)
        
        # 8. 根據檢測結果決定是否記憶
        if memory_decision['should_remember']:
            memory_content = memory_decision['extracted_content'] or user_input
            
            # 存儲記憶
            memory_id = self.memory_manager.memory_system.add_memory(
                memory_content,
                metadata={
                    'type': memory_decision['memory_type'],
                    'confidence': memory_decision['confidence'],
                    'reason': memory_decision['reason'],
                    'original_input': user_input
                }
            )
            
            # 添加確認訊息
            if memory_decision['memory_type'] == 'explicit':
                response += f"\n\n✅ 已記住 (ID:{memory_id}): {memory_content}"
            
            self._save_memory()
        
        # 9. 根據參數決定返回格式
        if return_memories:
            return response, relevant_memories
        return response
    
    def get_relevant_memories(self, user_input: str, top_k: int = 3, threshold: float = 0.6) -> List[Dict]:
        """
        獲取與輸入最相關的記憶
        
        Args:
            user_input: 用戶輸入
            top_k: 返回最相關的記憶數量
            threshold: 相似度閾值
            
        Returns:
            相關記憶列表，每個記憶包含 id, text, score, metadata 等資訊
        """
        return self.memory_manager.memory_system.search_memories(user_input, top_k, threshold)
    
    def add_memory_manually(self, content: str, metadata: Dict = None) -> int:
        """
        手動添加記憶
        
        Args:
            content: 記憶內容
            metadata: 元資料
            
        Returns:
            記憶 ID
        """
        memory_id = self.memory_manager.memory_system.add_memory(content, metadata)
        self._save_memory()
        return memory_id
    
    def delete_memory_by_id(self, memory_id: int) -> bool:
        """
        根據 ID 刪除記憶
        
        Args:
            memory_id: 記憶 ID
            
        Returns:
            是否刪除成功
        """
        success = self.memory_manager.memory_system.delete_memory_by_id(memory_id)
        if success:
            self._save_memory()
        return success
    
    def search_and_format_memories(self, user_input: str, top_k: int = 3) -> str:
        """
        搜索記憶並格式化為可用於 prompt 的字串
        
        Args:
            user_input: 用戶輸入
            top_k: 最多返回的記憶數量
            
        Returns:
            格式化的記憶字串，可直接加入 prompt
        """
        memories = self.get_relevant_memories(user_input, top_k)
        return self.memory_manager.memory_system.format_memories_for_prompt(memories)
    
    def call_language_model(self, prompt: str, user_input: str, memories: List[Dict]) -> str:
        """
        調用語言模型生成回應
        注意：這是一個範例實現，你需要根據使用的模型 API 來修改
        """
        # 這裡可以整合不同的語言模型 API
        # 例如：OpenAI GPT, Anthropic Claude, 或本地模型
        
        # 範例回應生成（實際使用時請替換為真實的模型調用）
        if memories:
            response = f"根據我的記憶，我了解到相關資訊。關於「{user_input}」，"
        else:
            response = f"關於「{user_input}」，"
        
        # 簡單的回應邏輯範例
        if "你好" in user_input or "hello" in user_input.lower():
            response += "你好！很高興與你對話。"
        elif "謝謝" in user_input or "thank" in user_input.lower():
            response += "不客氣！有什麼其他需要幫助的嗎？"
        else:
            response += "我正在處理你的問題。請注意，這是一個範例回應，實際使用時需要整合真實的語言模型。"
        
        return response
    
    def _save_memory(self):
        """保存記憶到磁碟"""
        try:
            self.memory_manager.memory_system.save_to_disk(self.memory_file)
        except Exception as e:
            print(f"保存記憶失敗: {e}")
    
    def chat_loop(self):
        """開始聊天循環"""
        print("🤖 智能記憶聊天機器人已啟動！")
        print("💡 提示：")
        print("   - 說「列出記憶」查看所有記憶")
        print("   - 說「記憶統計」查看統計資訊") 
        print("   - 說「刪除記憶」或「忘記...」來刪除記憶")
        print("   - 說「退出」結束對話")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n你: ").strip()
                
                if user_input.lower() in ['退出', 'quit', 'exit', 'bye']:
                    print("👋 再見！")
                    break
                
                if not user_input:
                    continue
                
                response = self.process_input(user_input)
                print(f"\n🤖: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 聊天已中斷，再見！")
                break
            except Exception as e:
                print(f"❌ 發生錯誤: {e}")


def main():
    """主程式入口"""
    print("正在初始化智能記憶聊天機器人...")
    
    # 建立聊天機器人實例
    chatbot = SmartChatbotWithMemory()
    
    # 開始聊天
    chatbot.chat_loop()


if __name__ == "__main__":
    main()