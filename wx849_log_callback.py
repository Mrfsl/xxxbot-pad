#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import os
import sys
import time
import json
import re
import requests
import threading
import logging
from datetime import datetime
import traceback

from urllib.parse import urlencode
from urllib.request import urlretrieve
import os
import tempfile
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 修改为DEBUG级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wx849_log_callback.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 回调配置
CONFIG_FILE = "wx849_callback_config.json"

def load_config():
    """加载回调配置"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {
            "callback_url": "http://127.0.0.1:8088/wx849/callback",
            "callback_key": ""
        }

def send_callback(message_data):
    """发送回调请求"""
    config = load_config()
    callback_url = config.get("callback_url", "http://127.0.0.1:8088/wx849/callback")
    callback_key = config.get("callback_key", "")

    headers = {
        "Content-Type": "application/json"
    }

    if callback_key:
        headers["Authorization"] = f"Bearer {callback_key}"

    try:
        response = requests.post(
            callback_url,
            headers=headers,
            json=message_data,
            timeout=5
        )

        if response.status_code == 200:
            logger.info(f"回调成功: {response.text}")
            return True
        else:
            logger.error(f"回调失败: 状态码 {response.status_code}, 响应: {response.text}")
            return False
    except Exception as e:
        logger.error(f"发送回调请求失败: {e}")
        logger.error(traceback.format_exc())
        return False

def parse_log_line(line):
    """解析日志行"""
    # 匹配日志行
    log_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (INFO|DEBUG|ERROR|WARNING) \| (.+)"
    match = re.match(log_pattern, line)

    if not match:
        return None

    timestamp, level, content = match.groups()

    # 调试输出
    logger.debug(f"解析日志行: {line}")
    logger.debug(f"提取内容: {content}")

    # 解析消息类型

    # 匹配各种消息类型
    patterns = {
        # 文本消息
        "text": r"收到文本消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 被@消息
        "at": r"收到被@消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 图片消息
        "image": r"收到图片消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 语音消息
        "voice": r"收到语音消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 视频消息
        "video": r"收到视频消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 文件消息
        "file": r"收到文件消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 链接消息
        "link": r"收到链接消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)",
        # 系统消息
        "system": r"收到系统消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)"
    }

    # 特殊处理被@消息
    if "收到被@消息" in content:
        logger.debug(f"检测到被@消息: {content}")
        # 尝试使用正则表达式提取消息ID、来源、发送人和内容
        at_pattern = r"收到被@消息: 消息ID:(\d+) 来自:([^ ]+) 发送人:([^ ]+) @:(\[.*?\]) 内容:(.*)"
        at_match = re.match(at_pattern, content)
        if at_match:
            logger.debug(f"成功匹配被@消息: {at_match.groups()}")
            msg_id, from_wxid, sender_wxid, at_list_str, msg_content = at_match.groups()

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

            # 构建消息数据
            message_data = {
                "MsgId": int(msg_id),
                "FromUserName": {"string": from_wxid},
                "ToUserName": {"string": ""},
                "MsgType": 1,  # 文本消息
                "Content": msg_content,
                "FromWxid": from_wxid,
                "SenderWxid": sender_wxid,
                "RawLogLine": line,
                "IsAtMessage": True  # 标记为被@消息
            }

            # 添加@列表
            if at_list:
                message_data["AtList"] = at_list
                # 构建MsgSource XML
                at_users_str = ",".join(at_list)
                msg_source = f'<msgsource><atuserlist>{at_users_str}</atuserlist></msgsource>'
                message_data["MsgSource"] = msg_source

            logger.debug(f"构建被@消息数据: {message_data}")
            return message_data

    # 尝试匹配其他类型的消息
    for msg_type, pattern in patterns.items():
        match = re.match(pattern, content)
        if match:
            msg_id, from_wxid, sender_wxid, at_list_str, msg_content = match.groups()

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

            # 根据消息类型设置MsgType
            message_type = 1  # 默认为文本消息
            if msg_type == "image":
                message_type = 3
            elif msg_type == "voice":
                message_type = 34
            elif msg_type == "video":
                message_type = 43
            elif msg_type == "file":
                message_type = 49
            elif msg_type == "link":
                message_type = 49
            elif msg_type == "system":
                message_type = 10000

            # 特殊处理被@消息
            is_at_message = (msg_type == "at")

            # 构建消息数据
            message_data = {
                "MsgId": int(msg_id),
                "FromUserName": {"string": from_wxid},
                "ToUserName": {"string": ""},
                "MsgType": message_type,
                "Content": msg_content,
                "FromWxid": from_wxid,
                "SenderWxid": sender_wxid,
                "RawLogLine": line,
                "IsAtMessage": is_at_message  # 标记是否为被@消息
            }

            # 添加@列表
            if at_list:
                message_data["AtList"] = at_list

                # 如果是被@消息，添加MsgSource字段
                if is_at_message:
                    # 构建MsgSource XML
                    at_users_str = ",".join(at_list)
                    msg_source = f'<msgsource><atuserlist>{at_users_str}</atuserlist></msgsource>'
                    message_data["MsgSource"] = msg_source

            return message_data

    # 如果没有匹配到任何消息类型，返回None
    return None



def monitor_log_file(log_file_path):
    """监控日志文件"""
    # 确保日志文件存在
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w", encoding="utf-8") as f:
            pass

    # 获取文件大小
    file_size = os.path.getsize(log_file_path)
    logger.info(f"日志文件大小: {file_size} 字节")

    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        # 从头开始读取文件
        f.seek(0)
        logger.info(f"从头开始读取文件")

        line_count = 0
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    line_count += 1
                    # 检查是否包含关键字
                    if "收到被@消息" in line:
                        logger.info(f"发现被@消息行: {line}")

                    # 解析日志行
                    message_data = parse_log_line(line)
                    if message_data:
                        logger.info(f"成功解析消息: {message_data.get('MsgId')}, 类型: {message_data.get('MsgType')}, 是否被@: {message_data.get('IsAtMessage', False)}")
                        # 发送回调
                        result = send_callback(message_data)
                        logger.info(f"回调结果: {result}")
                    elif "收到被@消息" in line:
                        logger.warning(f"无法解析被@消息行: {line}")
            else:
                # 每100行输出一次统计信息
                if line_count > 0 and line_count % 100 == 0:
                    logger.info(f"已处理 {line_count} 行日志")
                # 没有新行，等待一段时间
                time.sleep(0.1)

def main():
    """主函数"""
    # 获取日志文件路径
    log_file_path = os.path.join("logs", "XYBot_2025-05-04_17-09-24_707021.log")

    # 检查日志文件是否存在
    if not os.path.exists(log_file_path):
        logger.error(f"日志文件不存在: {log_file_path}")

        # 尝试查找最新的日志文件
        log_dir = "logs"
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.startswith("XYBot_") and f.endswith(".log")]
            if log_files:
                # 按修改时间排序，获取最新的日志文件
                log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
                log_file_path = os.path.join(log_dir, log_files[0])
                logger.info(f"找到最新的日志文件: {log_file_path}")

        # 如果仍然找不到日志文件，尝试在整个目录中查找
        if not os.path.exists(log_file_path):
            for root, _, files in os.walk("."):
                for file in files:
                    if file.startswith("XYBot_") and file.endswith(".log"):
                        log_file_path = os.path.join(root, file)
                        logger.info(f"找到日志文件: {log_file_path}")
                        break
                if os.path.exists(log_file_path):
                    break

    if not os.path.exists(log_file_path):
        logger.error("无法找到日志文件，请手动指定日志文件路径")
        return

    logger.info(f"开始监控日志文件: {log_file_path}")

    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor_log_file, args=(log_file_path,))
    monitor_thread.daemon = True
    monitor_thread.start()

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("程序已停止")









if __name__ == "__main__":
    main()
