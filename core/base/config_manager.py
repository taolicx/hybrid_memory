"""配置管理模块"""
from typing import Any


class ConfigManager:
    """配置管理器"""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @property
    def webui_settings(self) -> dict[str, Any]:
        """WebUI 设置"""
        return {
            "enabled": self.config.get("webui_enabled", True),
            "host": self.config.get("webui_host", "0.0.0.0"),
            "port": self.config.get("webui_port", 9241),
            "username": self.config.get("webui_username", "admin"),
            "password": self.config.get("webui_password", "admin"),
        }

    @property
    def embedding_provider(self) -> str:
        """Embedding Provider"""
        return self.config.get("embedding_provider", "")

    @property
    def llm_provider(self) -> str:
        """LLM Provider"""
        return self.config.get("llm_provider", "")

    @property
    def summary_threshold(self) -> int:
        """记忆总结阈值（消息数）"""
        return self.config.get("summary_threshold", 20)

    @property
    def max_short_term_messages(self) -> int:
        """短期记忆最大消息数"""
        return self.config.get("max_messages", 50)

    @property
    def memory_decay_enabled(self) -> bool:
        """是否启用记忆衰减"""
        return self.config.get("decay_enabled", True)

    @property
    def memory_decay_days(self) -> int:
        """记忆衰减天数"""
        return self.config.get("decay_days", 30)

    @property
    def retrieval_top_k(self) -> int:
        """检索返回结果数"""
        return self.config.get("retrieval_top_k", 5)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)