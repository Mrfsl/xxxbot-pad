# XXXBot 更新指南

## 确保获取最新版本

为了确保您始终使用最新版本的 XXXBot，请按照以下步骤操作：

### 方法一：使用更新后的 docker-compose.yml（推荐）

我们已经更新了 `docker-compose.yml` 文件，添加了 `pull_policy: always` 设置，这将确保每次启动容器时都会检查并拉取最新的镜像。

1. 使用更新后的 `docker-compose.yml` 文件（已包含在最新版本中）
2. 运行以下命令重新启动服务：

```bash
# 停止当前运行的容器
docker-compose down

# 拉取最新镜像并启动
docker-compose pull
docker-compose up -d
```

### 方法二：手动拉取最新镜像

如果您不想修改 `docker-compose.yml` 文件，也可以手动拉取最新镜像：

```bash
# 拉取最新镜像
docker pull nanssye/xxxbot-pad:latest

# 停止并删除旧容器
docker-compose down

# 使用新镜像启动容器
docker-compose up -d
```

### 方法三：使用管理后台重启容器

如果您已经更新了 `docker-compose.yml` 文件（包含 `pull_policy: always`），可以直接使用管理后台的重启容器功能：

1. 登录管理后台（默认地址：http://您的服务器IP:9090）
2. 进入"系统管理"页面
3. 在"机器人信息"卡片中，点击"重启容器"按钮
4. 确认重启操作

重启后，Docker 将自动检查并拉取最新的镜像。

## 验证版本

重启后，您可以在管理后台的右上角看到当前版本号。确保版本号与最新发布的版本一致。

## 常见问题

### Q: 我更新了但版本号没有变化

A: 这可能是因为：
1. 镜像缓存问题 - 尝试手动拉取最新镜像
2. 没有新版本发布 - 检查发布页面确认最新版本
3. 持久化数据问题 - 检查 `version.json` 文件是否被持久化存储覆盖

### Q: 更新后功能不正常

A: 尝试以下步骤：
1. 清除浏览器缓存
2. 检查日志文件（在管理后台的"系统管理"页面）
3. 如果问题持续，可以尝试删除持久化数据并重新启动（注意：这将删除所有配置和数据）

```bash
docker-compose down
docker volume rm xxxbot-pad
docker-compose up -d
```

## 联系支持

如果您在更新过程中遇到任何问题，请联系我们的支持团队获取帮助。
