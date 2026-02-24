# HybridMemory

整合长期记忆与短期记忆的混合记忆系统插件，专为 AstrBot 设计。

[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-blue)](https://github.com/SoulTer/AstrBot)
[![License](https://img.shields.io/github/license/lxfight/hybrid_memory)](LICENSE)

## 简介

HybridMemory 是基于 [LivingMemory](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory) 和 [Mnemosyne](https://github.com/lxfight/astrbot_plugin_mnemosyne) 整合而成的混合记忆插件，同时具备：

- **长期记忆**：持久化存储，支持语义搜索，动态生命周期
- **短期记忆**：会话级临时存储，自动总结
- **WebUI 管理面板**：可视化查看、编辑、删除记忆

## 功能特性

### 长期记忆 (基于 LivingMemory)
- **向量语义搜索**: 使用 Faiss 向量数据库存储记忆，支持语义相似度检索
- **动态生命周期**: 记忆具有重要性评分，可随时间自动衰减
- **持久化存储**: SQLite + 向量索引的双重存储机制

### 短期记忆 (基于 Mnemosyne)
- **会话级临时存储**: 按会话分开存储对话历史
- **自动总结**: 达到阈值后自动总结会话内容并转入长期记忆
- **内存缓存**: 快速响应的内存缓存 + 持久化存储

### WebUI 管理面板
- 查看/编辑/删除所有长期记忆
- 查看/清除短期记忆会话
- 记忆统计分析
- 搜索过滤功能

---

## 安装教程

### 方式一：从 GitHub 安装（推荐）

#### 1. 下载插件

访问 GitHub 仓库，点击 **Code** → **Download ZIP**

或者使用命令行：
```bash
git clone https://github.com/taolicx/hybrid_memory.git
```

### 1. 安装依赖

```bash
pip install aiohttp
```

#### 3. 放置插件

将下载的 `hybrid_memory` 文件夹复制到 AstrBot 的插件目录：

```
AstrBot/
└── data/
    └── plugins/
        └── hybrid_memory/    # 放入这里
```

#### 4. 重启 AstrBot

重启服务后，插件会自动加载。

---

### 方式二：手动安装

#### 1. 创建插件目录

在 AstrBot 插件目录下创建 `hybrid_memory` 文件夹

#### 2. 上传文件

将插件所有文件上传到该目录：
- `main.py`
- `metadata.yaml`
- `requirements.txt`
- `_conf_schema.json`
- `README.md`
- `core/` 目录
- `webui/` 目录
- `storage/` 目录（如有）

#### 3. 安装依赖

```bash
cd 你的插件目录
pip install -r requirements.txt
```

#### 4. 重启 AstrBot

---

## 配置说明

### 通过 WebUI 配置

插件启动后，访问 `http://127.0.0.1:9241`，使用以下默认账号登录：
- 用户名：`admin`
- 密码：`admin`

登录后可在界面中查看和编辑配置。

### 通过配置文件

在 AstrBot 管理面板中配置以下选项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `webui.enabled` | 启用 WebUI | `true` |
| `webui.host` | WebUI 监听地址 | `127.0.0.1` |
| `webui.port` | WebUI 端口 | `9241` |
| `webui.username` | WebUI 登录用户名 | `admin` |
| `webui.password` | WebUI 登录密码 | `admin` |
| `long_term_memory.embedding_provider` | Embedding Provider | - |
| `long_term_memory.llm_provider` | LLM Provider | - |
| `long_term_memory.decay_enabled` | 启用记忆衰减 | `true` |
| `long_term_memory.decay_days` | 记忆衰减天数 | `30` |
| `long_term_memory.retrieval_top_k` | 检索返回数量 | `5` |
| `short_term_memory.summary_threshold` | 自动总结阈值 | `20` |
| `short_term_memory.max_messages` | 最大消息数 | `50` |

---

## 命令列表

| 命令 | 说明 | 权限 |
|------|------|------|
| `/hmem status` | 查看记忆系统状态 | 管理员 |
| `/hmem search <关键词> [k]` | 搜索记忆 (k 默认 5) | 管理员 |
| `/hmem forget <id> [long/short]` | 删除记忆 (默认长期) | 管理员 |
| `/hmem rebuild-index` | 重建向量索引 | 管理员 |
| `/hmem webui` | 获取 WebUI 访问地址 | 管理员 |
| `/hmem summarize` | 立即总结当前会话 | 管理员 |
| `/hmem reset` | 重置当前会话记忆 | 管理员 |
| `/hmem stats` | 查看记忆统计 | 管理员 |
| `/hmem help` | 显示帮助 | 管理员 |

---

## 使用示例

### 查看状态
```
用户: /hmem status
机器人: === HybridMemory 状态 ===

长期记忆: 10 条
短期记忆: 25 条 (3 个会话)
WebUI: 已启用
```

### 搜索记忆
```
用户: /hmem search 名字
机器人: 找到 3 条相关记忆:

1. [ID:5] 用户说他叫小明...
   相似度: 0.95

2. [ID:2] 昨天提到了我的名字...
   相似度: 0.82
```

### 删除记忆
```
用户: /hmem forget 5 long
机器人: 长期记忆已删除
```

---

## 工作原理

### 记忆流程

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  用户消息   │ ──▶ │  短期记忆    │ ──▶ │ 自动总结    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ LLM 请求时   │     │  长期记忆   │
                    │ 注入上下文   │ ◀── │ (持久化)    │
                    └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  LLM 响应    │
                    │ 存储记忆    │
                    └──────────────┘
```

### 记忆注入

在每次 LLM 请求前，插件会自动：
1. 检索相关长期记忆（语义相似度）
2. 获取会话短期记忆（最近对话）
3. 组合成记忆上下文注入系统提示词

这样机器人可以"记住"之前的对话内容。

---

## 数据存储

插件数据存储在 `{plugin_data_dir}/` 目录下：

```
{plugin_data_dir}/storage/
├── long_term_memory.db     # 长期记忆 SQLite 数据库
├── short_term_memory.db    # 短期记忆 SQLite 数据库
└── vector_index/          # Faiss 向量索引
    ├── index.faiss
    └── metadata.json
```

---

## WebUI 界面预览

### 统计页面
- 显示长期记忆总数
- 显示短期记忆会话数
- 显示消息总数

### 长期记忆页面
- 记忆列表展示
- 搜索过滤
- 编辑/删除功能

### 短期记忆页面
- 会话列表
- 清除会话功能

---

## 常见问题

### Q: 启动后提示 "WebUI 未启用"
A: 请在配置中设置 `webui.enabled: true`

### Q: 向量搜索不工作
A: 需要在配置中设置 `embedding_provider`，否则只会返回最近添加的记忆

### Q: 自动总结不工作
A: 需要在配置中设置 `llm_provider`，插件才能调用 LLM 进行总结

### Q: 端口被占用
A: 修改配置中的 `webui.port` 为其他端口

### Q: 忘记 WebUI 密码
A: 删除插件目录下的 `storage` 文件夹并重启（会重置所有数据）

---

## 注意事项

- 首次启动会自动创建数据库和索引目录
- 向量检索需要配置 Embedding Provider 才能完全生效
- 记忆总结需要配置 LLM Provider
- **建议修改默认 WebUI 账号密码确保安全**
- 定期备份 `storage` 目录防止数据丢失

---

## 更新日志

### v1.0.0
- 初始版本
- 整合长期记忆与短期记忆
- 添加 WebUI 管理面板

---

## 许可

本插件基于 [AGPL-3.0](LICENSE) 许可证开源。

---

## 相关链接

- [AstrBot 官网](https://astrbot.com/)
- [LivingMemory 插件](https://github.com/lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory)
- [Mnemosyne 插件](https://github.com/lxfight/astrbot_plugin_mnemosyne)
