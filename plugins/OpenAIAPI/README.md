# OpenAI API 兼容插件 🚀

## 简介

OpenAI API 兼容插件为 XYBot 提供了标准的 OpenAI API 接口，使您可以将机器人与任何支持 OpenAI API 的应用程序集成。这个插件创建了一个本地 API 服务器，它可以将请求转发到您配置的后端 AI 服务（如 OpenAI、Azure OpenAI 或其他兼容的 API）。

## 特性

- **标准 OpenAI API 兼容性**：完全兼容 OpenAI API 的请求和响应格式 ✅
- **灵活的后端配置**：可以连接到 OpenAI、Azure OpenAI 或其他兼容的 API 服务 🔄
- **模型配置**：支持配置可用模型列表和默认模型 🤖
- **安全访问控制**：可以设置 API 密钥验证 🔐
- **积分系统集成**：支持使用 XYBot 的积分系统控制 API 使用 💰
- **代理支持**：支持配置 HTTP 代理，解决网络访问问题 🌐

## 安装

1. 将插件文件夹复制到 `plugins` 目录
2. 编辑 `config.toml` 配置文件
3. 重启 XYBot 或使用管理命令加载插件

## 配置说明

```toml
[OpenAIAPI]
enable = true                           # 是否启用此功能
api-key = ""                            # 后端API密钥，如果后端需要
base-url = "https://api.openai.com/v1"  # 后端API地址，可以是OpenAI或兼容的API服务

# 模型配置
default-model = "gpt-3.5-turbo"         # 默认使用的模型
available-models = [                    # 可用模型列表
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo"
]

# 插件配置
port = 8100                             # API服务端口
host = "0.0.0.0"                        # API服务主机

# 积分系统
price = 0                               # 每次使用扣除的积分，0表示不扣除
admin_ignore = true                     # 管理员是否忽略积分扣除
whitelist_ignore = true                 # 白名单用户是否忽略积分扣除

# Http代理设置
http-proxy = ""                         # HTTP代理设置

# 高级设置
max_tokens = 4096                       # 最大token数
temperature = 0.7                       # 温度参数
top_p = 1.0                             # Top-p采样
frequency_penalty = 0.0                 # 频率惩罚
presence_penalty = 0.0                  # 存在惩罚
```

## 使用方法

1. 启用插件后，API 服务器将在配置的端口上启动
2. 使用标准的 OpenAI API 客户端连接到 `http://你的IP:配置的端口`
3. API 密钥可以是任意值，将被转发到后端服务

### 示例（Python）

```python
import openai

# 设置API基础URL为你的机器人地址
openai.api_base = "http://你的IP:8100/v1"
# API密钥可以是任意值，将被转发到后端
openai.api_key = "你的API密钥"

# 使用标准的OpenAI API调用
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是一个有用的助手。"},
        {"role": "user", "content": "你好，请介绍一下自己。"}
    ]
)

print(response.choices[0].message.content)
```

## 支持的API端点

- `/v1/chat/completions` - 聊天完成API
- `/v1/models` - 模型列表API

## 注意事项

- 此插件需要安装额外的依赖：`fastapi` 和 `uvicorn`
- 确保配置的端口未被其他应用占用
- 如果使用代理，确保代理服务器正常工作
- 后端API密钥需要有足够的配额

## 故障排除

- 如果API服务无法启动，检查端口是否被占用
- 如果请求失败，检查后端API地址和密钥是否正确
- 如果响应速度慢，考虑使用代理或更换后端服务

## 开发者信息

- 作者：XYBot团队
- 版本：1.0.0
- 许可证：MIT
