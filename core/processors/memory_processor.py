"""记忆处理器模块"""
import asyncio
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


class MemoryProcessor:
    """记忆处理器 - 负责处理消息和响应"""

    def __init__(self, context: Any, long_term_memory: Any, short_term_memory: Any, config_manager: Any):
        self.context = context
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory
        self.config_manager = config_manager
        self._message_counter: dict[str, int] = {}

    async def handle_message(self, event: AstrMessageEvent):
        """处理收到的消息"""
        session_id = event.get_session_id()
        if not session_id:
            return
        
        # 获取消息内容
        message = event.get_message()
        if not message:
            return
        
        # 添加到短期记忆
        self.short_term_memory.add_message(session_id, "user", str(message))
        
        # 更新计数器
        self._message_counter[session_id] = self._message_counter.get(session_id, 0) + 1
        
        # 检查是否需要总结
        threshold = self.config_manager.summary_threshold
        if self._message_counter[session_id] >= threshold:
            await self.summarize_session(session_id)
            self._message_counter[session_id] = 0

    async def process_response(self, event: AstrMessageEvent, response: Any):
        """处理LLM响应"""
        session_id = event.get_session_id()
        if not session_id:
            return
        
        # 获取响应内容
        if hasattr(response, 'text'):
            content = response.text
        elif hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
        
        # 添加到短期记忆
        self.short_term_memory.add_message(session_id, "assistant", content)
        
        # 可选：选择性存储到长期记忆
        # 这里可以实现重要性评估逻辑
        await self._maybe_store_long_term(session_id, content)

    async def _maybe_store_long_term(self, session_id: str, content: str):
        """可能存储到长期记忆"""
        # 简单实现：超过一定长度才存储
        if len(content) > 100:
            # 这里可以添加更复杂的评估逻辑
            await self.long_term_memory.add_memory(
                content=content,
                session_id=session_id,
                importance=0.5,
                metadata={"source": "response"}
            )

    async def summarize_session(self, session_id: str) -> str:
        """总结会话并存储到长期记忆"""
        try:
            # 获取会话消息
            messages = self.short_term_memory.get_session_context(session_id)
            
            if not messages:
                return ""
            
            # 构建总结提示
            summary_prompt = f"""请总结以下对话的要点:

{chr(10).join([f"{m['role']}: {m['content'][:200]}" for m in messages[-10:]])}

请用简洁的语言总结关键信息:"""
            
            # 调用LLM进行总结
            # 注意：这里需要根据实际的 LLM API 进行调整
            summary = await self._call_llm_summary(summary_prompt)
            
            if summary:
                # 存储到长期记忆
                await self.long_term_memory.add_memory(
                    content=summary,
                    session_id=session_id,
                    importance=0.7,
                    metadata={"type": "summary"}
                )
                
                logger.info(f"会话 {session_id} 总结已存储")
            
            return summary or ""
        except Exception as e:
            logger.error(f"总结会话失败: {e}")
            return ""

    async def _call_llm_summary(self, prompt: str) -> str:
        """调用LLM进行总结"""
        # 这里需要实现实际的 LLM 调用
        # 可以通过 self.context 获取 provider
        try:
            provider = self.context.lc_llm
            if provider:
                # 简化实现
                return f"[这是对话总结 - {len(prompt)} 字符]"
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
        
        return ""
