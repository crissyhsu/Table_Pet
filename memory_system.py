"""
智能记忆聊天机器人系统 - 改进版
整合记忆储存、搜索、删除和自动检测功能

依赖套件:
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
    print("请安装 faiss: pip install faiss-cpu")
    # 为了不让整个程式崩潰，我們提供一個假的替代實現
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
    """进阶记忆系统 - 支援向量检索和记忆管理"""
    
    def __init__(self, embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        print(f"初始化记忆系统，载入模型: {embedding_model_name}")
        try:
            self.model = SentenceTransformer(embedding_model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"无法载入嵌入模型: {e}")
            print("使用简化的文字比对模式")
            self.model = None
            self.dimension = 768
            
        self.index = faiss.IndexFlatIP(self.dimension)
        self.memories = []
        self.metadata = []
        self.memory_ids = []
        self.next_id = 0
        self.deleted_ids = set()
        
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单的文字相似度计算（当没有嵌入模型时使用）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 and not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
        
    def add_memory(self, text: str, metadata: Dict = None) -> int:
        """添加记忆并返回记忆 ID"""
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
        
        # 添加时间戳
        if metadata is None:
            metadata = {}
        metadata['timestamp'] = metadata.get('timestamp', time.time())
        metadata['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        self.metadata.append(metadata)
        self.memory_ids.append(memory_id)
        self.next_id += 1
        
        return memory_id
    
    def delete_memory_by_id(self, memory_id: int) -> bool:
        """根据 ID 删除记忆"""
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
        """根据内容相似度删除记忆"""
        deleted_ids = []
        similar_memories = self.search_memories(search_text, top_k=10, threshold=threshold)
        
        for memory in similar_memories:
            memory_idx = memory['index']
            memory_id = self.memory_ids[memory_idx]
            
            if self.delete_memory_by_id(memory_id):
                deleted_ids.append(memory_id)
        
        return deleted_ids
    
    def delete_recent_memories(self, hours: int = 24) -> List[int]:
        """删除最近指定时间内的记忆"""
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
        """清理已删除的记忆，重建索引"""
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
        
        print(f"清理完成，剩餘 {len(self.memories)} 条记忆")
    
    def search_memories(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """搜索记忆（排除已删除的）"""
        if len(self.memories) == 0:
            return []
        
        if self.model:
            query_embedding = self.model.encode([query])
            scores, indices = self.index.search(
                query_embedding.astype('float32'), 
                min(top_k * 2, len(self.memories))
            )
        else:
            # 使用简单相似度计算
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
        """将记忆格式化为自然语言加入 prompt"""
        if not memories:
            return ""
        
        formatted_memories = []
        for memory in memories:
            formatted_memories.append(f"- {memory['text']}")
        
        return f"""
相关记忆：
{chr(10).join(formatted_memories)}

