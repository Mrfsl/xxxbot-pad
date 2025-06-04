# XXXBot-PAD Docker 部署指南

## 简介

本指南详细说明如何使用 Docker 部署 XXXBot-PAD，特别是如何使用修改后的 docker-compose.yml 文件，将容器内的应用目录直接映射到主机上，方便直接访问和修改文件。

## 修改后的 docker-compose.yml

```yaml
services:
  xxxbot:
    image: nanssye/xxxbot-pad:latest
    container_name: xxxbot-pad
    restart: unless-stopped
    pull_policy: always # 确保每次都检查并拉取最新的镜像
    ports:
      - "9090:9090" # 管理后台端口
      - "3000:3000" # WeTTy终端端口
    volumes:
      - ./app:/app # 直接映射当前目录下的app文件夹到容器的/app
      - redis_data:/var/lib/redis

volumes:
  redis_data:
    name: redis_data
```

## 主要变更

原始的 docker-compose.yml 文件使用命名卷 `xxxbot-pad:/app` 来映射容器内的 `/app` 目录，这意味着数据被保存在 Docker 管理的卷中，不方便直接访问和修改。

修改后的文件使用 `./app:/app` 将容器内的 `/app` 目录直接映射到当前目录下的 `app` 文件夹，这样您可以直接访问和修改这些文件，无需进入容器或使用 Docker 命令。

## 部署步骤

### 1. 准备目录结构

首先，创建一个用于存放 XXXBot-PAD 数据的目录：

```bash
mkdir -p app
```

这个 `app` 目录将被映射到容器内的 `/app` 目录，所有的配置文件、插件和数据都将存储在这里。

### 2. 创建 docker-compose.yml 文件

将修改后的 docker-compose.yml 内容保存到文件中：

```bash
# 使用文本编辑器创建文件
nano docker-compose.yml
# 或
vim docker-compose.yml
```

粘贴上面提供的 docker-compose.yml 内容，保存并退出。

### 3. 启动服务

使用以下命令启动 XXXBot-PAD：

```bash
docker-compose up -d
```

首次启动时，Docker 会自动下载镜像并创建容器。启动完成后，您可以通过以下地址访问管理后台：

- 管理后台：http://localhost:9090
- WeTTy 终端：http://localhost:3000

### 4. 查看日志

您可以使用以下命令查看容器的日志：

```bash
docker-compose logs -f
```

### 5. 停止服务

使用以下命令停止 XXXBot-PAD：

```bash
docker-compose down
```

## 目录结构说明

启动容器后，`app` 目录下将会生成以下文件和目录：

```
app/
├── config.json          # 主配置文件
├── main_config.toml     # 主配置文件（新版）
├── plugins/             # 插件目录
├── tmp/                 # 临时文件目录
├── logs/                # 日志目录
└── ...
```

您可以直接编辑这些文件，修改将立即生效（某些配置可能需要重启服务）。

## 配置说明

### 主配置文件

主配置文件位于 `app/main_config.toml`，您可以根据需要修改以下配置：

```toml
[Protocol]
version = "849"  # 可选值: "849", "855" 或 "ipad"

[Admin]
username = "admin"  # 管理后台用户名
password = "admin"  # 管理后台密码

[API]
host = "127.0.0.1"  # API 主机地址
port = 9011         # API 端口
```

### 插件配置

每个插件的配置文件位于 `app/plugins/插件名/config.toml`，您可以根据需要修改插件配置。

## 数据持久化

- 所有的配置文件、插件和数据都存储在 `app` 目录中，即使容器被删除，数据也不会丢失。
- Redis 数据存储在 Docker 卷 `redis_data` 中，确保数据的持久性。

## 更新镜像

使用以下命令更新 XXXBot-PAD 到最新版本：

```bash
docker-compose pull
docker-compose up -d
```

## 常见问题

### 1. 如何修改端口？

如果您需要修改端口映射，可以编辑 `docker-compose.yml` 文件中的 `ports` 部分：

```yaml
ports:
  - "自定义端口:9090"  # 管理后台端口
  - "自定义端口:3000"  # WeTTy终端端口
```

### 2. 如何进入容器？

使用以下命令进入容器：

```bash
docker-compose exec xxxbot bash
```

### 3. 如何备份数据？

只需备份 `app` 目录即可，它包含了所有的配置文件、插件和数据。

### 4. 权限问题

如果遇到权限问题，可能是因为容器内的进程以特定用户运行，而主机上的目录权限不匹配。可以尝试以下解决方案：

```bash
# 修改app目录的权限
chmod -R 777 app
```

或者在 docker-compose.yml 中添加用户映射：

```yaml
services:
  xxxbot:
    # ... 其他配置 ...
    user: "1000:1000"  # 使用主机上的UID:GID
```

### 5. 容器启动失败

如果容器启动失败，可以查看日志找出原因：

```bash
docker-compose logs
```

常见原因包括：
- 端口冲突：其他服务已经占用了9090或3000端口
- 权限问题：无法写入映射的目录
- 配置错误：main_config.toml中的配置有误

## 注意事项

- 请确保您的服务器防火墙允许访问您配置的端口。
- 如果您在公网环境部署，请务必修改默认的管理后台密码。
- 定期备份您的数据，以防意外情况发生。

## 许可证

本项目仅供学习和交流使用，禁止用于商业用途。
