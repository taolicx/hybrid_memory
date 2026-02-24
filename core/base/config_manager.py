"""配置管理模块"""
from typing import Any


class ConfigManager:
    """配置管理器"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        
        # 长期记忆配置
        self.long_term_config = config.get("long_term_memory", {})
        
        # 短期记忆配置
        self.short_term_config = config.get("short_term_memory", {})
        
        # WebUI 配置
        self.webui_config = config.get("webui", {})

    @property
    def webui_settings(self) -> dict[str, Any]:
        """WebUI 设置"""
        return {
            "enabled": self.webui_config.get("enabled", True),
            "host": self.webui_config.get("host", "127.0.0.1"),
            "port": self.webui_config.get("port", 9241),
            "username": self.webui_config.get("username", "admin"),
            "password": self.webui_config.get("password", "admin"),
        }

    @property
    def embedding_provider(self) -> dict[str, Any]:
        """Embedding Provider 配置"""
        return self.long_term_config.get("embedding_provider", {})

    @property
    def llm_provider(self) -> dict[str, Any]:
        """LLM Provider 配置"""
        return self.long_term_config.get("llm_provider", {})

    @property
    def summary_threshold(self) -> int:
        """记忆总结阈值（消息数）"""
        return self.short_term_config.get("summary_threshold", 20)

    @property
    def max_short_term_messages(self) -> int:
        """短期记忆最大消息数"""
        return self.short_term_config.get("max_messages", 50)

    @property
    def memory_decay_enabled(self) -> bool:
        """是否启用记忆衰减"""
        return self.long_term_config.get("decay_enabled", True)

    @property
    def memory_decay_days(self) -> int:
        """记忆衰减天数"""
        return self.long_term_config.get("decay_days", 30)

    @property
    def retrieval_top_k(self) -> int:
        """检索返回结果数"""
        return self.long_term_config.get("retrieval_top_k", 5)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
