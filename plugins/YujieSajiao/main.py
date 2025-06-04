"""
御姐撒娇插件

随机返回一条御姐撒娇语音
"""

import os
import aiohttp
import subprocess
import uuid
import time
import traceback
from loguru import logger
import tomllib
from utils.decorators import *
from utils.plugin_base import PluginBase
from WechatAPI import WechatAPIClient


class YujieSajiao(PluginBase):
    description = "御姐撒娇插件"
    author = "老夏的金库"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        try:
            with open("plugins/YujieSajiao/config.toml", "rb") as f:
                config = tomllib.load(f)
            plugin_config = config["YujieSajiao"]
            self.enable = plugin_config["enable"]
            self.api_url = plugin_config["api_url"]
            self.trigger_words = plugin_config["trigger_words"]
            self.http_proxy = plugin_config.get("http_proxy", None)
            self.use_ffmpeg = plugin_config.get("use_ffmpeg", True)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            logger.error(f"加载御姐撒娇插件配置文件失败: {e}")
            raise

        # 创建缓存目录
        self.cache_dir = "plugins/YujieSajiao/cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息"""
        if not self.enable:
            return True  # 插件未启用，允许后续插件处理

        content = message["Content"].strip()

        # 检查是否包含触发词
        if not any(trigger in content for trigger in self.trigger_words):
            return True  # 不包含触发词，允许后续插件处理

        logger.info(f"[YujieSajiao] 收到触发消息: {content}")

        try:
            # 下载并处理语音文件
            voice_path = await self.download_and_process_voice()
            if voice_path:
                # 从文件读取语音数据
                with open(voice_path, "rb") as f:
                    voice_data = f.read()

                # 发送语音消息
                logger.info(f"[YujieSajiao] 开始发送语音消息: 接收者={message['FromWxid']}, 文件大小={len(voice_data)}字节")

                # 记录bot对象信息
                logger.info(f"[YujieSajiao] bot对象类型: {type(bot)}")
                logger.info(f"[YujieSajiao] bot.wxid: {bot.wxid}")

                # 记录send_voice_message方法的源码
                import inspect
                logger.info(f"[YujieSajiao] send_voice_message方法源码:\n{inspect.getsource(bot.send_voice_message)}")

                # 发送语音消息
                result = await bot.send_voice_message(message["FromWxid"], voice=voice_data, format="mp3")

                # 记录返回结果
                logger.info(f"[YujieSajiao] 语音发送结果: {result}")
                logger.info(f"[YujieSajiao] 成功发送御姐撒娇语音")

                # 删除临时文件
                try:
                    os.remove(voice_path)
                except Exception as e:
                    logger.warning(f"[YujieSajiao] 删除临时文件失败: {e}")

                # 成功发送语音后阻止后续插件处理
                return False
            else:
                await bot.send_text_message(message["FromWxid"], "获取御姐撒娇语音失败，请稍后再试~")
                logger.error("[YujieSajiao] 获取语音失败")
                return True  # 即使失败也允许后续插件处理
        except Exception as e:
            logger.error(f"[YujieSajiao] 处理消息异常: {e}")
            await bot.send_text_message(message["FromWxid"], f"获取御姐撒娇语音时出错: {str(e)}")
            return True  # 异常情况下允许后续插件处理

    async def download_and_process_voice(self) -> str:
        """下载并处理御姐撒娇语音

        Returns:
            str: 处理后的语音文件路径，如果失败则返回None
        """
        try:
            # 生成唯一的文件名
            timestamp = int(time.time())
            random_str = uuid.uuid4().hex[:8]
            original_file = os.path.join(self.cache_dir, f"original_{timestamp}_{random_str}.mp3")
            processed_file = os.path.join(self.cache_dir, f"processed_{timestamp}_{random_str}.mp3")

            logger.info(f"[YujieSajiao] 开始下载语音文件: URL={self.api_url}, 代理={self.http_proxy}")

            # 下载语音文件
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, proxy=self.http_proxy, timeout=30) as response:
                    if response.status == 200:
                        # 将下载的数据保存到文件
                        content = await response.read()
                        content_length = len(content)
                        logger.info(f"[YujieSajiao] 下载的数据大小: {content_length}字节")

                        with open(original_file, "wb") as f:
                            f.write(content)

                        logger.info(f"[YujieSajiao] 成功下载语音文件到: {original_file}")

                        # 检查文件是否存在
                        if not os.path.exists(original_file):
                            logger.error(f"[YujieSajiao] 文件保存失败，文件不存在: {original_file}")
                            return None

                        # 检查文件大小
                        file_size = os.path.getsize(original_file)
                        logger.info(f"[YujieSajiao] 保存的文件大小: {file_size}字节")

                        # 如果配置为使用ffmpeg处理文件
                        if self.use_ffmpeg:
                            # 检查ffmpeg是否可用
                            if not self._check_ffmpeg():
                                logger.warning("[YujieSajiao] ffmpeg不可用，将直接使用原始文件")
                                return original_file

                            # 使用ffmpeg处理文件
                            logger.info(f"[YujieSajiao] 开始处理语音文件: {original_file} -> {processed_file}")
                            if self._process_audio_with_ffmpeg(original_file, processed_file):
                                logger.info(f"[YujieSajiao] 成功处理语音文件: {processed_file}")
                                return processed_file
                            else:
                                logger.warning("[YujieSajiao] 处理语音文件失败，将使用原始文件")
                                return original_file
                        else:
                            # 不使用ffmpeg，直接返回原始文件
                            logger.info("[YujieSajiao] 不使用ffmpeg处理，直接使用原始文件")
                            return original_file
                    else:
                        logger.error(f"[YujieSajiao] 下载语音失败，状态码: {response.status}")
                        # 尝试获取响应内容
                        try:
                            response_text = await response.text()
                            logger.error(f"[YujieSajiao] 响应内容: {response_text}")
                        except Exception as e:
                            logger.error(f"[YujieSajiao] 无法获取响应内容: {e}")
                        return None
        except Exception as e:
            logger.error(f"[YujieSajiao] 下载或处理语音异常: {e}")
            logger.error(f"[YujieSajiao] 异常详情: {traceback.format_exc()}")
            return None

    def _check_ffmpeg(self) -> bool:
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"[YujieSajiao] 检查ffmpeg异常: {e}")
            return False

    def _process_audio_with_ffmpeg(self, input_file: str, output_file: str) -> bool:
        """使用ffmpeg处理音频文件

        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径

        Returns:
            bool: 处理是否成功
        """
        try:
            # 记录输入文件信息
            input_file_size = os.path.getsize(input_file)
            logger.info(f"[YujieSajiao] 输入文件大小: {input_file_size}字节")

            # 使用ffmpeg将音频转换为标准MP3格式
            command = [
                "ffmpeg", "-y", "-i", input_file,
                "-acodec", "libmp3lame", "-ar", "44100", "-ab", "192k",
                "-ac", "2", output_file
            ]

            # 记录命令
            logger.info(f"[YujieSajiao] ffmpeg命令: {' '.join(command)}")

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                # 记录输出文件信息
                output_file_size = os.path.getsize(output_file)
                logger.info(f"[YujieSajiao] 输出文件大小: {output_file_size}字节")

                # 获取音频时长
                try:
                    duration_command = [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        output_file
                    ]
                    duration_result = subprocess.run(duration_command, capture_output=True, text=True)
                    if duration_result.returncode == 0:
                        duration = float(duration_result.stdout.strip())
                        logger.info(f"[YujieSajiao] 音频时长: {duration}秒")
                except Exception as e:
                    logger.error(f"[YujieSajiao] 获取音频时长失败: {e}")

                return True
            else:
                logger.error(f"[YujieSajiao] ffmpeg处理失败: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"[YujieSajiao] 处理音频异常: {e}")
            return False
