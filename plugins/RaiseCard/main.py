import io
import requests
import os
from loguru import logger
from WechatAPI import WechatAPIClient
from utils.plugin_base import PluginBase
from utils.decorators import on_text_message, on_at_message

class RaiseCard(PluginBase):
    description = "举牌插件 - 生成举牌图片"
    author = "XXXBot"
    version = "1.1.0"

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.suyanw.cn/api/zt.php"
        self.hsjp_api_url = "https://api.suyanw.cn/api/hsjp/"
        logger.info("举牌插件已加载")

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        content = message.get("Content", "").strip()

        # 检查是否是普通举牌命令
        command_found = False
        is_hsjp = False  # 是否是黑丝举牌
        text = ""

        # 检查普通举牌
        for cmd in ["举牌", "举牌子", "举个牌", "举个牌子"]:
            if content.startswith(cmd):
                command_found = True
                text = content[len(cmd):].strip()
                break

        # 检查黑丝举牌
        if not command_found:
            for cmd in ["黑丝举牌", "黑丝举牌子", "黑丝举个牌", "黑丝举个牌子"]:
                if content.startswith(cmd):
                    command_found = True
                    is_hsjp = True
                    text = content[len(cmd):].strip()
                    break

        if not command_found:
            return True  # 允许其他插件处理

        # 如果没有文本，返回帮助信息
        if not text:
            if is_hsjp:
                await bot.send_text_message(message["FromWxid"], "请输入要黑丝举牌的内容，例如：\n黑丝举牌 第一行|第二行|第三行\n或者：黑丝举牌 第一行|第二行\n注意使用|分隔每行文本")
            else:
                await bot.send_text_message(message["FromWxid"], "请输入要举牌的内容，例如：举牌 XXXBot")
            return False  # 阻止其他插件处理

        # 获取举牌图片
        try:
            if is_hsjp:
                image_data = await self.get_hsjp_image(text)
            else:
                image_data = await self.get_card_image(text)

            if image_data:
                await bot.send_image_message(message["FromWxid"], image_data)
            else:
                await bot.send_text_message(message["FromWxid"], "生成举牌图片失败，请稍后再试")
            return False  # 阻止其他插件处理
        except Exception as e:
            logger.error(f"举牌插件错误: {e}")
            await bot.send_text_message(message["FromWxid"], f"生成举牌图片时出错: {str(e)}")
            return False  # 阻止其他插件处理

    async def get_card_image(self, text):
        """获取普通举牌图片"""
        try:
            # 使用 API 获取举牌图片
            response = requests.get(self.api_url, params={"msg": text})
            response.raise_for_status()

            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                logger.info(f"成功获取举牌图片，内容类型: {content_type}")
                return response.content

            # 如果返回的是 JSON，尝试从中提取图片 URL
            try:
                data = response.json()
                image_url = data.get("image")
                if image_url:
                    # 下载图片
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    logger.info(f"成功从 JSON 响应中获取并下载举牌图片")
                    return img_response.content
            except ValueError:
                # 如果不是 JSON，直接使用响应内容
                logger.info("响应不是 JSON 格式，直接使用响应内容作为图片")
                return response.content

            logger.error("无法从 API 响应中获取图片")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"请求举牌 API 失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取举牌图片时出错: {e}")
            return None

    async def get_hsjp_image(self, text):
        """获取黑丝举牌图片"""
        try:
            # 处理文本，分割成多行
            lines = text.split('|')

            # 准备参数
            params = {
                "rgb1": "0",  # 默认黑色
                "rgb2": "0",
                "rgb3": "0"
            }

            # 根据行数添加参数
            if len(lines) >= 1:
                params["msg"] = lines[0]
            if len(lines) >= 2:
                params["msg1"] = lines[1]
            if len(lines) >= 3:
                params["msg2"] = lines[2]

            # 请求 API
            logger.info(f"请求黑丝举牌 API，参数: {params}")
            response = requests.get(self.hsjp_api_url, params=params)
            response.raise_for_status()

            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                logger.info(f"成功获取黑丝举牌图片，内容类型: {content_type}")
                return response.content

            # 如果返回的是 JSON，尝试从中提取图片 URL
            try:
                data = response.json()
                image_url = data.get("image")
                if image_url:
                    # 下载图片
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    logger.info(f"成功从 JSON 响应中获取并下载黑丝举牌图片")
                    return img_response.content
            except ValueError:
                # 如果不是 JSON，直接使用响应内容
                logger.info("响应不是 JSON 格式，直接使用响应内容作为图片")
                return response.content

            logger.error("无法从 API 响应中获取黑丝举牌图片")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"请求黑丝举牌 API 失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取黑丝举牌图片时出错: {e}")
            return None

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        content = message.get("Content", "").strip()

        # 检查是否是普通举牌命令
        command_found = False
        is_hsjp = False  # 是否是黑丝举牌
        text = ""

        # 检查普通举牌
        for cmd in ["举牌", "举牌子", "举个牌", "举个牌子"]:
            if content.startswith(cmd):
                command_found = True
                text = content[len(cmd):].strip()
                break

        # 检查黑丝举牌
        if not command_found:
            for cmd in ["黑丝举牌", "黑丝举牌子", "黑丝举个牌", "黑丝举个牌子"]:
                if content.startswith(cmd):
                    command_found = True
                    is_hsjp = True
                    text = content[len(cmd):].strip()
                    break

        if not command_found:
            return True  # 允许其他插件处理

        # 如果没有文本，返回帮助信息
        if not text:
            if is_hsjp:
                await bot.send_at_message(message["FromWxid"], "\n请输入要黑丝举牌的内容，例如：\n黑丝举牌 第一行|第二行|第三行\n或者：黑丝举牌 第一行|第二行\n注意使用|分隔每行文本", [message["SenderWxid"]])
            else:
                await bot.send_at_message(message["FromWxid"], "\n请输入要举牌的内容，例如：举牌 XXXBot", [message["SenderWxid"]])
            return False  # 阻止其他插件处理

        # 获取举牌图片
        try:
            if is_hsjp:
                image_data = await self.get_hsjp_image(text)
            else:
                image_data = await self.get_card_image(text)

            if image_data:
                await bot.send_image_message(message["FromWxid"], image_data)
            else:
                await bot.send_at_message(message["FromWxid"], "\n生成举牌图片失败，请稍后再试", [message["SenderWxid"]])
            return False  # 阻止其他插件处理
        except Exception as e:
            logger.error(f"举牌插件错误: {e}")
            await bot.send_at_message(message["FromWxid"], f"\n生成举牌图片时出错: {str(e)}", [message["SenderWxid"]])
            return False  # 阻止其他插件处理
