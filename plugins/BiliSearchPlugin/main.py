import asyncio
import json
import re
import tomllib
import traceback
from typing import List, Optional, Union

import aiohttp
import filetype
from loguru import logger
import speech_recognition as sr  # 导入speech_recognition
import os
from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase
import os
import base64
import asyncio
import shutil
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont  # 导入 PIL 库


class BiliSearchPlugin(PluginBase):
    """
    一个根据关键词搜索 BiliBili 视频链接并以文字形式发送给用户的插件，并支持播放指定编号的视频。
    """

    description = "一个根据关键词搜索BiliBili视频链接并以文字形式发送给用户的插件，并支持播放指定编号的视频"
    author = "老夏的金库"
    version = "2.4.0"

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.enable = self.config.get("enable", False)
        self.commands = self.config.get("commands", ["B站"])  # 修改为 B站
        self.api_url = self.config.get("api_url", "")
        self.play_command = self.config.get("play_command", "视频 ")
        self.search_results = {}  # 用于存储搜索结果，格式为 {chat_id: {keyword: [video_list]}}
        self.episode_results = {}  # 用于存储剧集结果，格式为 {chat_id: {video_index: [episode_list], start_index: int}}
        self.current_video_index = {}  # 用于记录当前用户选择的视频索引
        self.LIST_URL_KEY = "list_url"  # 定义 list_url 的 key 为常量
        self.RESULTS_PER_PAGE = 20  # 每页显示的结果数量
        self.PAGE_COMMANDS = ["第", "页", "上一页", "下一页", "最后一页"]  # 分页命令
        self.EPISODES_PER_BATCH = 20  # 每次发送的剧集数量

    def _load_config(self):
        """加载插件配置."""
        try:
            with open("plugins/BiliSearchPlugin/config.toml", "rb") as f:
                plugin_config = tomllib.load(f)
            config = plugin_config["BiliSearchPlugin"]
            logger.info("BiliSearchPlugin 插件配置加载成功")
            return config
        except FileNotFoundError:
            logger.error("BiliSearchPlugin 插件配置文件未找到，插件已禁用。")
            return {}
        except Exception as e:
            logger.exception(f"BiliSearchPlugin 插件初始化失败: {e}")
            return {}

    async def _search_video(self, keyword: str) -> Optional[dict]:
        """根据关键词搜索视频."""
        if not self.api_url:
            logger.error("API URL 未配置")
            return None

        try:
            url = f"{self.api_url}?msg={keyword}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 确保返回结果包含list_url
                        if data and data["code"] == 200 and "data" in data:
                            for item in data["data"]:
                                if self.LIST_URL_KEY not in item:
                                    logger.warning(f"API 返回结果缺少 {self.LIST_URL_KEY} 字段: {item}")
                        return data
                    else:
                        logger.error(f"搜索视频失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.exception(f"搜索视频过程中发生异常: {e}")
            return None

    async def _get_video_urls(self, list_url: str) -> Optional[List[str]]:
        """根据 list_url 获取视频链接列表"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(list_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "data" in data:
                            video_urls = [item.get("mp4") for item in data["data"] if item.get("mp4")]
                            return video_urls
                        else:
                            logger.warning(f"获取视频链接失败，API 返回错误: {data}")
                            return None
                    else:
                        logger.error(f"获取视频链接失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.exception(f"获取视频链接过程中发生异常: {e}")
            return None

    async def _get_episodes(self, list_url: str) -> Optional[List[str]]:
        """根据 list_url 获取视频的剧集列表"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(list_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "data" in data:
                            episodes = data["data"]
                            episode_titles = [f"第{i + 1}集 {ep.get('title', '')}".replace(f" {i + 1}", "") for i, ep in enumerate(episodes)]  # 添加剧集名字，并移除重复数字
                            return episode_titles
                        else:
                            logger.warning(f"获取剧集列表失败，API 返回错误: {data}")
                            return None
                    else:
                        logger.error(f"获取剧集列表失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.exception(f"获取剧集列表过程中发生异常: {e}")
            return None

    def get_number_emoji(self, num):
        """将数字转换为对应的 Emoji 序号"""
        num_str = str(num)
        emoji_dict = {
            '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣',
            '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣',
            '8': '8️⃣', '9': '9️⃣'
        }
        return ''.join(emoji_dict.get(digit, digit) for digit in num_str)

    async def _handle_play_command(self, bot: WechatAPIClient, chat_id: str, content: str) -> bool:
        """处理播放命令."""
        try:
            index_str = content.split()[1].strip()
            index = int(index_str)
            if chat_id in self.search_results:
                video_list = self.search_results[chat_id]["video_list"]
                if 1 <= index <= len(video_list):
                    video = video_list[index - 1]
                    list_url = video.get(self.LIST_URL_KEY)

                    if list_url:
                        # 检查是否已经获取过该视频的剧集信息
                        if chat_id in self.episode_results and index in self.episode_results[chat_id]:
                            episode_data = self.episode_results[chat_id][index]
                            episode_list = episode_data["episodes"]
                            start_index = episode_data["start_index"]
                            total_episodes = len(episode_list)
                            total_pages = (total_episodes + self.EPISODES_PER_BATCH - 1) // self.EPISODES_PER_BATCH
                            current_page = (start_index // self.EPISODES_PER_BATCH) + 1
                            end_index = min(start_index + self.EPISODES_PER_BATCH, total_episodes)
                            display_list = episode_list[start_index:end_index]

                            # 发送剧集列表供用户选择
                            response_text = f"🎬———{video['title']} ———🎬\n"
                            for i, episode in enumerate(display_list):
                                episode_number = start_index + i + 1
                                number_emoji = self.get_number_emoji(episode_number)
                                response_text += f"{number_emoji}. {episode}\n"

                            # 添加当前页码
                            page_emoji = self.get_number_emoji(current_page)
                            total_page_emoji = self.get_number_emoji(total_pages)
                            response_text += f"       🎞️{page_emoji}/{total_page_emoji}🎞️\n"

                            response_text += "_________________________\n"
                            response_text += f"🎵输入 “序号 + 数字” 选择剧集🎵\n"
                            navigation_tips = "🎵输入 “下一页” “上一页” “最后一页”🎵"  # 简化
                            response_text += navigation_tips
                            await bot.send_text_message(chat_id, response_text)
                            self.current_video_index[chat_id] = index
                            return False  # 阻止后续操作
                        else:
                            # 获取剧集信息
                            episode_list = await self._get_episodes(list_url)
                            if episode_list:
                                if chat_id not in self.episode_results:
                                    self.episode_results[chat_id] = {}

                                self.episode_results[chat_id][index] = {
                                    "episodes": episode_list,
                                    "start_index": 0,
                                }
                                start_index = 0
                                total_episodes = len(episode_list)
                                total_pages = (total_episodes + self.EPISODES_PER_BATCH - 1) // self.EPISODES_PER_BATCH
                                current_page = 1
                                end_index = min(start_index + self.EPISODES_PER_BATCH, total_episodes)
                                display_list = episode_list[start_index:end_index]

                                # 发送剧集列表供用户选择
                                response_text = f"🎬———{video['title']} ———🎬\n"
                                for i, episode in enumerate(display_list):
                                    episode_number = start_index + i + 1
                                    number_emoji = self.get_number_emoji(episode_number)
                                    response_text += f"{number_emoji}. {episode}\n"

                                # 添加当前页码
                                page_emoji = self.get_number_emoji(current_page)
                                total_page_emoji = self.get_number_emoji(total_pages)
                                response_text += f"       🎞️{page_emoji}/{total_page_emoji}🎞️\n"

                                response_text += "_________________________\n"
                                response_text += f"🎵输入 “序号 + 数字” 选择剧集🎵\n"
                                navigation_tips = "🎵输入 “下一页” “上一页” “最后一页”🎵"  # 简化
                                response_text += navigation_tips
                                await bot.send_text_message(chat_id, response_text)
                                self.current_video_index[chat_id] = index
                                return False  # 阻止后续操作
                            else:
                                await bot.send_text_message(chat_id, "无法获取该视频的剧集信息。")
                                return False
                    else:
                        await bot.send_text_message(chat_id, "视频信息中缺少 list_url。")
                else:
                    await bot.send_text_message(chat_id, "无效的视频编号。")
            else:
                await bot.send_text_message(chat_id, "请先搜索视频。")
            return False
        except ValueError:
            # 尝试直接解析集数
            try:
                episode_number = int(index_str)
                if chat_id in self.current_video_index:
                    video_index = self.current_video_index[chat_id]
                    episode_data = self.episode_results[chat_id][video_index]
                    episode_list = episode_data["episodes"]
                    if 1 <= episode_number <= len(episode_list):
                        content = f"序号 {episode_number}"
                         # 递归调用，传递正确的序号选择消息
                        return await self._handle_episode_selection(bot, chat_id, content) 
                    else:
                        await bot.send_text_message(chat_id, "无效的剧集编号。")
                        return False
                else:
                    await bot.send_text_message(chat_id, "请先选择视频并查看剧集列表。")
                    return False

            except ValueError:
                await bot.send_text_message(chat_id, "请输入有效的数字编号。")
                return False
        except Exception as e:
            logger.exception(f"处理视频卡片消息过程中发生异常: {e}")
            await bot.send_text_message(chat_id, f"处理视频卡片消息过程中发生异常: {e}")
            return False

    async def _handle_episode_selection(self, bot: WechatAPIClient, chat_id: str, content: str) -> bool:
        """处理剧集选择命令，并发送卡片消息."""
        try:
            if chat_id in self.current_video_index:
                video_index = self.current_video_index[chat_id]
                episode_index = int(content.split()[1].strip())
                if (
                    chat_id in self.search_results
                    and chat_id in self.episode_results
                    and video_index in self.episode_results[chat_id]
                ):
                    video_list = self.search_results[chat_id]["video_list"]
                    video = video_list[video_index - 1]
                    list_url = video.get(self.LIST_URL_KEY)

                    episode_data = self.episode_results[chat_id][video_index]
                    episode_list = episode_data["episodes"]
                    start_index = episode_data["start_index"]
                    total_episodes = len(episode_list)
                    total_pages = (total_episodes + self.EPISODES_PER_BATCH - 1) // self.EPISODES_PER_BATCH
                    current_page = (start_index // self.EPISODES_PER_BATCH) + 1

                    if 1 <= episode_index <= len(episode_list):
                        video_urls = await self._get_video_urls(list_url)
                        if video_urls and len(video_urls) > episode_index - 1:
                            video_url = video_urls[episode_index - 1]

                            # 获取剧集信息
                            episode_title = episode_list[episode_index - 1]

                            # 从 video 变量中获取信息
                            title = f"🎉{video['title']} - {episode_title}🎉"  # 视频标题 + 剧集标题
                            description_text = "点开后用浏览器观看哦 🎥\n温馨提示：需要等待2秒再点击哦"  # 新增提示语，用🎥装饰
                            video_description = video.get("description", "")  # 视频描述，如果没有则为空字符串
                            description = f"{description_text}\n{video_description}"  # 将固定文本和视频描述组合起来
                            thumbnail = video.get("cover", "")  # 视频封面，如果没有则为空字符串

                            # 构建跳转链接
                            url = video_url  # 直接使用视频播放链接作为跳转链接

                            # 构造XML消息
                            xml = f"""<appmsg appid="wx79f2c4418704b4f8" sdkver="0"><title>{title}</title><des>{description}</des><action>view</action><type>5</type><showtype>0</showtype><content/><url>{url}</url><dataurl/><lowurl/><lowdataurl/><recorditem/><thumburl>{thumbnail}</thumburl><messageaction/><laninfo/><extinfo/><sourceusername/><sourcedisplayname/><commenturl/><appattach><totallen>0</totallen><attachid/><emoticonmd5/><fileext/><aeskey/></appattach><webviewshared><publisherId/><publisherReqId>0</publisherReqId></webviewshared><weappinfo><pagepath/><username/><appid/><appservicetype>0</appservicetype></weappinfo><websearch/><songalbumurl/></appmsg><fromusername>{bot.wxid}</fromusername><scene>0</scene><appinfo><version>1</version><appname/></appinfo><commenturl/>"""  #注意：type=5 是网页链接

                            await bot.send_app_message(chat_id, xml, 5)  # type=5 是网页链接
                            logger.info(f"发送卡片消息到 {chat_id}: {title}")

                            # 发送视频链接
                            await bot.send_text_message(chat_id, f"📺 视频链接：{video_url}")
                            return False
                        else:
                            await bot.send_text_message(chat_id, "无法获取该集视频链接或该视频没有播放资源。")
                            return False
                    else:
                        await bot.send_text_message(chat_id, "无效的剧集编号。")
                        return False
                else:
                    await bot.send_text_message(chat_id, "请先选择视频并查看剧集列表。")
                    return False
            else:
                await bot.send_text_message(chat_id, "请先选择视频。")
                return False
        except ValueError:
            await bot.send_text_message(chat_id, "请输入有效的剧集数字编号。")
            return False
        except Exception as e:
            logger.exception(f"处理视频卡片消息过程中发生异常: {e}")
            await bot.send_text_message(chat_id, f"处理视频卡片消息过程中发生异常: {e}")
            return False

    async def _handle_search_command(self, bot: WechatAPIClient, chat_id: str, content: str) -> bool:
        """处理搜索命令."""
        parts = content.split()
        if len(parts) < 1:  # 修改判断条件
            await bot.send_text_message(chat_id, "请输入要搜索的关键词。")
            return False

        keyword = " ".join(parts[1:])  # 获取关键词
        # 如果没有关键词，提示
        if not keyword:
            await bot.send_text_message(chat_id, "请输入要搜索的关键词。")
            return False

        try:
            search_result = await self._search_video(keyword)

            if search_result and search_result["code"] == 200 and search_result["data"]:
                video_list = search_result["data"]
                total_videos = len(search_result["data"])
                total_pages = (total_videos + self.RESULTS_PER_PAGE - 1) // self.RESULTS_PER_PAGE
                current_page = 1  # 默认显示第一页
                start_index = (current_page - 1) * self.RESULTS_PER_PAGE
                end_index = min(current_page * self.RESULTS_PER_PAGE, total_videos)
                display_list = video_list[start_index:end_index]

                response_text = f"🎬———B站视频———🎬\n"
                for i, video in enumerate(display_list):
                    number_emoji = self.get_number_emoji(start_index + i + 1)
                    video_type_emoji = "🎞️" if "剧场版" in video["title"] else "🎞️"
                    response_text += f"{number_emoji}. {video['title']}{video_type_emoji}\n"
                response_text += "_________________________\n"
                response_text += f"🎵输入 “{self.play_command.strip()}+序号” 选择视频🎵\n"
                response_text += f"当前：{current_page}/{total_pages}页, 输入 “下一页” “上一页” “最后一页”"  # 简化

                self.search_results[chat_id] = {
                    "keyword": keyword,
                    "video_list": video_list,  # 保存所有视频
                    "total_pages": total_pages,
                    "current_page": current_page,
                }  # 保存搜索结果
                await bot.send_text_message(chat_id, response_text)
                logger.info(f"成功发送视频搜索结果 (文字) 到 {chat_id}, 第{current_page}页")
                return False

            else:
                await bot.send_text_message(chat_id, "未找到相关视频。")
                logger.warning(f"未找到关键词为 {keyword} 的视频")
                return False

        except Exception as e:
            logger.exception(f"处理视频搜索过程中发生异常: {e}")
            await bot.send_text_message(chat_id, f"处理视频搜索过程中发生异常: {e}")
            return False

    async def _handle_episode_navigation(self, bot: WechatAPIClient, chat_id: str, content: str) -> bool:
        """处理剧集翻页命令."""
        if chat_id not in self.current_video_index:
            await bot.send_text_message(chat_id, "请先选择视频。")
            return False

        video_index = self.current_video_index[chat_id]
        if (
            chat_id not in self.episode_results
            or video_index not in self.episode_results[chat_id]
        ):
            await bot.send_text_message(chat_id, "请先选择视频并查看剧集列表。")
            return False

        episode_data = self.episode_results[chat_id][video_index]
        episode_list = episode_data["episodes"]
        start_index = episode_data["start_index"]
        total_episodes = len(episode_list)
        total_pages = (total_episodes + self.EPISODES_PER_BATCH - 1) // self.EPISODES_PER_BATCH

        new_start_index = start_index

        if content == "下一页":
            new_start_index += self.EPISODES_PER_BATCH
        elif content == "上一页":
            new_start_index -= self.EPISODES_PER_BATCH
        elif content == "最后一页":
            new_start_index = max(0, total_episodes - self.EPISODES_PER_BATCH)

        if new_start_index < 0:
            new_start_index = 0
        elif new_start_index >= total_episodes:
            new_start_index = max(0, total_episodes - self.EPISODES_PER_BATCH)  # 最后一页

        self.episode_results[chat_id][video_index]["start_index"] = new_start_index

        end_index = min(new_start_index + self.EPISODES_PER_BATCH, total_episodes)
        display_list = episode_list[new_start_index:end_index]
        video = self.search_results[chat_id]["video_list"][video_index - 1]

        # 发送剧集列表供用户选择
        response_text = f"🎬———{video['title']} ———🎬\n"
        for i, episode in enumerate(display_list):
            episode_number = new_start_index + i + 1
            number_emoji = self.get_number_emoji(episode_number)
            response_text += f"{number_emoji}. {episode}\n"

        # 添加当前页码
        current_page = (new_start_index // self.EPISODES_PER_BATCH) + 1
        page_emoji = self.get_number_emoji(current_page)
        total_page_emoji = self.get_number_emoji(total_pages)
        response_text += f"       🎞️{page_emoji}/{total_page_emoji}🎞️\n"

        response_text += "_________________________\n"
        response_text += f"🎵输入 “序号 + 数字” 选择剧集🎵\n"
        navigation_tips = "🎵输入 “下一页” “上一页” “最后一页”🎵"  # 简化
        response_text += navigation_tips

        await bot.send_text_message(chat_id, response_text)
        return False

    @on_text_message
    async def handle_text_message(self, bot: WechatAPIClient, message: dict) -> bool:
        """处理文本消息，判断是否需要触发发送视频链接."""
        if not self.enable:
            logger.info("插件未启用，不处理消息")
            return True  # 插件未启用，不阻塞

        content = message["Content"].strip()
        chat_id = message["FromWxid"]

        logger.info(f"收到消息：content={content}, chat_id={chat_id}")

        # 播放命令处理
        if content.startswith(self.play_command):
            logger.info("处理播放命令")
            return await self._handle_play_command(bot, chat_id, content)

        # 剧集选择命令处理
        if content.startswith("序号 "):
            logger.info("处理剧集选择命令")
            return await self._handle_episode_selection(bot, chat_id, content)

        # 剧集翻页命令处理
        if content in ["下一页", "上一页", "最后一页"]:
            logger.info("处理剧集翻页命令")
            return await self._handle_episode_navigation(bot, chat_id, content)

        # 搜索命令处理
        for command in self.commands:
            if command in content:  # 使用 in 关键字进行模糊匹配
                logger.info(f"处理搜索命令: {command}")
                return await self._handle_search_command(bot, chat_id, content)

        #  处理直接播放第几集
        if content.startswith("第") and content.endswith("集"):
            try:
                episode_number = int(content[1:-1])
                logger.info(f"尝试直接播放第{episode_number}集")
                # 递归调用，传递正确的序号选择消息
                content = f"序号 {episode_number}"
                return await self._handle_episode_selection(bot, chat_id, content)
            except ValueError:
                await bot.send_text_message(chat_id, "请输入有效的剧集数字编号。")
                return False

        logger.info("没有匹配到任何命令，不处理消息")
        return True  # 没有匹配到任何命令，不阻塞
