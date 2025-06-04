# plugins/screenshot_plugin.py
import aiohttp
import asyncio
from loguru import logger
from pathlib import Path


class ScreenshotPlugin:
    def __init__(self, bot):
        self.bot = bot
        self.config_path = Path(__file__).parent.parent / "main_config.toml"
        self.api_key = self._load_config()

    def _load_config(self):
        """从配置文件读取API FLASH配置"""
        try:
            with open(self.config_path, "rb") as f:
                config = tomllib.load(f)
            return config.get("APIFLASH", {}).get("api_key", "")
        except Exception as e:
            logger.error(f"读取配置失败: {e}")
            return ""

    async def on_message(self, message: dict):
        """消息处理入口"""
        content = message.get('Content', '')
        group_id = message.get('FromGroup', '')

        if "截图" in content:  # 触发关键词
            await self.process_screenshot(group_id)

    async def process_screenshot(self, group_id):
        """完整的截图处理流程"""
        try:
            # 获取截图
            screenshot_data = await self.get_apiflash_screenshot()
            if not screenshot_data:
                return

            # 发送到群聊
            await self.send_to_wechat(group_id, screenshot_data)

        except Exception as e:
            logger.error(f"截图处理失败: {e}")

    async def get_apiflash_screenshot(self):
        """调用APIFLASH API获取截图"""
        api_url = "https://api.apiflash.com/v1/urltoimage"
        params = {
            "access_key": self.api_key,
            "url": "https://example.com",
            "format": "png",
            "quality": 100,
            "delay": 5
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        return await response.read()
                    logger.error(f"API请求失败: {response.status}")
            except aiohttp.ClientError as e:
                logger.error(f"网络请求异常: {e}")
            return None

    async def send_to_wechat(self, group_id, image_data):
        """通过微信API发送图片"""
        try:
            # 使用XYBot的发送图片接口
            result = await self.bot.send_image(
                receiver=group_id,
                image_data=image_data,
                image_type="png"
            )

            if result.get("code") == 0:
                logger.success("图片发送成功")
            else:
                logger.error(f"发送失败: {result.get('msg')}")
        except Exception as e:
            logger.error(f"微信接口调用异常: {e}")


def setup(bot):
    """插件标准初始化接口"""
    plugin = ScreenshotPlugin(bot)
    return {"message_handler": plugin.on_message}
