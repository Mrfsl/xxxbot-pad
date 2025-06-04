# 🔌 XXXBot 插件开发指南

## 📝 目录

- [插件系统介绍](#插件系统介绍)
- [插件基本结构](#插件基本结构)
- [创建第一个插件](#创建第一个插件)
- [消息处理装饰器](#消息处理装饰器)
  - [阻塞机制详解](#阻塞机制详解-)
- [定时任务](#定时任务)
- [插件配置文件](#插件配置文件)
- [插件生命周期](#插件生命周期)
- [API 接口](#api-接口)
- [最佳实践](#最佳实践)
- [示例插件](#示例插件)
- [常见问题](#常见问题)

## 🌟 插件系统介绍

XXXBot 的插件系统允许开发者扩展机器人的功能，而无需修改核心代码。每个插件都是一个独立的 Python 模块，可以处理各种类型的消息，执行定时任务，或者提供新的功能。

插件系统的主要特点：

- 🔄 **热插拔**：可以在不重启机器人的情况下启用或禁用插件
- 🔢 **优先级控制**：可以设置插件处理消息的优先级
- ⏱️ **定时任务**：支持基于时间的定期任务执行
- 🔒 **隔离性**：每个插件都在自己的命名空间中运行，不会干扰其他插件

## 📂 插件基本结构

一个标准的插件目录结构如下：

```
plugins/
└── YourPlugin/
    ├── __init__.py      # 插件入口点
    ├── main.py          # 插件主要代码
    ├── config.toml      # 插件配置文件
    └── README.md        # 插件说明文档
```

### 必需文件

- \***\*init**.py\*\*：标识这是一个 Python 模块，可以为空或导入主类
- **main.py**：包含插件的主要逻辑和类定义
- **config.toml**：插件的配置文件

## 🚀 创建第一个插件

### 步骤 1：创建插件目录

```bash
mkdir -p plugins/MyFirstPlugin
```

### 步骤 2：创建 **init**.py

```python
# plugins/MyFirstPlugin/__init__.py
from .main import MyFirstPlugin
```

### 步骤 3：创建 main.py

```python
# plugins/MyFirstPlugin/main.py
from loguru import logger
import tomllib
import os

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class MyFirstPlugin(PluginBase):
    description = "我的第一个插件"
    author = "Your Name"
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
            self.enable = basic_config.get("enable", False)  # 读取插件开关
            self.trigger_word = basic_config.get("trigger_word", "你好")  # 读取触发词

        except Exception as e:
            logger.error(f"加载MyFirstPlugin配置文件失败: {str(e)}")
            self.enable = False  # 如果加载失败，禁用插件

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息"""
        if not self.enable:
            return True  # 插件未启用，允许后续插件处理

        content = message["Content"]

        # 检查是否包含触发词
        if self.trigger_word in content:
            # 发送回复
            await bot.send_text_message(
                message["FromWxid"],
                f"你好！我是你的第一个插件。你说了：{content}"
            )
            return False  # 阻止后续插件处理

        return True  # 允许后续插件处理
```

### 步骤 4：创建 config.toml

```toml
[basic]
# 是否启用插件
enable = true
# 触发词
trigger_word = "你好"
```

## 🎯 消息处理装饰器

XXXBot 提供了多种装饰器来处理不同类型的消息：

| 装饰器              | 描述           | 参数                         |
| ------------------- | -------------- | ---------------------------- |
| `@on_text_message`  | 处理文本消息   | `priority`: 优先级（默认 0） |
| `@on_at_message`    | 处理 @ 消息    | `priority`: 优先级（默认 0） |
| `@on_voice_message` | 处理语音消息   | `priority`: 优先级（默认 0） |
| `@on_image_message` | 处理图片消息   | `priority`: 优先级（默认 0） |
| `@on_video_message` | 处理视频消息   | `priority`: 优先级（默认 0） |
| `@on_file_message`  | 处理文件消息   | `priority`: 优先级（默认 0） |
| `@on_xml_message`   | 处理 XML 消息  | `priority`: 优先级（默认 0） |
| `@on_quote_message` | 处理引用消息   | `priority`: 优先级（默认 0） |
| `@on_pat_message`   | 处理拍一拍消息 | `priority`: 优先级（默认 0） |
| `@on_emoji_message` | 处理表情消息   | `priority`: 优先级（默认 0） |

### 优先级说明

- 优先级越高（数值越大），越先处理消息
- 优先级范围是 0-99，默认为 50
- 如果一个插件处理了消息并返回 `False`，后续插件将不会处理该消息
- 如果返回 `True`，则允许后续插件继续处理该消息

#### 全局优先级设置

除了在装饰器中设置优先级外，还可以在插件的 `config.toml` 文件中设置全局优先级，这将覆盖所有装饰器中的优先级设置：

```toml
[basic]
# 是否启用插件
enable = true
# 全局优先级设置 (0-99)，值越高优先级越高
priority = 80
```

或者：

```toml
[PluginName]
enable = true
priority = 80
```

**重要说明**：

- 如果在配置文件中设置了全局优先级，则该优先级将覆盖所有装饰器中设置的优先级
- 如果没有设置全局优先级，则使用各个处理函数装饰器中设置的优先级
- 这样可以保持向后兼容性，不需要修改现有的插件代码

### 阻塞机制详解 🔐

XXXBot 的插件系统采用了阻塞机制，允许插件决定是否允许后续插件处理同一消息。这个机制通过消息处理函数的返回值来控制：

- **返回 `False`**：表示消息已被完全处理，系统将阻止后续插件处理该消息
- **返回 `True`**：表示允许后续插件继续处理该消息
- **返回 `None` 或不返回**：默认等同于返回 `None`，允许后续插件处理

#### 阻塞机制的应用场景

1. **完全处理消息**：当插件完全处理了消息，不需要其他插件再处理时

   ```python
   @on_text_message(priority=50)
   async def handle_command(self, bot: WechatAPIClient, message: dict):
       if message["Content"].startswith("/command"):
           # 处理命令
           await bot.send_text_message(message["FromWxid"], "命令已执行")
           return False  # 阻止后续插件处理
       return True  # 不是命令，允许后续插件处理
   ```

2. **条件处理**：根据消息内容决定是否阻止

   ```python
   @on_text_message(priority=80)
   async def handle_keyword(self, bot: WechatAPIClient, message: dict):
       content = message["Content"]
       if "敏感词" in content:
           await bot.send_text_message(message["FromWxid"], "该消息包含敏感内容")
           return False  # 阻止后续插件处理敏感内容
       return True  # 允许后续插件处理
   ```

3. **消息过滤**：高优先级插件可以过滤消息

   ```python
   @on_text_message(priority=99)
   async def filter_messages(self, bot: WechatAPIClient, message: dict):
       if self._is_spam(message["Content"]):
           logger.info(f"拦截垃圾消息: {message['Content']}")
           return False  # 阻止后续插件处理垃圾消息
       return True  # 非垃圾消息，允许后续插件处理
   ```

#### 阻塞机制最佳实践

1. **明确的返回值**：始终明确返回 `True` 或 `False`，避免默认返回 `None`
2. **谨慎使用阻塞**：只在真正需要阻止后续处理时返回 `False`
3. **注意优先级**：高优先级插件的阻塞决定会影响所有低优先级插件

### 消息处理示例

```python
@on_text_message(priority=99)  # 高优先级
async def handle_high_priority(self, bot: WechatAPIClient, message: dict):
    # 处理逻辑
    return False  # 阻止后续插件处理

@on_text_message(priority=50)  # 中等优先级
async def handle_medium_priority(self, bot: WechatAPIClient, message: dict):
    # 处理逻辑
    return True  # 允许后续插件处理

@on_text_message()  # 默认优先级（0）
async def handle_default_priority(self, bot: WechatAPIClient, message: dict):
    # 处理逻辑
    return True
```

## ⏰ 定时任务

XXXBot 支持三种类型的定时任务：

1. **间隔执行**：按固定时间间隔执行
2. **定时执行**：按 cron 表达式执行
3. **一次性执行**：在指定日期时间执行一次

### 示例

```python
# 每5秒执行一次
@schedule('interval', seconds=5)
async def periodic_task(self, bot: WechatAPIClient):
    if not self.enable:
        return
    logger.info("我每5秒执行一次")

# 每天早上8点30分30秒执行
@schedule('cron', hour=8, minute=30, second=30)
async def daily_task(self, bot: WechatAPIClient):
    if not self.enable:
        return
    logger.info("我每天早上8点30分30秒执行")

# 在指定日期时间执行一次
@schedule('date', run_date='2025-01-29 00:00:00')
async def new_year_task(self, bot: WechatAPIClient):
    if not self.enable:
        return
    logger.info("我在2025年1月29日执行")
```

## ⚙️ 插件配置文件

插件配置文件使用 TOML 格式，提供了一种简单、易读的方式来配置插件。

### 基本结构

```toml
[basic]
# 基本配置
enable = true  # 是否启用插件

[feature_1]
# 功能1的配置
option_1 = "value"
option_2 = 123

[feature_2]
# 功能2的配置
enabled = false
items = ["item1", "item2", "item3"]
```

### 读取配置

```python
def __init__(self):
    super().__init__()

    config_path = os.path.join(os.path.dirname(__file__), "config.toml")

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # 读取基本配置
        basic_config = config.get("basic", {})
        self.enable = basic_config.get("enable", False)

        # 读取功能1配置
        feature_1 = config.get("feature_1", {})
        self.option_1 = feature_1.get("option_1", "default")
        self.option_2 = feature_1.get("option_2", 0)

        # 读取功能2配置
        feature_2 = config.get("feature_2", {})
        self.feature_2_enabled = feature_2.get("enabled", False)
        self.items = feature_2.get("items", [])

    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        self.enable = False  # 如果加载失败，禁用插件
```

## 🔄 插件生命周期

插件的生命周期包括以下阶段：

1. **加载**：系统发现并加载插件
2. **初始化**：调用插件的 `__init__` 方法
3. **异步初始化**：调用插件的 `async_init` 方法（如果存在）
4. **运行**：插件处理消息和执行定时任务
5. **启用/禁用**：通过 `on_enable` 和 `on_disable` 方法控制插件状态
6. **卸载**：系统卸载插件

### 异步初始化

如果插件需要在启动时执行异步操作（如网络请求），可以实现 `async_init` 方法：

```python
async def async_init(self):
    # 执行异步初始化操作
    result = await some_async_function()
    self.data = result
    return
```

### 启用/禁用回调

```python
async def on_enable(self, bot=None):
    """插件启用时调用"""
    logger.info(f"{self.__class__.__name__} 插件已启用")

async def on_disable(self):
    """插件禁用时调用"""
    logger.info(f"{self.__class__.__name__} 插件已禁用")
```

## 🔌 API 接口

### WechatAPIClient (PAD 协议)

`WechatAPIClient` 提供了与微信交互的各种方法，本项目使用 PAD 协议与微信进行通信：

#### 发送消息

```python
# 发送文本消息
await bot.send_text_message(wxid, "Hello, world!")

# 发送图片消息
await bot.send_image_message(wxid, "path/to/image.jpg")

# 发送语音消息
await bot.send_voice_message(wxid, "path/to/voice.mp3", format="mp3")

# 发送视频消息
await bot.send_video_message(wxid, "path/to/video.mp4")

# 发送文件消息
await bot.send_file_message(wxid, "path/to/file.pdf")

# 发送@消息
await bot.send_at_message(group_wxid, "大家好", ["wxid1", "wxid2"])
```

#### 获取联系人信息

```python
# 获取联系人列表
contacts = await bot.get_contacts()

# 获取群成员列表
members = await bot.get_chatroom_members(group_wxid)

# 获取群成员详细信息
member_info = await bot.get_chatroom_member_info(group_wxid, member_wxid)

# 获取用户信息
user_info = await bot.get_user_info(wxid)
```

#### 朋友圈相关操作

```python
# 获取朋友圈列表
pyq_list = await bot.get_friend_circle_list()

# 获取指定用户的朋友圈
user_pyq = await bot.get_user_friend_circle(wxid)

# 点赞朋友圈
await bot.like_friend_circle(pyq_id)

# 评论朋友圈
await bot.comment_friend_circle(pyq_id, "评论内容")
```

#### 其他操作

```python
# 接受好友请求
await bot.accept_friend_request(v1, v2, scene)

# 创建群聊
await bot.create_chatroom(wxids)

# 邀请用户加入群聊
await bot.invite_chatroom_members(chatroom_wxid, wxids)

# 同步消息
await bot.sync_message(scene=0)  # scene=0 同步消息，scene=1 同步摘要，scene=7 初始化
```

## 🔗 PAD 协议 API 路径参考

下面是 PAD 协议的主要 API 路径参考，开发者可以了解底层实现。所有路径在实际调用时需要添加 `/VXAPI` 前缀，但在使用 `WechatAPIClient` 时会自动处理。

### 消息相关 API

| API 路径         | 功能描述     | 主要参数                                             |
| ---------------- | ------------ | ---------------------------------------------------- |
| `/Msg/Sync`      | 同步消息     | `Scene`: 0(同步消息), 1(同步摘要), 7(初始化), `Wxid` |
| `/Msg/SendTxt`   | 发送文本消息 | `ToWxid`, `Content`, `At`(群@用户)                   |
| `/Msg/UploadImg` | 发送图片     | `ToWxid`, `Base64`                                   |
| `/Msg/SendVoice` | 发送语音     | `ToWxid`, `Base64`, `VoiceTime`(时长), `Type`        |
| `/Msg/SendVideo` | 发送视频     | `ToWxid`, `Base64`, `ImageBase64`(封面)              |
| `/Msg/SendEmoji` | 发送表情     | `ToWxid`, `Md5`, `TotalLen`                          |
| `/Msg/ShareLink` | 发送链接     | `ToWxid`, `Title`, `Desc`, `Url`, `ThumbUrl`         |
| `/Msg/ShareCard` | 分享名片     | `ToWxid`, `CardWxId`, `CardNickName`                 |
| `/Msg/Revoke`    | 撤回消息     | `ToUserName`, `ClientMsgId`, `NewMsgId`              |

### 朋友圈相关 API

| API 路径                    | 功能描述            | 主要参数                                           |
| --------------------------- | ------------------- | -------------------------------------------------- |
| `/FriendCircle/GetList`     | 获取朋友圈列表      | `Wxid`, `Maxid`, `Fristpagemd5`                    |
| `/FriendCircle/GetDetail`   | 获取指定用户朋友圈  | `Wxid`, `Towxid`, `Maxid`, `Fristpagemd5`          |
| `/FriendCircle/GetIdDetail` | 获取指定朋友圈详情  | `Wxid`, `Id`                                       |
| `/FriendCircle/Comment`     | 点赞/评论朋友圈     | `Wxid`, `Id`, `Type`(1 点赞,2 评论), `Content`     |
| `/FriendCircle/Operation`   | 朋友圈操作          | `Wxid`, `Id`, `Type`(1 删除,2 设为隐私,3 设为公开) |
| `/FriendCircle/Upload`      | 上传朋友圈图片/视频 | `Wxid`, `Base64`                                   |
| `/FriendCircle/Messages`    | 发布朋友圈          | `Wxid`, `Content`, `ISVideo`                       |

### 群组相关 API

| API 路径                         | 功能描述       | 主要参数                                 |
| -------------------------------- | -------------- | ---------------------------------------- |
| `/Group/CreateChatRoom`          | 创建群聊       | `Wxid`, `ToWxids`(多个用户 ID)           |
| `/Group/AddChatRoomMember`       | 增加群成员     | `Wxid`, `ChatRoomName`(群 ID), `ToWxids` |
| `/Group/DelChatRoomMember`       | 删除群成员     | `Wxid`, `ChatRoomName`, `ToWxids`        |
| `/Group/GetChatRoomMemberDetail` | 获取群成员     | `Wxid`, `QID`(群 ID)                     |
| `/Group/GetSomeMemberInfo`       | 获取群成员信息 | `Wxid`, `QID`, `ToWxid`                  |
| `/Group/SetChatRoomName`         | 设置群名称     | `Wxid`, `QID`, `Content`                 |
| `/Group/SetChatRoomAnnouncement` | 设置群公告     | `Wxid`, `QID`, `Content`                 |
| `/Group/Quit`                    | 退出群聊       | `Wxid`, `QID`                            |

### 好友相关 API

| API 路径                    | 功能描述       | 主要参数                                                   |
| --------------------------- | -------------- | ---------------------------------------------------------- |
| `/Friend/GetContractList`   | 获取通讯录好友 | `Wxid`, `CurrentWxcontactSeq`, `CurrentChatRoomContactSeq` |
| `/Friend/GetContractDetail` | 获取好友详情   | `Wxid`, `Towxids`                                          |
| `/Friend/Search`            | 搜索联系人     | `Wxid`, `ToUserName`                                       |
| `/Friend/SendRequest`       | 发送好友请求   | `Wxid`, `V1`, `V2`, `Scene`, `VerifyContent`               |
| `/Friend/PassVerify`        | 通过好友请求   | `Wxid`, `V1`, `V2`, `Scene`                                |
| `/Friend/Delete`            | 删除好友       | `Wxid`, `ToWxid`                                           |
| `/Friend/SetRemarks`        | 设置好友备注   | `Wxid`, `ToWxid`, `Remarks`                                |

### 工具相关 API

| API 路径               | 功能描述 | 主要参数                                 |
| ---------------------- | -------- | ---------------------------------------- |
| `/Tools/DownloadImg`   | 下载图片 | `Wxid`, `ToWxid`, `MsgId`, `DataLen`     |
| `/Tools/DownloadVideo` | 下载视频 | `Wxid`, `ToWxid`, `MsgId`, `DataLen`     |
| `/Tools/DownloadVoice` | 下载语音 | `Wxid`, `MsgId`, `Length`                |
| `/Tools/DownloadFile`  | 下载文件 | `Wxid`, `DataLen`, `AttachId`, `Section` |
| `/Tools/EmojiDownload` | 下载表情 | `Wxid`, `Md5`                            |
| `/Tools/UploadFile`    | 上传文件 | `Wxid`, `Base64`                         |

#### 文件下载详解

对于大文件，需要使用分段下载机制。`/Tools/DownloadFile` API 支持分段下载，通过 `Section` 参数指定要下载的文件块。

```python
# 分段下载示例
# 每次下载 64KB
chunk_size = 64 * 1024  # 64KB
total_len = 1024 * 1024  # 总大小 1MB
file_data = bytearray()

# 计算需要下载的分段数量
chunks = (total_len + chunk_size - 1) // chunk_size

# 分段下载
for i in range(chunks):
    start_pos = i * chunk_size
    current_chunk_size = min(chunk_size, total_len - start_pos)

    # 构造请求参数
    json_param = {
        "AppID": app_id,
        "AttachId": attach_id,
        "DataLen": total_len,
        "Section": {
            "DataLen": current_chunk_size,
            "StartPos": start_pos
        },
        "UserName": "",  # 可选参数
        "Wxid": wxid
    }

    # 发送请求
    response = await session.post(
        'http://127.0.0.1:9011/api/Tools/DownloadFile',
        json=json_param
    )

    # 处理响应
    json_resp = await response.json()
    if json_resp.get("Success"):
        data = json_resp.get("Data")
        chunk_data = base64.b64decode(data)
        file_data.extend(chunk_data)
```

#### 文件上传详解

使用 `upload_file` 方法可以上传文件到服务器，返回的信息包含 `mediaId`、`attachid` 等字段，可用于后续的文件操作。

```python
# 上传文件示例
file_info = await bot.upload_file(file_path)

# 返回的文件信息示例
# {
#   'BaseResponse': {'ret': 0, 'errMsg': {}},
#   'mediaId': '@cdn_3052020100044b30490201000204434d245e02033d14ba0204bc10949d020467fe1a3c042436396534353565362d323734302d346563372d383837342d3030376632616566313933390204052800050201000400c879beff_6c696f716d7776716c67717278647167_1',
#   'clientAppDataId': 'wxid_uz9za1pqr3ea22_1744706107_UploadFile',
#   'userName': 'wxid_uz9za1pqr3ea22',
#   'totalLen': 52757,
#   'startPos': 52757,
#   'dataLen': 0,
#   'createTime': 1744706108
# }
```

### 登录相关 API

| API 路径           | 功能描述       | 主要参数                 |
| ------------------ | -------------- | ------------------------ |
| `/Login/GetQR`     | 获取登录二维码 | `DeviceID`, `DeviceName` |
| `/Login/CheckQR`   | 检测二维码状态 | `uuid`                   |
| `/Login/HeartBeat` | 心跳包         | `wxid`                   |
| `/Login/LogOut`    | 退出登录       | `wxid`                   |

以上只是 PAD 协议的部分 API 路径，完整的 API 文档请参考官方文档或平台提供的 Swagger 文档。

## 🏆 最佳实践

### 1. 始终检查插件是否启用

```python
@on_text_message()
async def handle_text(self, bot: WechatAPIClient, message: dict):
    if not self.enable:
        return True  # 允许后续插件处理
    # 处理逻辑...
```

### 2. 使用适当的优先级

- 高优先级（80-100）：核心功能，需要先于其他插件处理
- 中等优先级（40-79）：一般功能
- 低优先级（0-39）：辅助功能，可以在其他插件之后处理

### 3. 异常处理

```python
@on_text_message()
async def handle_text(self, bot: WechatAPIClient, message: dict):
    if not self.enable:
        return True

    try:
        # 处理逻辑...
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        return True  # 出错时允许后续插件处理
```

### 4. 日志记录

```python
# 不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 5. 资源清理

```python
async def on_disable(self):
    """插件禁用时调用"""
    # 清理资源
    if hasattr(self, 'session') and self.session:
        await self.session.close()
    # 其他清理操作...
```

## 📚 示例插件

XXXBot 提供了多个示例插件，可以作为开发参考：

- **ExamplePlugin**：基本插件示例，展示各种消息处理和定时任务
- **Dify**：集成 Dify API 的 AI 对话插件，支持文本对话和图片识别功能
- **YujieSajiao**：语音处理插件示例
- **GetWeather**：天气查询插件示例
- **FileDownloader**：文件下载插件，自动下载收到的文件
- **FileSender**：文件发送插件，可以发送文件给用户

### Dify 插件图片识别功能

Dify 插件支持图片识别功能，可以分析和描述用户发送的图片内容。使用方法如下：

1. **发送图片**：用户先发送一张图片到聊天
2. **发送文本查询**：然后发送文本消息，如“这张图片是什么”或“描述一下这张图片”
3. **接收回复**：插件会自动处理图片，并返回 AI 对图片的分析结果

技术实现：

- 插件会自动缓存用户最近发送的图片
- 当用户发送文本消息时，插件会检查是否有缓存的图片
- 如果有缓存的图片，插件会将图片与文本查询一起发送给 Dify API
- Dify API 处理图片和文本，返回分析结果

注意事项：

- 图片缓存有时间限制，默认为 60 秒
- 发送文本查询时应在图片发送后的缓存时间内进行
- 支持各种常见图片格式，包括 JPEG、PNG 等

示例代码：

```python
# 处理图片消息
@on_image_message(priority=20)
async def handle_image(self, bot: WechatAPIClient, message: dict):
    if not self.enable:
        return

    # 获取图片内容并缓存
    image_content = await self.download_and_process_image(bot, message)
    if image_content:
        self.image_cache[message["FromWxid"]] = {
            "content": image_content,
            "timestamp": time.time()
        }
        logger.info(f"已缓存用户 {message['FromWxid']} 的图片")

# 处理文本消息
@on_text_message(priority=20)
async def handle_text(self, bot: WechatAPIClient, message: dict):
    if not self.enable:
        return

    # 检查是否有缓存的图片
    image_content = await self.get_cached_image(message["FromWxid"])
    files = []

    if image_content:
        # 将图片上传到 Dify
        file_id = await self.upload_file_to_dify(image_content, "image/jpeg", message["FromWxid"])
        if file_id:
            files = [file_id]

    # 调用 Dify API 处理文本和图片
    await self.dify(bot, message, message["Content"], files=files)
```

## ❓ 常见问题

### 插件加载失败

1. 检查 `__init__.py` 是否正确导入主类
2. 检查主类是否继承自 `PluginBase`
3. 检查配置文件格式是否正确

### 插件不响应消息

1. 检查插件是否启用 (`self.enable = True`)
2. 检查消息处理函数是否使用了正确的装饰器
3. 检查优先级是否合适，是否被其他插件拦截

### 定时任务不执行

1. 检查定时任务装饰器参数是否正确
2. 检查插件是否启用
3. 检查系统时间是否正确

### Dify 图片识别功能不工作

1. 检查图片发送后是否在缓存时间内（60 秒）发送了文本查询
2. 检查日志中是否有“已缓存用户 xxx 的图片”的信息
3. 确认 Dify API 配置是否正确，包括 API 密钥和基础 URL
4. 确认使用的 Dify 模型是否支持图片识别功能

---

如有更多问题，请参考 [XXXBot 文档](https://github.com/NanSsye/XXXBot) 或提交 Issue。

祝您开发愉快！🎉
