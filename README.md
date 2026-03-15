<p align="center">
  <img src="web/public/favicon.svg" alt="OpenHarmony Docs RAG" width="96" height="96" />
</p>

# OpenHarmony Docs RAG

面向 OpenHarmony 中文开发内容的 RAG 系统，提供单入口 Web 控制台、检索与问答 API、Skill 封装和 MCP 接入能力。

> [!TIP]
> 这套系统只推荐通过 Docker Compose 部署。Web、API、Qdrant 和运行时配置已经围绕容器交付方式收敛完成。

## 为什么用它

- 单入口交付：Web 控制台和 API 共用 `http://localhost:8000`
- 一键建库：支持同步仓库、增量更新、暂停、恢复和实时日志
- 运维可视化：可直接查看服务状态、端口、索引统计和文档状态
- 在线改配置：Web 控制台直接读写 `deploy/app.env`
- 多入口接入：同时提供 API、Skill 和 MCP
- 多架构镜像：默认发布 `linux/amd64` 和 `linux/arm64`

## 快速开始

### 1. 准备运行环境

- 安装 Docker Engine 和 Docker Compose
- 确保宿主机可以访问外部模型服务
- 预留端口：
  - `8000`：Web + API
  - `6333/6334`：Qdrant

### 2. 编辑运行时配置

默认配置文件是 [deploy/app.env](deploy/app.env)。

至少需要填写这些字段：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_CHAT_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`

常用可选项：

- `RERANK_ENABLED`
- `RERANK_MODEL`
- `DOCS_LOCAL_PATH`
- `DOCS_INCLUDE_DIRS`
- `QDRANT_COLLECTION`
- `API_PORT`

> [!NOTE]
> `deploy/app.env` 是唯一推荐的部署配置入口。Web 控制台的“服务状态”页编辑的也是这份文件。

### 3. 启动服务

```bash
docker compose --env-file deploy/app.env pull
docker compose --env-file deploy/app.env up -d
```

或者使用包装脚本：

```bash
./deploy/deploy.sh
```

启动完成后访问：

- Web 控制台：`http://localhost:8000/`
- 健康检查：`http://localhost:8000/health`
- OpenAPI：`http://localhost:8000/docs`

## Web 控制台

控制台包含以下主要页面：

- `工作台`：启动默认工作流 `sync_incremental`
- `构建中心`：查看阶段、日志、暂停和恢复
- `接口实验室`：调试 `/retrieve` 与 `/query`
- `智能问答`：查看答案、引用、耗时和意图
- `服务状态`：查看 API、Qdrant、SQLite、端口和 `deploy/app.env`
- `集成指南`：查看 Skill / MCP 接入片段
- `索引浏览`：浏览文档状态、目录统计和过滤结果

### 建库方式

默认部署不会自动同步仓库或自动建库。

推荐方式：

- 在 Web 控制台点击“同步文档并增量构建”
- 必要时在“构建中心”中执行暂停或恢复

手工方式：

```bash
docker compose --env-file deploy/app.env exec app python scripts/build_index.py
docker compose --env-file deploy/app.env exec app python scripts/build_index.py --full-rebuild
```

### 更新配置

1. 在 Web 控制台保存 `deploy/app.env`
2. 重新应用配置：

```bash
docker compose --env-file deploy/app.env up -d
```

## API

### 核心接口

- `POST /query`
  - 输入：`query`、可选 `top_k`、可选 `filters`
  - 输出：答案、引用、`trace_id`、耗时、意图
- `POST /retrieve`
  - 输入：`query`、可选 `top_k`、可选 `filters`
  - 输出：文档块、`trace_id`、耗时
- `GET /health`
- `GET /capabilities`
- `GET /stats`
- `GET /documents`

### 支持的过滤字段

- `top_dir`
- `kit`
- `subsystem`
- `page_kind`
- `exclude_readme`

### Web 管理接口

- `GET /web/services`
- `GET /web/env`
- `PUT /web/env`
- `GET /web/builds`
- `POST /web/builds`
- `GET /web/builds/{id}`
- `POST /web/builds/{id}/pause`
- `POST /web/builds/{id}/resume`
- `GET /web/builds/{id}/events`

构建模式：

- `sync_incremental`
- `incremental`
- `full_rebuild`

## Skill 与 MCP

### Skill

Python 封装入口：

- [skill/rag_skill_wrapper.py](skill/rag_skill_wrapper.py)
- [skill/SKILL.md](skill/SKILL.md)

示例：

```python
from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://127.0.0.1:8000")
result = await skill.ask_question("如何创建 UIAbility 组件？")
print(skill.format_answer(result))
```

### MCP

stdio server 入口：

- [rag_mcp/stdio_server.py](rag_mcp/stdio_server.py)
- [mcp/server.example.json](mcp/server.example.json)

示例：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://127.0.0.1:8000 \
./venv/bin/python -m rag_mcp.stdio_server
```

## 运维

常用命令：

```bash
docker compose --env-file deploy/app.env ps
docker compose --env-file deploy/app.env logs -f app
docker compose --env-file deploy/app.env logs -f qdrant
docker compose --env-file deploy/app.env down
```

持久化数据：

- `./data/raw/openharmony-docs`：同步下来的文档仓库
- `./storage/metadata.db`：SQLite 元数据
- `qdrant_storage` volume：向量数据

## 镜像发布

镜像和版本发布由 GitHub Actions 维护：

- [release.yml](.github/workflows/release.yml)
  - 推送 `main` 后执行 `semantic-release`
  - 自动生成版本说明
  - 自动创建 `vX.Y.Z` tag 和 GitHub Release
- [publish-image.yml](.github/workflows/publish-image.yml)
  - 推送 `main` 发布 `latest`
  - 推送 `v*` tag 发布版本镜像
  - 同时发布 `linux/amd64` 和 `linux/arm64`

默认镜像：

```text
ghcr.io/charmingyouyou/openharmony-docs-rag-app:latest
```

## 故障排查

### 配置问题

```bash
grep -E '^(LLM_|EMBEDDING_|RERANK_|DOCS_|API_)' deploy/app.env
```

### Qdrant 未就绪

```bash
docker compose --env-file deploy/app.env logs -f qdrant
curl http://localhost:6333/collections
```

### 应用启动失败

```bash
docker compose --env-file deploy/app.env logs -f app
curl http://localhost:8000/health
```

### Apple Silicon 拉不到镜像

```bash
docker buildx imagetools inspect ghcr.io/charmingyouyou/openharmony-docs-rag-app:latest
```

输出中应包含：

- `linux/amd64`
- `linux/arm64`
