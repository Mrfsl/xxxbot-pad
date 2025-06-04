# plugins/keyword_reply/main.py
import asyncio
import os
import traceback

import tomllib
import aiohttp
from loguru import logger
from WechatAPI import WechatAPIClient
from utils.decorators import on_text_message
from utils.plugin_base import PluginBase
from io import BytesIO

from typing import Optional



class KeywordReplyPlugin(PluginBase):
    """关键词自动回复插件（支持网页截图）"""

    description = "关键词自动回复插件,支持网页截图"
    author = "墨染"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.keyword_responses = {}
        self.apiflash_api_key = ""  # 从配置读取
        self.apiflash_endpoint = "https://api.apiflash.com/v1/urltoimage"

        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            self.enable = config.get("basic", {}).get("enable", False)
            self.apiflash_api_key = config.get("apiflash", {}).get("api_key", "")

            # 自定义截图服务 api
            self.puppeteer_screenshot_api = config.get("puppeteer", {}).get("puppeteer_screenshot_api", "")

            # 读取关键词配置
            self.keyword_responses = config.get("keywords", {})

        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            self.enable = False

    """
        apiflash 截图服务（在config.toml中配置api_key）
    """
    # async def capture_webpage(self, url: str) -> Optional[bytes]:
    #     """捕获网页截图（强制中文版）"""
    #     params = {
    #         "access_key": self.apiflash_api_key,
    #         "url": url,
    #         "format": "png",
    #         "quality": 100,
    #         "delay": 3,  # 等待页面加载完成
    #         "fresh": "true"  # 忽略缓存
    #     }
    #
    #     # 关键修改：添加中文请求头
    #     headers = {
    #         "Accept-Language": "zh-CN,zh;q=0.9",  # 强制优先返回中文
    #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    #         # 模拟中文浏览器
    #     }
    #
    #     try:
    #         async with aiohttp.ClientSession(headers=headers) as session:
    #             async with session.get(
    #                     "https://api.apiflash.com/v1/urltoimage",
    #                     params=params,
    #                     timeout=aiohttp.ClientTimeout(total=15)
    #             ) as resp:
    #                 if resp.status == 200:
    #                     return await resp.read()
    #                 logger.error(f"APIFlash错误: HTTP {resp.status}")
    #     except Exception as e:
    #         logger.error(f"截图捕获失败: {str(e)}")
    #
    #     return None



    """
        自己的截图服务
    """

    async def capture_webpage(self, url: str, max_retries: int = 2) -> Optional[bytes]:
        """使用自托管Puppeteer服务捕获网页截图（强制中文版）"""
        params = {
            "url": url,
            "format": "png",
            "fullPage": "true",
            "width": 1920,
            "height": 1080,
            "timeout": 60000  # 通知服务端延长超时
        }

        headers = {
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(
                            self.puppeteer_screenshot_api,
                            params=params,
                            timeout=aiohttp.ClientTimeout(total=60)  # 客户端超时60秒
                    ) as resp:
                        if resp.status == 200:
                            # 关键点：确保以二进制形式读取响应
                            return await resp.read()

                        error_detail = await resp.text()
                        logger.error(f"截图服务返回错误: HTTP {resp.status}, Body: {error_detail}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"截图请求超时（尝试 {attempt + 1}/{max_retries}）")
                if attempt == max_retries - 1:
                    logger.error("截图服务连续超时，请检查服务状态")
                    return None
                await asyncio.sleep(2)  # 延迟后重试

            except Exception as e:
                logger.error(f"请求失败: {type(e).__name__}, {str(e)}")
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                return None

        return None


    @on_text_message(priority=50)
    async def handle_text_message(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return True

        content = message["Content"].strip()
        sender = message["FromWxid"]  # 或 message['FromUserName'] 根据实际字段

        for keyword, response in self.keyword_responses.items():
            if keyword == content:   # 严格相等
                logger.info(f"检测到关键词: {keyword}")

                if response.startswith(("http://", "https://")):
                    # 发送等待提示
                    await bot.send_text_message(sender, "熊老板正在查找，笨蛋鱿别急~\n新的一天要加油哦！")

                    # 获取截图二进制数据
                    screenshot = await self.capture_webpage(response)
                    if not screenshot:
                        await bot.send_text_message(sender, "笨蛋熊老板没查到，晚点试试吧~呜呜呜=|_|=")
                        return False

                    try:
                        # 关键修改：完全适配微信API的参数要求
                        result = await bot.send_image_message(
                            wxid=sender,
                            image=screenshot  # 直接传递二进制数据
                        )
                        logger.success(f"图片发送成功，返回结果: {result}")
                    except Exception as e:
                        logger.error(f"发送失败: {type(e).__name__}: {str(e)}")
                        await bot.send_text_message(sender, "图片发送过程中被垃圾桶导弹命中=|_|=")
                else:
                    await bot.send_text_message(sender, response)

                return False
        return True
