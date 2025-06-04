import os
import tomllib
from typing import Dict, List, Optional
import re

from loguru import logger
from utils.plugin_base import PluginBase
from utils.decorators import on_text_message, on_at_message, on_xml_message
from WechatAPI.Client import WechatAPIClient


class AtAllFilter(PluginBase):
    """
    过滤@所有人消息的插件

    当在群聊中收到@所有人的消息时，阻止消息传递到其他插件
    """
    description = "@所有人消息过滤器"
    author = "xxxbot-pad"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", True)  # 读取插件开关

            # 读取过滤配置
            filter_config = config.get("filter", {})
            self.log_filtered = filter_config.get("log_filtered", True)  # 是否记录被过滤的消息

        except Exception as e:
            logger.error(f"加载AtAllFilter配置文件失败: {str(e)}")
            self.enable = True  # 默认启用
            self.log_filtered = True  # 默认记录

    async def async_init(self):
        """异步初始化"""
        return

    def is_at_all_message(self, message: dict) -> bool:
        """
        检查消息是否包含@所有人

        Args:
            message: 消息数据

        Returns:
            bool: 如果消息包含@所有人，返回True，否则返回False
        """
        # 检查是否是群聊消息
        if not message.get("IsGroup", False):
            return False

        # 获取消息内容
        content = message.get("Content", "")

        # 检查消息内容是否包含@所有人或@全体成员
        if "@所有人" in content or "@全体成员" in content:
            return True

        # 检查at_list是否包含"所有人"或"全体成员"
        at_list = message.get("AtList", [])
        if isinstance(at_list, list) and ("所有人" in at_list or "全体成员" in at_list):
            return True

        # 检查MsgSource是否包含atuserlist=notify@all
        msg_source = message.get("MsgSource", "")
        if "notify@all" in msg_source:
            return True

        return False

    @on_text_message(priority=100)  # 设置最高优先级，确保在其他插件之前处理
    async def filter_text_message(self, bot: WechatAPIClient, message: dict):
        """
        过滤文本消息中的@所有人

        Args:
            bot: 微信API客户端
            message: 消息数据

        Returns:
            bool: 如果消息包含@所有人，返回False阻止继续处理，否则返回True
        """
        if not self.enable:
            return True  # 如果插件未启用，允许消息继续传递

        # 检查消息是否包含@所有人
        if self.is_at_all_message(message):
            if self.log_filtered:
                logger.info(f"[AtAllFilter] 过滤@所有人消息: {message.get('Content', '')[:50]}...")
            return False  # 阻止消息继续传递

        return True  # 允许消息继续传递

    @on_at_message(priority=100)  # 设置最高优先级，确保在其他插件之前处理
    async def filter_at_message(self, bot: WechatAPIClient, message: dict):
        """
        过滤@消息中的@所有人

        Args:
            bot: 微信API客户端
            message: 消息数据

        Returns:
            bool: 如果消息包含@所有人，返回False阻止继续处理，否则返回True
        """
        if not self.enable:
            return True  # 如果插件未启用，允许消息继续传递

        # 检查消息是否包含@所有人
        if self.is_at_all_message(message):
            if self.log_filtered:
                logger.info(f"[AtAllFilter] 过滤@所有人消息: {message.get('Content', '')[:50]}...")
            return False  # 阻止消息继续传递

        return True  # 允许消息继续传递

    @on_xml_message(priority=100)  # 设置最高优先级，确保在其他插件之前处理
    async def filter_xml_message(self, bot: WechatAPIClient, message: dict):
        """
        过滤XML消息中的@所有人

        Args:
            bot: 微信API客户端
            message: 消息数据

        Returns:
            bool: 如果消息包含@所有人，返回False阻止继续处理，否则返回True
        """
        if not self.enable:
            return True  # 如果插件未启用，允许消息继续传递

        # 检查消息是否包含@所有人
        if self.is_at_all_message(message):
            if self.log_filtered:
                logger.info(f"[AtAllFilter] 过滤@所有人XML消息: {message.get('Content', '')[:50]}...")
            return False  # 阻止消息继续传递

        return True  # 允许消息继续传递
