"""
智能記憶聊天機器人系統 - 改進版
整合記憶儲存、搜索、刪除和自動檢測功能

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
import jieba

try:
    import faiss
except ImportError:
    print("請安裝 faiss: pip install faiss-cpu")
    # 為了不讓整個程式崩潰，我們提供一個假的替代實現
    class MockFaiss:
        class IndexFlatIP:
            def __init__(self, dimension):
                self.dimension = dimension
                self.data = []
            def add(self, embedding):
                self.data.append(embedding[0])
            def search(self, query, k):
                if not self.data:
                    return np.array([[0.0]]), np.array([[0]])
                # 簡單的相似度計算
                scores = []
                for i, vec in enumerate(self.data):
                    if len(vec) == len(query[0]):
                        score = np.dot(query[0], vec) / (np.linalg.norm(query[0]) * np.linalg.norm(vec))
                        scores.append((score, i))
                scores.sort(reverse=True)
                scores = scores[:k]
                return (np.array([[s[0] for s in scores]]), 
                       np.array([[s[1] for s in scores]]))
        @staticmethod
        def write_index(index, filepath):
            with open(filepath, 'wb') as f:
                pickle.dump(index.data, f)
        @staticmethod
        def read_index(filepath):
            idx = MockFaiss.IndexFlatIP(768)  # 默認維度
            try:
                with open(filepath, 'rb') as f:
                    idx.data = pickle.load(f)
            except:
                pass
            return idx
    faiss = MockFaiss()


class AdvancedMemorySystem:
    """進階記憶系統 - 支援向量檢索和記憶管理"""
    
    def __init__(self, embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        print(f"初始化記憶系統，載入模型: {embedding_model_name}")
        try:
            self.model = SentenceTransformer(embedding_model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"無法載入嵌入模型: {e}")
            print("使用簡化的文字比對模式")
            self.model = None
            self.dimension = 768
            
        self.index = faiss.IndexFlatIP(self.dimension)
        self.memories = []
        self.metadata = []
        self.memory_ids = []
        self.next_id = 0
        self.deleted_ids = set()
        
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """簡單的文字相似度計算（當沒有嵌入模型時使用）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 and not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
        
    def add_memory(self, text: str, metadata: Dict = None) -> int:
        """添加記憶並返回記憶 ID"""
        if not text.strip():
            return -1
            
        if self.model:
            embedding = self.model.encode([text])
            self.index.add(embedding.astype('float32'))
        else:
            # 使用假的嵌入向量
            fake_embedding = np.random.rand(1, self.dimension).astype('float32')
            self.index.add(fake_embedding)
        
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
            if self.model:
                embeddings = self.model.encode(self.memories)
                self.index.add(embeddings.astype('float32'))
            else:
                # 使用假的嵌入向量
                fake_embeddings = np.random.rand(len(self.memories), self.dimension).astype('float32')
                self.index.add(fake_embeddings)
        
        print(f"清理完成，剩餘 {len(self.memories)} 條記憶")
    
    def search_memories(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """搜索記憶（排除已刪除的）"""
        if len(self.memories) == 0:
            return []
        
        if self.model:
            query_embedding = self.model.encode([query])
            scores, indices = self.index.search(
                query_embedding.astype('float32'), 
                min(top_k * 2, len(self.memories))
            )
        else:
            # 使用簡單相似度計算
            similarities = []
            for i, memory in enumerate(self.memories):
                if self.memory_ids[i] not in self.deleted_ids and memory != "[DELETED]":
                    sim = self._simple_similarity(query, memory)
                    similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            scores = np.array([[s[0] for s in similarities[:min(top_k * 2, len(similarities))]]])
            indices = np.array([[s[1] for s in similarities[:min(top_k * 2, len(similarities))]]])
        
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


class SmartMemoryTriggerDetector:
    """智能記憶觸發檢測器 - 使用語義分析而非關鍵字匹配"""
    
    def __init__(self):
        # 個人資訊標識詞
        self.personal_indicators = {
            '身分': ['我叫', '我的名字', '我是', '我的職業', '我在', '我住在', '我來自'],
            '偏好': ['我喜歡', '我不喜歡', '我愛', '我討厭', '我傾向', '我偏好'],
            '狀態': ['我今年', '歲', '我現在', '我的生日', '我的年齡'],
            '經驗': ['我以前', '我曾經', '我記得', '我經歷過', '我做過'],
            '計畫': ['我打算', '我計劃', '我想要', '我希望', '提醒我', '記住我要'],
            '重要資訊': ['這很重要', '別忘記', '要記住', '記下來', '存起來']
        }
        
        # 查詢關鍵詞（這些通常不需要被記憶）
        self.query_indicators = [
            '什麼是', '怎麼', '為什麼', '在哪裡', '什麼時候', '誰是',
            '告訴我', '解釋', '說明', '幫我', '能不能', '可以嗎',
            '你會', '你是', '你的', '你能', '你可以', '你知道'
        ]
        
        # 明確記憶請求
        self.explicit_memory_requests = [
            '記住', '記下', '記錄', '保存', '儲存', '記住這個',
            '別忘記', '要記得', 'remember', 'save this', 'keep in mind'
        ]
    
    def detect_memory_request(self, text: str) -> Tuple[bool, str, Optional[str], float]:
        """
        檢測是否需要記憶 - 改進版使用多重判斷標準
        
        Returns:
            (should_remember, memory_type, extracted_content, confidence)
        """
        text = text.strip()
        
        # 1. 檢查是否為明確的查詢
        if self._is_query(text):
            return False, "query", None, 0.9
        
        # 2. 檢查明確記憶請求
        explicit_match = self._check_explicit_memory_request(text)
        if explicit_match:
            return True, "explicit", explicit_match, 0.95
        
        # 3. 檢查個人資訊模式
        personal_match = self._check_personal_info(text)
        if personal_match:
            return True, personal_match['type'], text, personal_match['confidence']
        
        # 4. 檢查語句結構和語義
        structural_match = self._analyze_sentence_structure(text)
        if structural_match:
            return True, structural_match['type'], text, structural_match['confidence']
        
        return False, "none", None, 0.0
    
    def _is_query(self, text: str) -> bool:
        """判斷是否為查詢語句"""
        # 檢查疑問詞開頭
        question_starters = ['什麼', '怎麼', '為什麼', '在哪', '何時', '誰', '哪個', '哪裡']
        if any(text.startswith(q) for q in question_starters):
            return True
        
        # 檢查疑問句模式
        question_patterns = ['嗎？', '呢？', '吧？', '？', '嗎', '呢']
        if any(text.endswith(q) for q in question_patterns):
            return True
        
        # 檢查查詢關鍵詞
        return any(indicator in text for indicator in self.query_indicators)
    
    def _check_explicit_memory_request(self, text: str) -> Optional[str]:
        """檢查明確的記憶請求"""
        for keyword in self.explicit_memory_requests:
            if keyword in text:
                # 提取要記住的內容
                parts = text.split(keyword, 1)
                if len(parts) > 1:
                    content = parts[1].strip(' ：:，,.。')
                    return content if content else text
                return text
        return None
    
    def _check_personal_info(self, text: str) -> Optional[Dict]:
        """檢查個人資訊"""
        for category, indicators in self.personal_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    # 根據不同類型計算信心度
                    confidence = 0.85 if category in ['身分', '偏好'] else 0.75
                    return {
                        'type': f'personal_{category}',
                        'confidence': confidence
                    }
        return None
    
    def _analyze_sentence_structure(self, text: str) -> Optional[Dict]:
        """分析語句結構判斷是否應該記憶"""
        
        # 1. 陳述句 - 通常包含個人資訊
        if self._is_declarative_statement(text):
            return {'type': 'declarative', 'confidence': 0.65}
        
        # 2. 未來計畫或提醒
        if self._is_future_plan(text):
            return {'type': 'plan', 'confidence': 0.8}
        
        # 3. 重要事實或資訊
        if self._is_important_fact(text):
            return {'type': 'important_fact', 'confidence': 0.7}
        
        return None
    
    def _is_declarative_statement(self, text: str) -> bool:
        """判斷是否為陳述句"""
        # 第一人稱陳述
        first_person_patterns = ['我', '我的', '我在', '我會', '我有']
        has_first_person = any(pattern in text for pattern in first_person_patterns)
        
        # 不是疑問句
        is_not_question = not any(text.endswith(q) for q in ['？', '?', '嗎', '呢', '吧'])
        
        # 包含動作或狀態動詞
        action_verbs = ['是', '在', '有', '做', '喜歡', '討厭', '住', '工作', '學習']
        has_action = any(verb in text for verb in action_verbs)
        
        return has_first_person and is_not_question and has_action
    
    def _is_future_plan(self, text: str) -> bool:
        """判斷是否為未來計畫"""
        future_indicators = [
            '打算', '計劃', '想要', '希望', '準備', '將會', '要', '會',
            '明天', '下週', '下個月', '以後', '等等', '提醒我'
        ]
        return any(indicator in text for indicator in future_indicators)
    
    def _is_important_fact(self, text: str) -> bool:
        """判斷是否為重要事實"""
        importance_indicators = [
            '重要', '關鍵', '必須', '一定要', '務必', '千萬', '特別',
            '注意', '記住', '別忘了'
        ]
        return any(indicator in text for indicator in importance_indicators)


class MemoryDeletionDetector:
    """記憶刪除檢測器 - 識別刪除請求"""
    
    def __init__(self):
        self.deletion_keywords = {
            'explicit': [
                '刪除', '刪掉', '移除', '忘記', '忘掉', '清除',
                '去掉', '別記得', '不要記得', '取消記憶',
                'delete', 'remove', 'forget', 'erase', 'clear'
            ],
            'specific_patterns': [
                '刪除.*記憶', '忘記我說過.*', '不要記得.*',
                '清除.*資訊', '刪掉.*內容', '忘記我的.*'
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
        remaining_text = re.sub(r'^[：:，,.。!！？?]+', '', remaining_text).strip()
        
        return remaining_text if remaining_text else None


class SmartMemoryManager:
    """智能記憶管理器 - 統合所有記憶功能"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        try:
            self.memory_system = AdvancedMemorySystem(model_name)
        except Exception as e:
            print(f"記憶系統初始化失敗: {e}")
            self.memory_system = AdvancedMemorySystem('fake-model')  # 使用假模型
            
        self.trigger_detector = SmartMemoryTriggerDetector()
        self.deletion_detector = MemoryDeletionDetector()
        print("智能記憶管理器初始化完成")
    
    def should_remember(self, user_input: str) -> Dict:
        """判斷是否需要記憶"""
        should_remember, memory_type, content, confidence = self.trigger_detector.detect_memory_request(user_input)
        
        return {
            'should_remember': should_remember,
            'memory_type': memory_type,
            'extracted_content': content,
            'confidence': confidence,
            'reason': 'semantic_analysis' if should_remember else 'query_or_no_trigger'
        }
    
    def build_context_with_memories(self, user_input: str, relevant_memories: List[Dict] = None) -> str:
        """構建包含記憶的上下文 - 這是關鍵改進"""
        if relevant_memories is None:
            relevant_memories = self.memory_system.search_memories(user_input, top_k=3, threshold=0.6)
        
        # 構建系統提示
        system_prompt = "你是一個智能桌面寵物，可以記住用戶告訴你的資訊。"
        
        if relevant_memories:
            memory_context = "以下是你之前記住的相關資訊：\n"
            for memory in relevant_memories:
                memory_context += f"- {memory['text']}\n"
            memory_context += "\n請基於這些記憶來回答用戶的問題。如果用戶詢問你記住的資訊，請直接使用這些記憶內容回答。\n\n"
        else:
            memory_context = "目前沒有相關的記憶資訊。\n\n"
        
        full_context = system_prompt + "\n\n" + memory_context + f"用戶當前的問題或輸入：{user_input}"
        
        return full_context
    
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


class SmartChatbotWithMemory:
    """智能記憶聊天機器人 - 專為整合到其他系統設計"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', memory_file='chatbot_memory'):
        self.memory_manager = SmartMemoryManager(model_name)
        self.memory_file = memory_file
        
        # 嘗試載入既有記憶
        try:
            self.memory_manager.memory_system.load_from_disk(self.memory_file)
            print("已載入既有記憶系統")
        except:
            print("建立新的記憶系統")
    
    def process_input(self, user_input: str) -> Tuple[Dict, str, List[Dict]]:
        """
        處理用戶輸入，返回完整的處理結果
        
        Args:
            user_input: 用戶輸入文字
            
        Returns:
            Tuple[處理結果字典, 給LLM的完整上下文, 相關記憶列表]
        """
        user_input = user_input.strip()
        
        result = {
            'has_response': False,
            'response': '',
            'memory_action': 'none',
            'memory_id': None,
            'deleted_count': 0,
            'should_save': False,
            'llm_context': ''  # 新增：給LLM的完整上下文
        }
        
        # 1. 檢查刪除請求
        deletion_result = self.memory_manager.process_deletion_request(user_input)
        if deletion_result['success']:
            result['has_response'] = True
            result['response'] = deletion_result['message']
            result['memory_action'] = 'delete'
            result['deleted_count'] = deletion_result['deleted_count']
            result['should_save'] = True
            self._save_memory()
            return result, "", []
        
        # 2. 檢查特殊指令
        if user_input.lower() in ['列出記憶', 'list memories', '顯示記憶', '記憶列表']:
            memories = self._list_memories()
            if not memories:
                result['response'] = "目前沒有任何記憶。"
            else:
                memory_list = "\n".join([
                    f"[ID:{m['id']}] {m['timestamp']} - {m['text']}" 
                    for m in memories
                ])
                result['response'] = f"當前記憶:\n{memory_list}"
            result['has_response'] = True
            return result, "", memories
        
        if user_input.lower() in ['記憶統計', 'memory stats', '統計']:
            stats = self.memory_manager.memory_system.get_memory_stats()
            result['response'] = (f"📊 記憶統計:\n"
                                f"活躍記憶: {stats['active']}\n"
                                f"已刪除: {stats['deleted']}\n"
                                f"總計: {stats['total']}\n"
                                f"需要清理: {'是' if stats['cleanup_needed'] else '否'}")
            result['has_response'] = True
            return result, "", []
        
        # 3. 搜索相關記憶
        relevant_memories = self.memory_manager.memory_system.search_memories(
            user_input, top_k=3, threshold=0.6
        )
        
        # 4. 構建給LLM的完整上下文 - 這是關鍵改進！
        llm_context = self.memory_manager.build_context_with_memories(user_input, relevant_memories)
        result['llm_context'] = llm_context
        
        # 5. 檢測記憶請求
        memory_decision = self.memory_manager.should_remember(user_input)
        
        # 6. 根據檢測結果決定是否記憶
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
            
            result['memory_action'] = 'add'
            result['memory_id'] = memory_id
            result['should_save'] = True
            
            self._save_memory()
        
        return result, llm_context, relevant_memories
    
    def get_relevant_memories(self, user_input: str, top_k: int = 3, threshold: float = 0.6) -> List[Dict]:
        """獲取與輸入最相關的記憶"""
        return self.memory_manager.memory_system.search_memories(user_input, top_k, threshold)
    
    def add_memory_manually(self, content: str, metadata: Dict = None) -> int:
        """手動添加記憶"""
        memory_id = self.memory_manager.memory_system.add_memory(content, metadata)
        self._save_memory()
        return memory_id
    
    def _list_memories(self, limit: int = 10) -> List[Dict]:
        """列出當前的記憶"""
        memories = []
        count = 0
        
        for memory_id, memory, metadata in zip(
            self.memory_manager.memory_system.memory_ids, 
            self.memory_manager.memory_system.memories, 
            self.memory_manager.memory_system.metadata
        ):
            if memory_id not in self.memory_manager.memory_system.deleted_ids and memory != "[DELETED]":
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
    
    def _save_memory(self):
        """保存記憶到磁盤"""
        try:
            self.memory_manager.memory_system.save_to_disk(self.memory_file)
        except Exception as e:
            print(f"保存記憶失敗: {e}")
    
    def get_stats(self) -> Dict:
        """獲取系統統計資訊"""
        return self.memory_manager.memory_system.get_memory_stats()