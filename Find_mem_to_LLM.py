from memory_system import SmartChatbotWithMemory

class MyBot:
    def __init__(self):
        self.memory_system = SmartChatbotWithMemory()
    
    def process_message(self, user_input: str):
        # 1. 搜索最相關的記憶（最多3條，太不相關不拿）
        relevant_memories = self.memory_system.get_relevant_memories(
            user_input, top_k=3, threshold=0.6
        )
        
        # 2. 處理輸入（自動判斷記憶和刪除）
        response, used_memories = self.memory_system.process_input(
            user_input, return_memories=True
        )
        
        return {
            'response': response,
            'memories_found': relevant_memories,
            'memories_found_num': len(relevant_memories),
            'memories_used': len(used_memories)
        }



# 使用
bot = MyBot()
while True:

    user_input = input("\n輸入你想講的話：")
    result = bot.process_message(user_input)
    print(result['response'])
    print("相關的記憶：",result['memories_found'])