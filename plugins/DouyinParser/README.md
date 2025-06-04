# DouyinParser 插件

这是一个为 XYBot 开发的 DouyinParser 插件，可以无需借用API实现本地解析抖音视频链接并发送视频卡片消息。

## ✨ 功能特性
- 解析抖音视频链接
- 发送视频卡片消息

## 🛠️ 安装方法
1. 确保已安装 XYBot 框架
2. 将插件文件夹复制到 `plugins/DouyinParser/` 目录下
3. 创建配置文件 `plugins/DouyinParser/config.toml`
4. 重启 XYBot 服务

## ⚙️ 配置说明
在 `plugins/DouyinParser/config.toml` 中进行配置：

```toml
[DouyinParser]
enable = true  # 是否启用插件
allowed_groups = ["group_id1@chatroom", "group_id2@chatroom"]  # 允许使用插件的群组
```

## 🚀 使用指南
- 在群聊中发送包含抖音链接的消息，插件会自动解析并发送视频卡片。

## 🔍 常见问题
1. **解析失败**
   - 请检查网络连接，确保配置文件正确。

2. **视频链接无效**
   - 请确保发送的链接为有效的抖音视频链接。

## 🔄 版本历史
- v1.0.0: 初始版本发布

感谢使用 DouyinParser 插件！
