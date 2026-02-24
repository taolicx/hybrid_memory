# Docker 环境安装教程

本文档介绍如何在 Docker 容器中运行的 AstrBot 上安装 HybridMemory 插件。

## 前置条件

- 你的 AstrBot 运行在 Docker 容器中
- 你可以通过命令行进入容器

## 安装步骤

### 方式一：通过 volume 挂载（推荐）

#### 1. 停止并删除现有容器（保留数据）

```bash
# 停止容器
docker stop astrbot

# 删除容器（保留数据卷）
docker rm astrbot
```

#### 2. 创建插件目录

在宿主机上创建插件目录：

```bash
mkdir -p /opt/astrbot/plugins/hybrid_memory
```

#### 3. 复制插件文件

将插件所有文件复制到该目录：

```bash
cp -r ./hybrid_memory/* /opt/astrbot/plugins/hybrid_memory/
```

#### 4. 重新创建容器并挂载插件目录

```bash
docker run -d \
  --name astrbot \
  -v astrbot_data:/app/data \
  -v /opt/astrbot/plugins/hybrid_memory:/app/data/plugins/hybrid_memory \
  -p 9241:9241 \
  -p 3000:3000 \
  --restart unless-stopped \
  your_astronano/astrbot:latest
```

> **注意**：将 `your_astronano/astrbot:latest` 替换为你实际使用的镜像

#### 5. 进入容器安装依赖

```bash
docker exec -it astrbot bash
```

在容器内安装 Python 依赖：

```bash
pip install aiohttp
```

#### 6. 重启插件

在 AstrBot 管理界面重启插件，或在容器内执行：

```bash
docker restart astrbot
```

---

### 方式二：直接进入容器安装

#### 1. 进入容器

```bash
docker exec -it astrbot bash
```

#### 2. 创建插件目录

```bash
mkdir -p /app/data/plugins/hybrid_memory
```

#### 3. 安装依赖

```bash
pip install aiohttp faiss-cpu numpy
```

如果网络问题导致安装失败，可以：

```bash
# 使用国内镜像
pip install aiohttp faiss-cpu numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 4. 复制插件文件

从宿主机复制文件到容器：

```bash
# 在宿主机执行
docker cp ./hybrid_memory/. astrbot:/app/data/plugins/hybrid_memory/
```

#### 5. 重启容器

```bash
docker restart astrbot
```

---

### 方式三：使用 docker-compose

如果使用 docker-compose，修改 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  astrbot:
    image: your_astronano/astrbot:latest
    container_name: astrbot
    ports:
      - "3000:3000"
      - "9241:9241"
    volumes:
      - astrbot_data:/app/data
      - ./plugins/hybrid_memory:/app/data/plugins/hybrid_memory  # 添加这行
    restart: unless-stopped

volumes:
  astrbot_data:
```

然后执行：

```bash
docker-compose down
docker-compose up -d
docker exec -it astrbot pip install aiohttp
docker restart astrbot
```

---

## 验证安装

### 1. 检查插件是否加载

在容器内执行：

```bash
docker exec -it astrbot bash -c "ls -la /app/data/plugins/hybrid_memory/"
```

应该能看到插件文件列表。

### 2. 测试命令

在 QQ 或其他平台发送：

```
/hmem status
```

如果返回状态信息，说明插件安装成功。

### 3. 访问 WebUI

浏览器访问：`http://你的服务器IP:9241`

使用默认账号登录：
- 用户名：`admin`
- 密码：`admin`

---

## 配置修改

### 修改 WebUI 端口

如果 9241 端口被占用，可以修改配置：

```bash
docker exec -it astrbot vi /app/data/plugins/hybrid_memory/_conf_schema.json
```

修改 `webui.port` 的 default 值。

或者在 AstrBot 管理界面配置。

### 修改登录密码

同样在 `_conf_schema.json` 中修改 `webui.password`。

---

## 常见问题

### Q: 插件没有加载

A: 检查插件目录名称是否为 `hybrid_memory`，确保目录结构正确：
```
/app/data/plugins/hybrid_memory/
├── main.py
├── metadata.yaml
├── core/
└── webui/
```

### Q: 依赖安装失败

A: 尝试使用国内镜像：
```bash
pip install aiohttp faiss-cpu numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: WebUI 无法访问

A: 检查端口是否已映射：
```bash
docker port astrbot
```

### Q: 数据存储在哪里

A: 插件数据存储在 Docker 卷 `astrbot_data` 中：
```
docker volume inspect astrbot_data
```

---

## 更新插件

1. 停止容器
2. 备份数据
3. 更新文件
4. 重新安装依赖
5. 重启容器

```bash
docker stop astrbot
# 备份插件数据（可选）
docker cp astrbot:/app/data/plugins/hybrid_memory/storage ./backup_storage
# 更新文件
cp -r ./hybrid_memory_new/* /opt/astrbot/plugins/hybrid_memory/
# 重新安装依赖
docker exec -it astrbot pip install aiohttp
docker start astrbot
```

---

如有问题，请检查容器日志：

```bash
docker logs astrbot
```