请基于以上记忆内容来回答问题。
"""
    
    def get_memory_stats(self) -> Dict:
        """取得记忆统计资讯"""
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
        """保存记忆系统到本地端"""
        try:
            # 保存 FAISS 索引
            faiss.write_index(self.index, f"{filepath}.index")
            
            # 保存其他资料
            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump({
                    'memories': self.memories,
                    'metadata': self.metadata,
                    'memory_ids': self.memory_ids,
                    'next_id': self.next_id,
                    'deleted_ids': self.deleted_ids
                }, f)
            
            print(f"记忆系统已保存到 {filepath}")
            
        except Exception as e:
            print(f"保存失败: {e}")
    
    def load_from_disk(self, filepath: str):
        """从本地端载入记忆系统"""
        try:
            # 载入 FAISS 索引
            if os.path.exists(f"{filepath}.index"):
                self.index = faiss.read_index(f"{filepath}.index")
            
            # 载入其他资料
            if os.path.exists(f"{filepath}.pkl"):
                with open(f"{filepath}.pkl", 'rb') as f:
                    data = pickle.load(f)
                    self.memories = data.get('memories', [])
                    self.metadata = data.get('metadata', [])
                    self.memory_ids = data.get('memory_ids', [])
                    self.next_id = data.get('next_id', 0)
                    self.deleted_ids = data.get('deleted_ids', set())
                
                print(f"已载入 {len(self.memories)} 条记忆")
            
        except Exception as e:
            print(f"载入失败: {e}")


class ImprovedMemoryTriggerDetector:
    """改进的记忆触发检测器 - 更精准地识别用户是否要求记住内容"""
    
    def __init__(self):
        # 明确的记忆存储关键词
            self.explicit_memory_keywords = [
                r'记住', r'记下', r'记录', r'存起来', r'保存', r'储存',
                r'记在', r'别忘记', r'不要忘记', r'记一下', r'记住这个',
                r'帮我记住', r'请记住', r'要记得', 
                r'remember', r'save this', r'keep in mind', r"don't forget",
                r'记住我', r'我告诉你', r'我叫', r'我的名字是'
            ]
            
            # 个人信息模式（用户主动提供信息）
            self.personal_info_list = [
                r'^我叫\s*(.+)',
                r'^我的名字是\s*(.+)', 
                r'^我住在\s*(.+)',
                r'^我的生日是\s*(.+)',
                r'^我喜欢\s*(.+)',
                r'^我不喜欢\s*(.+)',
                r'^我的工作是\s*(.+)',
                r'^我是一个\s*(.+)',
                r'我今年\s*(\d+)\s*岁',
                r'我来自\s*(.+)'
            ]
            
            # 查询关键词（这些不应该被记忆）
            self.query_keywords = [
                r'你叫什么', r'你的名字', r'你是谁', r'你会什么', 
                r'什么是', r'怎么', r'为什么', r'在哪里', r'什么时候',
                r'能不能', r'可以吗', r'帮我', r'告诉我',
                r'what is', r'what are', r'who are', r'how to', r'why',
                r'where', r'when', r'can you', r'could you', 'tell me'
            ]
            
            self.explicit_patterns = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in self.explicit_memory_keywords
            ]
            
            self.personal_info_patterns = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in self.personal_info_list
            ]
            
            self.query_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.query_keywords
            ]
    
    def detect_memory_request(self, text: str) -> Tuple[bool, str, Optional[str]]:
        """检测是否需要记忆 - 改进版"""
        text = text.strip()
        
        # 首先检查是否是查询（这些不应该被记忆）
        for pattern in self.query_patterns:
            if pattern.search(text):
                return False, "query", None
        
        # 检查明确的记忆请求
        for pattern in self.explicit_patterns:
            if pattern.search(text):
                return True, "explicit", self._extract_content_after_keyword(text, pattern)
        
        # 检查个人信息模式
        for pattern in self.personal_info_patterns:
            match = pattern.search(text)
            if match:
                return True, "personal_info", text
        
        # 检测特殊模式
        if self._detect_special_patterns(text):
            return True, "contextual", text
        
        return False, "none", None
    
    def _extract_content_after_keyword(self, text: str, pattern) -> str:
        """提取关键字后的内容"""
        match = pattern.search(text)
        if match:
            start_pos = match.end()
            content = text[start_pos:].strip()
            content = re.sub(r'^[：:，,.。!！？?]+', '', content).strip()
            return content if content else text
        return text
    
    def _detect_special_patterns(self, text: str) -> bool:
        """检测特殊模式"""
        special_patterns = [
            r'提醒我', r'我通常', r'我习惯',
            r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{1,2}/\d{1,2}/\d{4}',
            r'\w+@\w+\.\w+', r'\+?\d{10,}'
        ]
        
        for pattern in special_patterns:
            if re.search(pattern, text):
                return True
        return False


class MemoryDeletionDetector:
    """记忆删除检测器 - 识别删除请求"""
    
    def __init__(self):
        self.deletion_keywords = {
            'explicit': [
                r'删除', r'删掉', r'移除', r'忘记', r'忘掉', r'清除',
                r'去掉', r'别记得', r'不要记得', r'取消记忆',
                r'delete', r'remove', r'forget', r'erase', r'clear'
            ],
            'specific_patterns': [
                r'删除.*记忆', r'忘记我说过.*', r'不要记得.*',
                r'清除.*资讯', r'删掉.*内容', r'忘记我的.*'
            ]
        }
        
        self.deletion_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.deletion_keywords['explicit'] + self.deletion_keywords['specific_patterns']
        ]
    
    def detect_deletion_request(self, text: str) -> Dict:
        """检测删除请求"""
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
                elif any(word in text.lower() for word in ['最近', 'recent', '刚才', '今天']):
                    result['deletion_scope'] = 'recent'
                else:
                    result['deletion_scope'] = 'specific'
                
                break
        
        return result
    
    def _extract_deletion_target(self, text: str, match) -> Optional[str]:
        """提取要删除的目标内容"""
        start_pos = match.end()
        remaining_text = text[start_pos:].strip()
        
        remaining_text = re.sub(r'^[关于about]*', '', remaining_text, flags=re.IGNORECASE).strip()
        remaining_text = re.sub(r'^[：:，,.。!！？?]+', '', remaining_text).strip()
        
        return remaining_text if remaining_text else None


class SmartMemoryManager:
    """智能记忆管理器 - 统合所有记忆功能"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        try:
            self.memory_system = AdvancedMemorySystem(model_name)
        except Exception as e:
            print(f"记忆系统初始化失败: {e}")
            self.memory_system = AdvancedMemorySystem('fake-model')  # 使用假模型
            
        self.trigger_detector = ImprovedMemoryTriggerDetector()
        self.deletion_detector = MemoryDeletionDetector()
        print("智能记忆管理器初始化完成")
    
    def should_remember(self, user_input: str) -> Dict:
        """判断是否需要记忆"""
        should_remember, memory_type, content = self.trigger_detector.detect_memory_request(user_input)
        
        return {
            'should_remember': should_remember,
            'memory_type': memory_type,
            'extracted_content': content,
            'confidence': 0.9 if memory_type == 'explicit' else 0.8 if memory_type == 'personal_info' else 0.6,
            'reason': 'keyword_detected' if should_remember else 'query_or_no_trigger'
        }
    
    def build_context_with_memories(self, user_input: str, relevant_memories: List[Dict] = None) -> str:
        """构建包含记忆的上下文 - 这是关键改进"""
        if relevant_memories is None:
            relevant_memories = self.memory_system.search_memories(user_input, top_k=3, threshold=0.6)
        
        # 构建系统提示
        system_prompt = "你是一个智能桌面宠物，可以记住用户告诉你的信息。"
        
        if relevant_memories:
            memory_context = "以下是你之前记住的相关信息：\n"
            for memory in relevant_memories:
                memory_context += f"- {memory['text']}\n"
            memory_context += "\n请基于这些记忆来回答用户的问题。如果用户询问你记住的信息，请直接使用这些记忆内容回答。\n\n"
        else:
            memory_context = "目前没有相关的记忆信息。\n\n"
        
        full_context = system_prompt + "\n\n" + memory_context + f"用户当前的问题或输入：{user_input}"
        
        return full_context
    
    def process_deletion_request(self, user_input: str) -> Dict:
        """处理删除请求"""
        deletion_info = self.deletion_detector.detect_deletion_request(user_input)
        
        if not deletion_info['is_deletion_request']:
            return {'success': False, 'message': '未检测到删除请求'}
        
        deleted_count = 0
        deleted_ids = []
        
        if deletion_info['deletion_scope'] == 'all':
            deleted_ids = self._delete_all_memories()
            deleted_count = len(deleted_ids)
            message = f"已删除所有 {deleted_count} 条记忆"
            
        elif deletion_info['deletion_scope'] == 'recent':
            deleted_ids = self.memory_system.delete_recent_memories(24)
            deleted_count = len(deleted_ids)
            message = f"已删除最近 {deleted_count} 条记忆"
            
        elif deletion_info['target_content']:
            deleted_ids = self.memory_system.delete_memories_by_content(
                deletion_info['target_content'], 
                threshold=0.7
            )
            deleted_count = len(deleted_ids)
            message = f"已删除 {deleted_count} 条与「{deletion_info['target_content']}」相关的记忆"
            
        else:
            return {'success': False, 'message': '无法确定要删除的内容'}
        
        if deleted_count > 0:
            self.memory_system.cleanup_deleted_memories()
        
        return {
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'deleted_ids': deleted_ids
        }
    
    def _delete_all_memories(self) -> List[int]:
        """删除所有记忆"""
        all_ids = [mid for mid in self.memory_system.memory_ids 
                  if mid not in self.memory_system.deleted_ids]
        
        for memory_id in all_ids:
            self.memory_system.delete_memory_by_id(memory_id)
        
        return all_ids


