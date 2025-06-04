#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息回调守护进程 - 持续监控原始框架消息并转发给DOW框架
将此脚本放在原始框架的目录下，在启动时运行
"""

import os
import sys
import json
import time
import logging
import traceback
import requests
import threading
from datetime import datetime
import glob
import re  # 添加正则表达式模块

# 配置日志
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, f"wx849_callback_daemon_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 回调配置
DOW_CALLBACK_URL = "http://127.0.0.1:8088/wx849/callback"  # DOW框架的回调URL
DOW_CALLBACK_KEY = ""  # 从DOW框架启动日志中获取，或在配置中设置

# 如果存在配置文件，从中读取配置
config_file = "wx849_callback_config.json"
if os.path.exists(config_file):
    try:
        with open(config_file, "r", encoding="utf-8-sig") as f:  # 修改这里，使用utf-8-sig处理UTF-8 BOM
            config = json.load(f)
            DOW_CALLBACK_URL = config.get("callback_url", DOW_CALLBACK_URL)
            DOW_CALLBACK_KEY = config.get("callback_key", DOW_CALLBACK_KEY)
            logger.info(f"已从配置文件加载回调设置: URL={DOW_CALLBACK_URL}")
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")

# 消息队列
message_queue = []
message_queue_lock = threading.Lock()

# 用户昵称缓存字典
user_nickname_cache = {}

# 已处理的图片消息ID缓存
processed_image_msgs = set()

class MessageMonitor:
    def __init__(self):
        self.is_running = True
        self.last_check_time = 0
        self.last_file_scan_time = time.time()  # 添加上次扫描文件的时间

        # 消息文件路径
        self.message_file_paths = [
            "logs/XYBot_*.log",  # 匹配当前日志文件
            "logs/message.log",
            "logs/message_current.log",
            "logs/wechat_message.log"
        ]

        # 记录每个文件的上次读取位置
        self.file_positions = {}
        # 扩展文件路径模式
        self.actual_file_paths = []
        self._scan_log_files()  # 提取为单独方法

        logger.info(f"监控的日志文件: {self.actual_file_paths}")

    def _scan_log_files(self):
        """扫描并更新日志文件列表"""
        for pattern in self.message_file_paths:
            matching_files = glob.glob(pattern)
            for file_path in matching_files:
                if os.path.exists(file_path) and file_path not in self.actual_file_paths:
                    self.actual_file_paths.append(file_path)
                    self.file_positions[file_path] = os.path.getsize(file_path)
                    logger.info(f"添加日志文件到监控列表: {file_path}")

    def start(self):
        """启动监控"""
        logger.info("启动消息监控...")

        # 启动消息处理线程
        processor_thread = threading.Thread(target=self.process_messages)
        processor_thread.daemon = True
        processor_thread.start()

        # 主循环 - 监控消息文件
        try:
            while self.is_running:
                self.check_message_files()
                time.sleep(0.5)  # 每0.5秒检查一次
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            self.is_running = False
        except Exception as e:
            logger.error(f"监控异常: {e}")
            logger.error(traceback.format_exc())
            self.is_running = False

    def check_message_files(self):
        """检查消息文件变化"""
        # 定期重新扫描日志文件（每10分钟）
        current_time = time.time()
        if current_time - self.last_file_scan_time > 600:  # 10分钟检查一次
            self.last_file_scan_time = current_time
            logger.info("定期重新扫描日志文件...")
            self._scan_log_files()

            # 检查是否有不再存在的文件，从列表中移除
            files_to_remove = []
            for file_path in self.actual_file_paths:
                if not os.path.exists(file_path):
                    files_to_remove.append(file_path)
                    logger.info(f"日志文件不再存在，从监控列表移除: {file_path}")

            for file_path in files_to_remove:
                self.actual_file_paths.remove(file_path)
                if file_path in self.file_positions:
                    del self.file_positions[file_path]

        # 检查当前文件列表变化
        for file_path in self.actual_file_paths:
            if not os.path.exists(file_path):
                continue

            try:
                # 获取当前文件大小
                current_size = os.path.getsize(file_path)

                # 如果是新文件或文件被重置
                if file_path not in self.file_positions or current_size < self.file_positions[file_path]:
                    self.file_positions[file_path] = 0
                    logger.info(f"文件被重置或新添加，从头开始读取: {file_path}")

                # 如果文件有新内容
                if current_size > self.file_positions[file_path]:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # 移动到上次读取的位置
                        f.seek(self.file_positions[file_path])

                        # 读取新增内容
                        new_content = f.read()

                        # 更新位置
                        self.file_positions[file_path] = current_size

                        # 处理新内容
                        self.parse_new_content(new_content)
            except Exception as e:
                logger.error(f"读取文件 {file_path} 失败: {e}")

    def parse_new_content(self, content):
        """解析日志内容，提取消息"""
        # 按行分割
        lines = content.split('\n')

        for line in lines:
            if not line.strip():
                continue

            try:
                # 检查昵称更新行
                nickname_pattern = r"更新用户昵称缓存: (wxid_\w+) -> (.+)"
                nickname_match = re.search(nickname_pattern, line)
                if nickname_match:
                    wxid = nickname_match.group(1)
                    nickname = nickname_match.group(2)
                    user_nickname_cache[wxid] = nickname
                    logger.info(f"缓存用户昵称: {wxid} -> {nickname}")
                    continue

                # 匹配更多可能的消息模式，特别是原始框架特定的格式
                if ("收到文本消息" in line or
                    "收到消息" in line or
                    "收到图片消息" in line or  # 特别关注图片消息
                    "收到语音消息" in line or
                    "收到被@消息" in line or  # 添加被@消息类型
                    "收到引用消息" in line or  # 添加引用消息类型
                    "MsgId" in line or
                    "收到链接分享消息" in line):

                    # 特别处理图片消息，确保它们被正确识别
                    if "收到图片消息" in line:
                        logger.info(f"发现图片消息行: {line[:100]}...")
                    # 特别处理链接分享消息，确保它们被正确识别
                    elif "收到链接分享消息" in line:
                        logger.info(f"发现链接分享消息行: {line[:100]}...")

                    logger.info(f"发现可能的消息行: {line[:100]}...")

                    # 尝试提取消息数据
                    message_data = self.extract_message_from_line(line)

                    if message_data:
                        # 使用锁保护队列操作
                        with message_queue_lock:
                            message_queue.append(message_data)
                            logger.info(f"添加消息到队列，当前队列长度: {len(message_queue)}")
            except Exception as e:
                logger.error(f"解析行异常: {e}, 行内容: {line[:100]}...")

    def extract_message_from_line(self, line):
        """从日志行提取消息数据"""
        try:
            # 尝试提取JSON格式的消息

            # 尝试找到包含消息信息的JSON对象
            json_pattern = re.compile(r'({[^{]*"MsgId"[^}]*}|{[^{]*"msg_id"[^}]*}|{[^{]*"msgid"[^}]*})')
            json_match = json_pattern.search(line)

            if json_match:
                json_str = json_match.group(1)
                try:
                    # 尝试解析JSON
                    msg_data = json.loads(json_str)

                    # 确保消息类型正确设置
                    if 'MsgType' not in msg_data or msg_data['MsgType'] == 0:
                        # 默认将未知类型设置为文本消息类型(1)
                        msg_data['MsgType'] = 1

                    # 如果消息中有发送者ID但没有昵称，尝试从缓存添加
                    sender_wxid = None
                    if 'SenderWxid' in msg_data and msg_data['SenderWxid']:
                        sender_wxid = msg_data['SenderWxid']
                    elif 'SenderId' in msg_data and msg_data['SenderId']:
                        sender_wxid = msg_data['SenderId']

                    # 添加昵称信息
                    if sender_wxid and sender_wxid in user_nickname_cache:
                        msg_data['SenderNickName'] = user_nickname_cache[sender_wxid]
                        logger.info(f"为消息添加发送者昵称: {sender_wxid} -> {user_nickname_cache[sender_wxid]}")

                    # 保存原始行以便调试
                    msg_data['RawLogLine'] = line

                    logger.info(f"成功提取JSON消息数据: {json.dumps(msg_data, ensure_ascii=False)[:100]}...")
                    return msg_data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}, 内容: {json_str[:100]}")

            # 如果不是JSON格式，尝试从格式化的日志中提取信息
            # 特殊处理图片消息
            if "收到图片消息" in line:
                logger.info(f"检测到图片消息: {line}")
                # 尝试匹配图片消息格式: 消息ID:1687893408 来自:wxid_lnbsshdobq7y22 发送人:wxid_lnbsshdobq7y22 XML:<?xml...
                img_pattern = re.compile(r'消息ID:(\d+).*?来自:(.*?)[\s\:].*?发送人:(.*?)[\s\:].*?XML:(.*?)(?=$|\n)')
                img_match = img_pattern.search(line)

                if img_match:
                    msg_id, from_user, sender, xml_content = img_match.groups()
                    logger.info(f"成功解析图片消息: ID={msg_id}, 发送者={sender}, XML长度={len(xml_content)}")

                    # 检查是否已经处理过这条图片消息
                    global processed_image_msgs
                    if msg_id in processed_image_msgs:
                        logger.info(f"图片消息 {msg_id} 已经处理过，跳过重复处理")
                        return None

                    # 标记为已处理
                    processed_image_msgs.add(msg_id)

                    # 如果缓存太大，清理一下
                    if len(processed_image_msgs) > 1000:
                        # 只保留最近的500条
                        processed_image_msgs = set(list(processed_image_msgs)[-500:])

                    # 创建图片消息数据
                    msg_data = {
                        "MsgId": int(msg_id),
                        "FromUserName": {"string": from_user},
                        "MsgType": 3,  # 图片消息类型
                        "Content": xml_content,
                        "FromWxid": from_user,
                        "SenderWxid": sender,
                        "RawLogLine": line,  # 保存原始行
                    }

                    # 尝试从缓存添加发送者昵称
                    if sender in user_nickname_cache:
                        msg_data["SenderNickName"] = user_nickname_cache[sender]
                        logger.info(f"为图片消息添加发送者昵称: {sender} -> {user_nickname_cache[sender]}")

                    logger.info(f"成功从日志提取图片消息数据: ID={msg_id}, 发送者={sender}, 类型=3(图片)")
                    return msg_data
                else:
                    logger.warning(f"无法解析图片消息格式: {line[:100]}...")

            # 特殊处理引用消息
            if "收到引用消息" in line:
                logger.info(f"检测到引用消息: {line}")
                # 尝试匹配引用消息格式: 消息ID:1241182122 来自:47325400669@chatroom 发送人:wxid_lnbsshdobq7y22 内容:@小小x 酱爆说了啥 引用:{'MsgType': 1, ...}
                quote_pattern = re.compile(r'消息ID:(\d+).*?来自:(.*?)[\s\:].*?发送人:(.*?)[\s\:].*?内容:(.*?)引用:(.*?)(?=$|\n)')
                quote_match = quote_pattern.search(line)

                if quote_match:
                    msg_id, from_user, sender, content, quote_content = quote_match.groups()
                    logger.info(f"成功解析引用消息: ID={msg_id}, 发送者={sender}, 内容={content[:30]}, 引用内容={quote_content[:30]}")

                    # 尝试解析引用内容为JSON
                    quoted_data = {}
                    try:
                        # 引用内容可能是JSON格式
                        quoted_data = json.loads(quote_content.replace("'", "\""))

                        # 检查是否是图片消息
                        if quoted_data.get("MsgType") == 3:
                            # 尝试从XML中提取图片信息
                            try:
                                # 检查是否有DEBUG日志包含完整的XML内容
                                xml_content = None

                                # 查找最近的XML日志
                                xml_debug_pattern = re.compile(r'解析到的 XML 类型: 57, 完整内容: (.*?)$')

                                # 从日志文件中查找最近的XML内容
                                try:
                                    # 使用全局变量log_file而不是self.log_file
                                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                        lines = f.readlines()
                                        for i in range(len(lines) - 1, max(0, len(lines) - 20), -1):
                                            xml_match = xml_debug_pattern.search(lines[i])
                                            if xml_match:
                                                xml_content = xml_match.group(1)
                                                logger.info(f"找到XML内容，长度: {len(xml_content)}")
                                                break
                                except Exception as e:
                                    logger.error(f"读取日志文件查找XML内容失败: {e}")

                                # 如果找到了XML内容，从中提取refermsg部分
                                if xml_content:
                                    refermsg_match = re.search(r'<refermsg>(.*?)</refermsg>', xml_content, re.DOTALL)
                                    if refermsg_match:
                                        refermsg_content = refermsg_match.group(1)
                                        logger.info(f"成功提取refermsg部分，长度: {len(refermsg_content)}")
                                    else:
                                        logger.warning(f"无法从XML内容中提取refermsg部分，xml_content前100字符: {xml_content[:100]}...")
                                else:
                                    # 如果没有找到XML内容，尝试从原始行中提取
                                    logger.info(f"尝试从原始行中提取refermsg部分，原始行长度: {len(line)}")
                                    refermsg_match = re.search(r'<refermsg>(.*?)</refermsg>', line, re.DOTALL)
                                    if refermsg_match:
                                        refermsg_content = refermsg_match.group(1)
                                        logger.info(f"成功从原始行提取refermsg部分，长度: {len(refermsg_content)}")
                                    else:
                                        logger.warning(f"无法从原始行中提取refermsg部分，原始行前100字符: {line[:100]}...")

                                # 提取svrid（消息ID）
                                if 'refermsg_content' in locals():
                                    svrid_match = re.search(r'<svrid>(.*?)</svrid>', refermsg_content)
                                    if svrid_match:
                                        quoted_data["svrid"] = svrid_match.group(1)
                                        quoted_data["NewMsgId"] = svrid_match.group(1)
                                        logger.info(f"成功从引用消息中提取svrid: {quoted_data['svrid']}")
                                    else:
                                        logger.warning(f"无法从引用消息中提取svrid，refermsg_content: {refermsg_content[:100]}...")
                                else:
                                    logger.warning("无法提取svrid，因为没有找到refermsg_content")

                                # 提取fromusr（群ID）
                                if 'refermsg_content' in locals():
                                    fromusr_match = re.search(r'<fromusr>(.*?)</fromusr>', refermsg_content)
                                    if fromusr_match:
                                        quoted_data["fromusr"] = fromusr_match.group(1)
                                        logger.info(f"成功从引用消息中提取fromusr: {quoted_data['fromusr']}")

                                    # 提取chatusr（发送者ID）
                                    chatusr_match = re.search(r'<chatusr>(.*?)</chatusr>', refermsg_content)
                                    if chatusr_match:
                                        quoted_data["chatusr"] = chatusr_match.group(1)
                                        logger.info(f"成功从引用消息中提取chatusr: {quoted_data['chatusr']}")

                                    # 提取displayname（发送者昵称）
                                    displayname_match = re.search(r'<displayname>(.*?)</displayname>', refermsg_content)
                                    if displayname_match:
                                        quoted_data["Nickname"] = displayname_match.group(1)
                                        logger.info(f"成功从引用消息中提取displayname: {quoted_data['Nickname']}")

                                # 从XML内容中提取refermsg/content部分
                                content_xml = None
                                if xml_content:
                                    # 将完整的XML内容添加到引用数据中
                                    quoted_data["FullXmlContent"] = xml_content
                                    logger.info(f"将完整的XML内容添加到引用数据中，长度: {len(xml_content)}")

                                    # 优先从完整XML内容中提取
                                    xml_match = re.search(r'<refermsg>.*?<content>(.*?)</content>.*?</refermsg>', xml_content, re.DOTALL)
                                    if xml_match:
                                        # 获取content内容并解码XML实体
                                        content_xml = xml_match.group(1)
                                        content_xml = content_xml.replace("&lt;", "<").replace("&gt;", ">")
                                        logger.info(f"成功从XML内容中提取content部分，长度: {len(content_xml)}")
                                    else:
                                        logger.warning(f"无法从XML内容中提取content部分，xml_content前100字符: {xml_content[:100]}...")

                                # 如果从XML内容中没有提取到，尝试从原始行中提取
                                if not content_xml:
                                    xml_match = re.search(r'<refermsg>.*?<content>(.*?)</content>.*?</refermsg>', line, re.DOTALL)
                                    if xml_match:
                                        # 获取content内容并解码XML实体
                                        content_xml = xml_match.group(1)
                                        content_xml = content_xml.replace("&lt;", "<").replace("&gt;", ">")
                                        logger.info(f"成功从原始行中提取content部分，长度: {len(content_xml)}")
                                    else:
                                        logger.warning(f"无法从原始行中提取content部分，原始行前100字符: {line[:100]}...")

                                # 提取图片信息
                                if content_xml:
                                    img_match = re.search(r'<img\s+(.*?)>', content_xml, re.DOTALL)
                                    if img_match:
                                        img_attrs = img_match.group(1)

                                        # 提取各种属性
                                        aeskey_match = re.search(r'aeskey="([^"]*)"', img_attrs)
                                        cdnthumburl_match = re.search(r'cdnthumburl="([^"]*)"', img_attrs)
                                        cdnmidimgurl_match = re.search(r'cdnmidimgurl="([^"]*)"', img_attrs)
                                        length_match = re.search(r'length="([^"]*)"', img_attrs)
                                        md5_match = re.search(r'md5="([^"]*)"', img_attrs)

                                        # 添加到引用数据中
                                        if aeskey_match:
                                            quoted_data["aeskey"] = aeskey_match.group(1)
                                        if cdnthumburl_match:
                                            quoted_data["cdnthumburl"] = cdnthumburl_match.group(1)
                                        if cdnmidimgurl_match:
                                            quoted_data["cdnmidimgurl"] = cdnmidimgurl_match.group(1)
                                        if length_match:
                                            quoted_data["length"] = length_match.group(1)
                                        if md5_match:
                                            quoted_data["md5"] = md5_match.group(1)

                                        # 添加图片内容到引用数据
                                        quoted_data["Content"] = content_xml

                                        logger.info(f"成功从引用消息中提取图片信息: aeskey={quoted_data.get('aeskey', '')}, cdnthumburl={quoted_data.get('cdnthumburl', '')[:30]}..., length={quoted_data.get('length', '')}")
                                    else:
                                        logger.warning(f"无法从content_xml中提取img元素，content_xml前100字符: {content_xml[:100]}...")
                                else:
                                    logger.warning("无法提取图片信息，因为没有找到content_xml")
                            except Exception as e:
                                logger.error(f"提取引用图片信息失败: {e}")
                    except:
                        # 如果解析失败，保留原始字符串
                        quoted_data = {"Content": quote_content}

                    # 检查是否@了机器人
                    is_at_bot = False
                    # 从配置文件中读取机器人名称列表
                    robot_names = []
                    try:
                        # 尝试从配置文件中读取机器人名称
                        config_file = "dow/config.json"
                        if os.path.exists(config_file):
                            with open(config_file, "r", encoding="utf-8") as f:
                                dow_config = json.load(f)
                                robot_names = dow_config.get("robot_names", [])
                                logger.info(f"从配置文件中读取到机器人名称列表: {robot_names}")
                    except Exception as e:
                        logger.error(f"读取配置文件中的机器人名称失败: {e}")

                    # 如果配置文件中没有设置或读取失败，使用默认值
                    if not robot_names:
                        robot_names = ["小小x", "小x", "机器人"]
                        logger.info(f"使用默认机器人名称列表: {robot_names}")

                    for bot_name in robot_names:
                        if f"@{bot_name}" in content:
                            is_at_bot = True
                            logger.info(f"检测到@机器人: @{bot_name}")
                            break

                    # 创建消息数据
                    msg_data = {
                        "MsgId": int(msg_id),
                        "FromUserName": {"string": from_user},
                        "MsgType": 49,  # XML消息类型
                        "Content": content,
                        "FromWxid": from_user,
                        "SenderWxid": sender,
                        "RawLogLine": line,  # 保存原始行
                        "QuotedMessage": quoted_data,  # 添加引用消息数据
                        "IsAtMessage": is_at_bot  # 设置是否@了机器人的标志
                    }

                    # 尝试从缓存添加发送者昵称
                    if sender in user_nickname_cache:
                        msg_data["SenderNickName"] = user_nickname_cache[sender]
                        logger.info(f"为引用消息添加发送者昵称: {sender} -> {user_nickname_cache[sender]}")

                    # 如果引用内容中有昵称，也添加到消息中
                    if "Nickname" in quoted_data:
                        msg_data["QuotedNickname"] = quoted_data["Nickname"]
                        logger.info(f"添加被引用消息的发送者昵称: {quoted_data['Nickname']}")

                    logger.info(f"成功从日志提取引用消息数据: ID={msg_id}, 发送者={sender}, 类型=49(XML)")
                    return msg_data
                else:
                    logger.warning(f"无法解析引用消息格式: {line[:100]}...")

            # 特殊处理被@消息
            if "收到被@消息" in line:
                logger.info(f"检测到被@消息: {line}")
                at_pattern = re.compile(r'消息ID:(\d+).*?来自:(.*?)[\s\:].*?发送人:(.*?)[\s\:].*?@:(\[.*?\]).*?内容:(.*?)(?=$|\n)')
                at_match = at_pattern.search(line)

                if at_match:
                    msg_id, from_user, sender, at_list_str, content = at_match.groups()
                    logger.info(f"成功解析被@消息: ID={msg_id}, 发送者={sender}, @列表={at_list_str}")

                    # 解析@列表
                    at_list = []
                    if at_list_str.startswith("[") and at_list_str.endswith("]"):
                        # 去除[]
                        at_list_str = at_list_str[1:-1]
                        if at_list_str:
                            at_items = at_list_str.split(",")
                            for item in at_items:
                                item = item.strip().strip("'\"")
                                if item:
                                    at_list.append(item)

                    msg_data = {
                        "MsgId": int(msg_id),
                        "FromUserName": {"string": from_user},
                        "MsgType": 1,  # 文本消息
                        "Content": content,
                        "FromWxid": from_user,
                        "SenderWxid": sender,
                        "RawLogLine": line,  # 保存原始行
                        "IsAtMessage": True,  # 标记为被@消息
                        "AtList": at_list  # 添加@列表
                    }

                    # 如果有@列表，添加MsgSource字段
                    if at_list:
                        at_users_str = ",".join(at_list)
                        msg_source = f'<msgsource><atuserlist>{at_users_str}</atuserlist></msgsource>'
                        msg_data["MsgSource"] = msg_source

                    return msg_data

                # 特殊处理被@消息
            if "收到链接分享消息" in line:
                logger.info(f"检测到收到链接分享消息: {line}")
                url_pattern = re.compile(r'消息ID:(\d+).*?来自:(.*?)[\s\:].*?发送人:(.*?)[\s\:].*?XML:(.*?)(?=$|\n)')
                url_match = url_pattern.search(line)

                if url_match:
                    msg_id, from_user, sender, xml_content = url_match.groups()
                    logger.info(f"成功解析链接分享消息: ID={msg_id}, 发送者={sender}, XML长度={len(xml_content)}")

                    # 创建分享消息数据
                    msg_data = {
                        "MsgId": int(msg_id),
                        "FromUserName": {"string": from_user},
                        "MsgType": 6,  # SHARING 分享信息
                        "Content": xml_content,
                        "FromWxid": from_user,
                        "SenderWxid": sender,
                        "RawLogLine": line,  # 保存原始行
                    }

                    # 尝试从缓存添加发送者昵称
                    if sender in user_nickname_cache:
                        msg_data["SenderNickName"] = user_nickname_cache[sender]
                        logger.info(f"为分享消息添加发送者昵称: {sender} -> {user_nickname_cache[sender]}")

                    logger.info(f"成功从日志提取分享消息数据: ID={msg_id}, 发送者={sender}, 类型=6(分享信息)")
                    return msg_data

            # 处理普通消息
            msg_pattern = re.compile(r'消息ID:(\d+).*?来自:(.*?)[\s\:].*?发送人:(.*?)[\s\:].*?内容:(.*?)(?=$|\n)')
            msg_match = msg_pattern.search(line)

            if msg_match:
                msg_id, from_user, sender, content = msg_match.groups()
                msg_data = {
                    "MsgId": int(msg_id),
                    "FromUserName": {"string": from_user},
                    "MsgType": 1,  # 默认设置为文本消息类型
                    "Content": content,
                    "FromWxid": from_user,
                    "SenderWxid": sender,
                    "RawLogLine": line  # 保存原始行
                }

                # 尝试从缓存添加发送者昵称
                if sender in user_nickname_cache:
                    msg_data["SenderNickName"] = user_nickname_cache[sender]
                    logger.info(f"为消息添加发送者昵称: {sender} -> {user_nickname_cache[sender]}")

                # 检查内容中是否包含昵称信息 (格式如: "xxx : 消息内容")
                if "PushContent" not in msg_data and content:
                    push_content_match = re.match(r"(.+?)\s*:\s*(.+)", content)
                    if push_content_match:
                        nickname, real_content = push_content_match.groups()
                        msg_data["PushContent"] = f"{nickname} : {real_content}"
                        # 可能的情况下更新昵称缓存
                        if sender and sender not in user_nickname_cache:
                            user_nickname_cache[sender] = nickname
                            logger.info(f"从消息内容更新昵称缓存: {sender} -> {nickname}")

                logger.info(f"成功从日志提取消息数据: ID={msg_id}, 发送者={sender}, 类型=1(文本)")
                return msg_data

            # 尝试匹配新格式的日志行 (包含更多消息内容)
            new_pattern = re.compile(r'收到文本消息: chat_id=(.*?), content=(.*?),')
            new_match = new_pattern.search(line)
            if new_match:
                chat_id, content = new_match.groups()
                # 只有在队列为空时才添加，避免重复
                if not message_queue:
                    msg_data = {
                        "MsgId": int(time.time() * 1000),  # 生成一个临时ID
                        "FromUserName": {"string": chat_id},
                        "MsgType": 1,
                        "Content": content,
                        "FromWxid": chat_id,
                        "RawLogLine": line  # 保存原始行
                    }

                    # 从内容中提取发送者信息 (格式如: "xxx : 消息内容")
                    if content:
                        push_content_match = re.match(r"(.+?)\s*:\s*(.+)", content)
                        if push_content_match:
                            nickname, real_content = push_content_match.groups()
                            msg_data["Content"] = real_content
                            msg_data["PushContent"] = f"{nickname} : {real_content}"
                            # 这里无法确定wxid，所以不更新昵称缓存

                    logger.info(f"成功从新格式日志提取消息: chat_id={chat_id}, content={content[:30]}...")
                    return msg_data

            return None
        except Exception as e:
            logger.error(f"提取消息异常: {e}")
            logger.error(traceback.format_exc())
            return None

    def process_messages(self):
        """处理消息队列"""
        logger.info("启动消息处理线程")

        while self.is_running:
            try:
                # 检查队列是否有消息
                if message_queue:
                    # 使用锁保护队列操作
                    with message_queue_lock:
                        # 获取最早的消息
                        if message_queue:
                            message = message_queue.pop(0)
                            logger.debug(f"从队列取出消息，剩余: {len(message_queue)}")
                        else:
                            message = None

                    # 处理消息
                    if message:
                        self.send_to_dow(message)

                # 短暂休眠避免CPU过载
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"处理消息异常: {e}")
                logger.error(traceback.format_exc())

    def send_to_dow(self, message_data):
        """将消息发送给DOW框架"""
        try:
            headers = {
                "Content-Type": "application/json"
            }

            # 只有当有密钥时才添加Authorization头
            if DOW_CALLBACK_KEY:
                headers["Authorization"] = f"Bearer {DOW_CALLBACK_KEY}"

            # 发送完整消息数据，不过滤任何字段
            logger.debug(f"发送完整消息数据: {json.dumps(message_data, ensure_ascii=False)[:200]}...")

            # 发送POST请求
            response = requests.post(DOW_CALLBACK_URL,
                                   json=message_data,
                                   headers=headers,
                                   timeout=5)

            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    logger.info("消息转发成功")
                else:
                    logger.error(f"DOW框架处理失败: {result.get('message', '未知错误')}")
            else:
                logger.error(f"发送失败，状态码: {response.status_code}, 内容: {response.text}")
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("======== 启动微信消息回调守护进程 ========")
    logger.info(f"回调URL: {DOW_CALLBACK_URL}")

    # 创建并启动监控器
    monitor = MessageMonitor()
    monitor.start()