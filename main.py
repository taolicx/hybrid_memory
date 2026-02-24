"""HybridMemory 插件主文件
整合长期记忆 (LivingMemory) 与短期记忆 (Mnemosyne) 的混合记忆系统
"""
import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.event.filter import PermissionType, permission_type
from astrbot.api.provider import LLMResponse, ProviderRequest
from astrbot.api.star import Star, StarTools, register

from .core.base.config_manager import ConfigManager
from .core.managers.long_term_memory import LongTermMemoryEngine
from .core.managers.short_term_memory import ShortTermMemoryManager
from .core.processors.memory_processor import MemoryProcessor
from .core.retrieval.retriever import MemoryRetriever
from .webui import WebUIServer


@register(
    "HybridMemory",
    "lxfight",
    "整合长期记忆与短期记忆的混合记忆系统，支持动态生命周期和WebUI管理",
    "1.0.0",
    "https://github.com/your-repo/hybrid_memory",
)
class HybridMemoryPlugin(Star):
    """HybridMemory 插件主类"""

    def __init__(self, context: Any, config: dict[str, Any]):
        super().__init__(context)
        self.context = context
        self.config = config
        
        # 获取插件数据目录
        data_dir = str(StarTools.get_data_dir())
        self.data_dir = Path(data_dir)
        self.storage_dir = self.data_dir / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(config)
        
        # 初始化长期记忆引擎
        self.long_term_memory = LongTermMemoryEngine(
            context=context,
            config_manager=self.config_manager,
            data_dir=str(self.storage_dir)
        )
        
        # 初始化短期记忆管理器
        self.short_term_memory = ShortTermMemoryManager(
            data_dir=str(self.storage_dir)
        )
        
        # 初始化记忆处理器
        self.memory_processor = MemoryProcessor(
            context=context,
            long_term_memory=self.long_term_memory,
            short_term_memory=self.short_term_memory,
            config_manager=self.config_manager
        )
        
        # 初始化记忆检索器
        self.retriever = MemoryRetriever(
            long_term_memory=self.long_term_memory,
            short_term_memory=self.short_term_memory,
            config_manager=self.config_manager
        )
        
        # WebUI 服务器
        self.webui_server: WebUIServer | None = None
        
        # 后台任务
        self._background_tasks: set[asyncio.Task] = set()
        
        # 启动初始化
        self._create_task(self._initialize())

    def _create_task(self, coro) -> asyncio.Task:
        """创建并跟踪后台任务"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def _initialize(self):
        """初始化插件"""
        try:
            # 初始化长期记忆引擎
            await self.long_term_memory.initialize()
            
            # 启动 WebUI
            await self._start_webui()
            
            logger.info("HybridMemory 插件初始化完成")
        except Exception as e:
            logger.error(f"HybridMemory 插件初始化失败: {e}", exc_info=True)

    async def _start_webui(self):
        """启动 WebUI"""
        webui_config = self.config_manager.webui_settings
        if not webui_config.get("enabled"):
            return
        
        try:
            self.webui_server = WebUIServer(
                long_term_memory=self.long_term_memory,
                short_term_memory=self.short_term_memory,
                config=webui_config,
                data_dir=str(self.storage_dir)
            )
            await self.webui_server.start()
            logger.info(f"WebUI started at: http://{webui_config.get('host', '127.0.0.1')}:{webui_config.get('port', 9241)}")
        except Exception as e:
            logger.error(f"启动 WebUI 失败: {e}", exc_info=True)

    async def _stop_webui(self):
        """停止 WebUI"""
        if self.webui_server:
            try:
                await self.webui_server.stop()
            except Exception as e:
                logger.warning(f"停止 WebUI 时出现异常: {e}", exc_info=True)
            finally:
                self.webui_server = None

    # ==================== 事件钩子 ====================

    @filter.platform_adapter_type(filter.PlatformAdapterType.ALL)
    async def handle_all_group_messages(self, event: AstrMessageEvent):
        """[事件钩子] 捕获所有消息用于短期记忆存储"""
        await self.memory_processor.handle_message(event)

    @filter.on_llm_request()
    async def handle_memory_recall(self, event: AstrMessageEvent, req: ProviderRequest):
        """[事件钩子] 在 LLM 请求前，查询并注入记忆"""
        await self.retriever.inject_memory(event, req)

    @filter.on_llm_response()
    async def handle_memory_storage(self, event: AstrMessageEvent, resp: LLMResponse):
        """[事件钩子] 在 LLM 响应后，存储记忆"""
        await self.memory_processor.process_response(event, resp)

    @filter.after_message_sent()
    async def handle_session_reset(self, event: AstrMessageEvent):
        """[事件钩子] 消息发送后检查是否需要重置"""
        if event.get_extra("_clean_ltm_session", False):
            session_id = event.get_session_id()
            if session_id:
                self.short_term_memory.clear_session(session_id)

    # ==================== 命令处理 ====================

    @filter.command_group("hmem")
    def hmem(self):
        """混合记忆管理命令组 /hmem"""
        pass

    @permission_type(PermissionType.ADMIN)
    @hmem.command("status", priority=10)
    async def status(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 显示记忆系统状态"""
        yield event.plain_result(await self._get_status_message())

    @permission_type(PermissionType.ADMIN)
    @hmem.command("search", priority=10)
    async def search(
        self, event: AstrMessageEvent, query: str, k: int = 5
    ) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 搜索记忆"""
        results = await self.long_term_memory.search(query, k)
        if not results:
            yield event.plain_result("未找到相关记忆。")
            return
        
        msg = f"找到 {len(results)} 条相关记忆:\n\n"
        for i, r in enumerate(results, 1):
            msg += f"{i}. [ID:{r.get('id')}] {r.get('content', '')[:100]}...\n"
            msg += f"   相似度: {r.get('score', 0):.2f}\n\n"
        
        yield event.plain_result(msg)

    @permission_type(PermissionType.ADMIN)
    @hmem.command("forget")
    async def forget(
        self, event: AstrMessageEvent, doc_id: int, memory_type: str = "long"
    ) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 删除指定记忆
        Args:
            doc_id: 记忆ID
            memory_type: 记忆类型 (long/short)
        """
        if memory_type == "long":
            success = await self.long_term_memory.delete_memory(doc_id)
            msg = "长期记忆已删除" if success else "删除失败，记忆不存在"
        else:
            success = self.short_term_memory.delete_memory(doc_id)
            msg = "短期记忆已删除" if success else "删除失败，记忆不存在"
        
        yield event.plain_result(msg)

    @permission_type(PermissionType.ADMIN)
    @hmem.command("rebuild-index")
    async def rebuild_index(
        self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 重建索引"""
        yield event.plain_result("正在重建索引...")
        try:
            await self.long_term_memory.rebuild_index()
            yield event.plain_result("索引重建完成")
        except Exception as e:
            yield event.plain_result(f"索引重建失败: {e}")

    @permission_type(PermissionType.ADMIN)
    @hmem.command("webui")
    async def webui(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 显示WebUI访问信息"""
        webui_config = self.config_manager.webui_settings
        if not webui_config.get("enabled"):
            yield event.plain_result("WebUI 未启用，请在配置中开启")
            return
        
        host = webui_config.get("host", "127.0.0.1")
        port = webui_config.get("port", 9241)
        yield event.plain_result(f"WebUI 访问地址: http://{host}:{port}")

    @permission_type(PermissionType.ADMIN)
    @hmem.command("summarize")
    async def summarize(
        self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 立即触发当前会话的记忆总结"""
        session_id = event.get_session_id()
        if not session_id:
            yield event.plain_result("无法获取会话ID")
            return
        
        yield event.plain_result("正在总结记忆...")
        try:
            summary = await self.memory_processor.summarize_session(session_id)
            yield event.plain_result(f"总结完成:\n{summary}")
        except Exception as e:
            yield event.plain_result(f"总结失败: {e}")

    @permission_type(PermissionType.ADMIN)
    @hmem.command("reset")
    async def reset(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 重置当前会话的记忆"""
        session_id = event.get_session_id()
        if not session_id:
            yield event.plain_result("无法获取会话ID")
            return
        
        self.short_term_memory.clear_session(session_id)
        yield event.plain_result(f"会话 {session_id} 的短期记忆已清除")

    @permission_type(PermissionType.ADMIN)
    @hmem.command("stats")
    async def stats(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 显示记忆统计信息"""
        long_count = await self.long_term_memory.get_memory_count()
        short_stats = self.short_term_memory.get_stats()
        
        msg = "=== 记忆统计 ===\n\n"
        msg += f"长期记忆总数: {long_count}\n"
        msg += f"短期记忆会话数: {short_stats.get('session_count', 0)}\n"
        msg += f"短期记忆消息数: {short_stats.get('message_count', 0)}\n"
        
        yield event.plain_result(msg)

    @permission_type(PermissionType.ADMIN)
    @hmem.command("help")
    async def help(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """[管理员] 显示帮助信息"""
        help_text = """=== HybridMemory 命令帮助 ===

/hmem status - 显示记忆系统状态
/hmem search <关键词> [k] - 搜索记忆 (k默认5)
/hmem forget <id> [long/short] - 删除记忆 (默认长期记忆)
/hmem rebuild-index - 重建索引
/hmem webui - 显示WebUI访问地址
/hmem summarize - 立即总结当前会话
/hmem reset - 重置当前会话记忆
/hmem stats - 显示记忆统计
/hmem help - 显示此帮助

WebUI 功能:
- 查看/编辑/删除所有记忆
- 管理短期会话
- 搜索记忆
"""
        yield event.plain_result(help_text)

    async def _get_status_message(self) -> str:
        """获取状态消息"""
        try:
            long_count = await self.long_term_memory.get_memory_count()
            short_stats = self.short_term_memory.get_stats()
            
            return f"""=== HybridMemory 状态 ===

长期记忆: {long_count} 条
短期记忆: {short_stats.get('message_count', 0)} 条 ({short_stats.get('session_count', 0)} 个会话)
WebUI: {'已启用' if self.webui_server else '未启用'}
"""
        except Exception as e:
            return f"获取状态失败: {e}"

    # ==================== 生命周期管理 ====================

    async def terminate(self):
        """插件停止时的清理逻辑"""
        logger.info("HybridMemory 插件正在停止...")
        
        # 取消后台任务
        if self._background_tasks:
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # 停止 WebUI
        await self._stop_webui()
        
        # 关闭长期记忆引擎
        if self.long_term_memory:
            await self.long_term_memory.close()
        
        # 关闭短期记忆
        if self.short_term_memory:
            self.short_term_memory.close()
        
        logger.info("HybridMemory 插件已停止")
