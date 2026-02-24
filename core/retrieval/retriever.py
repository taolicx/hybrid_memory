"""记忆检索模块"""
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.provider import ProviderRequest


class MemoryRetriever:
    """记忆检索器 - 负责在LLM请求前注入记忆"""

    def __init__(self, long_term_memory: Any, short_term_memory: Any, config_manager: Any):
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory
        self.config_manager = config_manager

    async def inject_memory(self, event: AstrMessageEvent, req: ProviderRequest):
        """注入记忆到LLM请求"""
        session_id = event.get_session_id()
        if not session_id:
            return

        # 获取系统提示词
        system_prompt = req.system_prompt or ""
        
        # 构建记忆上下文
        memory_context = await self._build_memory_context(session_id, req)
        
        if memory_context:
            # 注入到系统提示词
            memory_prompt = f"\n\n[记忆上下文]\n{memory_context}\n[/记忆上下文]\n"
            req.system_prompt = system_prompt + memory_prompt
            
            logger.debug(f"已注入记忆上下文到会话 {session_id}")

    async def _build_memory_context(self, session_id: str, req: ProviderRequest) -> str:
        """构建记忆上下文"""
        parts = []
        
        # 获取短期记忆
        short_memories = self.short_term_memory.get_session_context(session_id)
        if short_memories:
            short_text = self._format_short_term_memory(short_memories)
            parts.append(f"=== 短期记忆 (最近对话) ===\n{short_text}")
        
        # 获取长期记忆
        query = self._extract_query_from_request(req)
        if query:
            long_memories = await self.long_term_memory.search(query, k=self.config_manager.retrieval_top_k)
            if long_memories:
                long_text = self._format_long_term_memory(long_memories)
                parts.append(f"=== 长期记忆 (相关记忆) ===\n{long_text}")
        
        return "\n\n".join(parts) if parts else ""

    def _extract_query_from_request(self, req: ProviderRequest) -> str:
        """从请求中提取查询"""
        # 尝试从消息中提取
        try:
            if hasattr(req, 'messages') and req.messages:
                last_msg = req.messages[-1]
                if isinstance(last_msg, dict):
                    return last_msg.get('content', '')[:500]
                elif hasattr(last_msg, 'content'):
                    return last_msg.content[:500]
        except Exception:
            pass
        return ""

    def _format_short_term_memory(self, memories: list[dict]) -> str:
        """格式化短期记忆"""
        lines = []
        for m in memories[-10:]:  # 最近10条
            role = "用户" if m.get('role') == 'user' else "助手"
            content = m.get('content', '')[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _format_long_term_memory(self, memories: list[dict]) -> str:
        """格式化长期记忆"""
        lines = []
        for m in memories:
            content = m.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            importance = m.get('importance', 0.5)
            lines.append(f"[重要性: {importance:.1f}] {content}")
        return "\n".join(lines)