class SmartChatbotWithMemory:
    """智能记忆聊天机器人 - 专为整合到其他系统设计"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', memory_file='chatbot_memory'):
        self.memory_manager = SmartMemoryManager(model_name)
        self.memory_file = memory_file
        
        # 尝试载入既有记忆
        try:
            self.memory_manager.memory_system.load_from_disk(self.memory_file)
            print("已载入既有记忆系统")
        except:
            print("建立新的记忆系统")
    
    def process_input(self, user_input: str) -> Tuple[Dict, str, List[Dict]]:
        """
        处理用户输入，返回完整的处理结果
        
        Args:
            user_input: 用户输入文字
            
        Returns:
            Tuple[处理结果字典, 给LLM的完整上下文, 相关记忆列表]
        """
        user_input = user_input.strip()
        
        result = {
            'has_response': False,
            'response': '',
            'memory_action': 'none',
            'memory_id': None,
            'deleted_count': 0,
            'should_save': False,
            'llm_context': ''  # 新增：给LLM的完整上下文
        }
        
        # 1. 检查删除请求
        deletion_result = self.memory_manager.process_deletion_request(user_input)
        if deletion_result['success']:
            result['has_response'] = True
            result['response'] = deletion_result['message']
            result['memory_action'] = 'delete'
            result['deleted_count'] = deletion_result['deleted_count']
            result['should_save'] = True
            self._save_memory()
            return result, "", []
        
        # 2. 检查特殊指令
        if user_input.lower() in ['列出记忆', 'list memories', '显示记忆', '记忆列表']:
            memories = self._list_memories()
            if not memories:
                result['response'] = "目前没有任何记忆。"
            else:
                memory_list = "\n".join([
                    f"[ID:{m['id']}] {m['timestamp']} - {m['text']}" 
                    for m in memories
                ])
                result['response'] = f"当前记忆:\n{memory_list}"
            result['has_response'] = True
            return result, "", memories
        
        if user_input.lower() in ['记忆统计', 'memory stats', '统计']:
            stats = self.memory_manager.memory_system.get_memory_stats()
            result['response'] = (f"📊 记忆统计:\n"
                                f"活跃记忆: {stats['active']}\n"
                                f"已删除: {stats['deleted']}\n"
                                f"总计: {stats['total']}\n"
                                f"需要清理: {'是' if stats['cleanup_needed'] else '否'}")
            result['has_response'] = True
            return result, "", []
        
        # 3. 搜索相关记忆
        relevant_memories = self.memory_manager.memory_system.search_memories(
            user_input, top_k=3, threshold=0.6
        )
        
        # 4. 构建给LLM的完整上下文 - 这是关键改进！
        llm_context = self.memory_manager.build_context_with_memories(user_input, relevant_memories)
        result['llm_context'] = llm_context
        
        # 5. 检测记忆请求
        memory_decision = self.memory_manager.should_remember(user_input)
        
        # 6. 根据检测结果决定是否记忆
        if memory_decision['should_remember']:
            memory_content = memory_decision['extracted_content'] or user_input
            
            # 存储记忆
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
        """获取与输入最相关的记忆"""
        return self.memory_manager.memory_system.search_memories(user_input, top_k, threshold)
    
    def add_memory_manually(self, content: str, metadata: Dict = None) -> int:
        """手动添加记忆"""
        memory_id = self.memory_manager.memory_system.add_memory(content, metadata)
        self._save_memory()
        return memory_id
    
    def _list_memories(self, limit: int = 10) -> List[Dict]:
        """列出当前的记忆"""
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
        """保存记忆到磁盘"""
        try:
            self.memory_manager.memory_system.save_to_disk(self.memory_file)
        except Exception as e:
            print(f"保存记忆失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取系统统计信息"""
        return self.memory_manager.memory_system.get_memory_stats()
    
        patterns = [
            r'^我叫\s*(.+)',
            r'^我的名字是\s*(.+)', 
            r'^我住在\s*(.+)',
            r'^我的生日是\s*(.+)',
            r'^我喜欢\s*(.+)',
            r'^我不喜欢\s*(.+)',
            r'^我的工作是\s*(.+)',
            r'^我是一个\s*(.+)',
            r'我今年\s*(\d+)\s*岁',
            r'我来自\s*(.+)'
        ]
        
        # 查询关键词（这些不应该被记忆）
        self.query_keywords = [
            r'你叫什么', r'你的名字', r'你是谁', r'你会什么', 
            r'什么是', r'怎么', r'为什么', r'在哪里', r'什么时候',
            r'能不能', r'可以吗', r'帮我', r'告诉我',
            r'what is', r'what are', r'who are', r'how to', r'why',
            r'where', r'when', r'can you', r'could you', r'tell me'
        ]
        
        # 删除关键词
        self.deletion_keywords = [
            r'删除', r'删掉', r'移除', r'忘记', r'忘掉', r'清除',
            r'去掉', r'别记得', r'不要记得', r'取消记忆',
            r'delete', r'remove', r'forget', r'erase', r'clear'
        ]
        
        self.explicit_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.explicit_memory_keywords
        ]
        
        self.personal_info_