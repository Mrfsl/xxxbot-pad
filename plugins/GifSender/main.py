import os
import base64
from loguru import logger
from typing import Dict, Any

from WechatAPI import WechatAPIClient
from utils.plugin_base import PluginBase
from utils.decorators import on_text_message

class GifSender(PluginBase):
    """动图发送测试插件"""

    def __init__(self):
        super().__init__()
        self.name = "GifSender"
        self.description = "测试动图发送功能"
        self.version = "0.1.0"
        self.author = "Augment Agent"
        self.enable = True

        # 创建gifs目录用于存放动图文件
        self.gifs_dir = os.path.join(os.path.dirname(__file__), "gifs")
        os.makedirs(self.gifs_dir, exist_ok=True)
        logger.info(f"动图目录创建成功: {self.gifs_dir}")

    @on_text_message
    async def list_gifs(self, bot: WechatAPIClient, message: Dict[str, Any]) -> bool:
        """列出动图目录中的文件"""
        if not self.enable:
            return True

        content = str(message.get("Content", "")).strip()
        if content != "动图列表":
            return True

        # 获取发送者wxid
        from_wxid = message.get("FromWxid")

        try:
            # 获取gifs目录中的所有文件
            files = [f for f in os.listdir(self.gifs_dir)
                    if f.lower().endswith(('.gif', '.mp4', '.webp'))]

            if not files:
                await bot.send_text_message(from_wxid, "动图目录中没有动图文件。\n请将GIF、MP4或WEBP文件放入以下目录：\n" + self.gifs_dir)
                return False

            # 构造文件列表消息
            file_list = "动图目录中的文件列表：\n"
            for i, file in enumerate(files, 1):
                file_path = os.path.join(self.gifs_dir, file)
                file_size = os.path.getsize(file_path)
                file_list += f"{i}. {file} ({self._format_size(file_size)})\n"

            file_list += "\n要发送动图，请使用命令：发送动图 [文件名]"

            await bot.send_text_message(from_wxid, file_list)
            return False
        except Exception as e:
            logger.error(f"获取动图列表失败: {e}")
            await bot.send_text_message(from_wxid, f"获取动图列表失败: {e}")
            return False

    @on_text_message
    async def send_gif(self, bot: WechatAPIClient, message: Dict[str, Any]) -> bool:
        """发送动图功能"""
        if not self.enable:
            return True

        content = str(message.get("Content", "")).strip()
        # 检查是否是发送动图命令
        if content.startswith("发送动图"):
            # 如果是简单的发送动图命令，则继续处理
            pass
        else:
            return True

        # 获取发送者wxid
        from_wxid = message.get("FromWxid")

        # 解析命令，检查是否指定了文件名
        parts = content.split(" ", 1)
        if len(parts) > 1 and parts[1].strip():
            # 指定了文件名
            specified_file = parts[1].strip()
            file_path = os.path.join(self.gifs_dir, specified_file)
            if not os.path.exists(file_path):
                await bot.send_text_message(from_wxid, f"指定的文件 '{specified_file}' 不存在。\n请使用命令：动图列表 查看可用文件。")
                return False
            logger.info(f"使用指定动图文件: {file_path}")
        else:
            # 没有指定文件名，检查目录中是否有动图文件
            files = [f for f in os.listdir(self.gifs_dir)
                    if f.lower().endswith(('.gif', '.mp4', '.webp'))]
            if files:
                file_path = os.path.join(self.gifs_dir, files[0])
                logger.info(f"使用动图目录中的第一个文件: {file_path}")
            else:
                await bot.send_text_message(from_wxid, "动图目录中没有动图文件。\n请使用命令：动图列表 查看可用文件。")
                return False

        try:
            # 发送提示消息
            await bot.send_text_message(from_wxid, "开始发送动图...")

            # 读取文件内容
            with open(file_path, "rb") as f:
                file_data = f.read()

            # 获取文件名和扩展名
            file_name = os.path.basename(file_path)
            file_extension = os.path.splitext(file_name)[1][1:].lower()  # 去掉点号

            # 根据文件类型选择发送方法
            if file_extension == 'gif':
                # 发送GIF动图
                await self._send_gif(bot, from_wxid, file_path, file_data)
            elif file_extension in ['mp4', 'webp']:
                # 发送视频
                await self._send_video(bot, from_wxid, file_path, file_data)
            else:
                await bot.send_text_message(from_wxid, f"不支持的文件类型: {file_extension}")

            return False
        except Exception as e:
            logger.error(f"发送动图失败: {e}")
            await bot.send_text_message(from_wxid, f"发送动图失败: {e}")
            return False

    async def _send_gif(self, bot: WechatAPIClient, to_wxid: str, file_path: str, file_data: bytes):
        """发送GIF动图"""
        try:
            # 转换为base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            # 上传图片
            logger.info(f"开始上传GIF动图: {file_path}")

            # 使用发送图片的API
            result = await bot.send_image_message(to_wxid, file_data)
            logger.info(f"GIF动图发送结果: {result}")

            # 发送成功提示
            await bot.send_text_message(to_wxid, f"GIF动图 {os.path.basename(file_path)} 发送成功！")
        except Exception as e:
            logger.error(f"发送GIF动图失败: {e}")
            raise

    async def _send_video(self, bot: WechatAPIClient, to_wxid: str, file_path: str, file_data: bytes):
        """发送视频"""
        try:
            # 转换为base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            # 上传视频
            logger.info(f"开始上传视频: {file_path}")

            # 使用发送视频的API
            # 注意：这里需要提供视频时长，但我们无法直接获取，所以使用一个默认值
            duration = 3  # 默认3秒

            # 创建一个空的缩略图
            thumbnail_base64 = ""

            # 发送视频
            result = await bot.send_video_message(to_wxid, file_data, thumbnail_base64, duration)
            logger.info(f"视频发送结果: {result}")

            # 发送成功提示
            await bot.send_text_message(to_wxid, f"视频 {os.path.basename(file_path)} 发送成功！")
        except Exception as e:
            logger.error(f"发送视频失败: {e}")
            raise

    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
