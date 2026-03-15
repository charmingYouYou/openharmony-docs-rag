# OpenHarmony 中文文档 RAG 系统

基于 OpenHarmony 中文开发文档构建的检索增强生成（RAG）系统，专注于应用开发指南和 API 使用最佳实践。

## 特性

- **智能意图识别**：自动识别查询意图（指南、API 使用、设计规范、概念）
- **文档类型感知**：针对 API 参考、开发指南、设计规范采用不同的切分和检索策略
- **混合检索**：向量检索 + 意图增强 + 元数据过滤
- **精准引用**：返回准确的文档路径、标题、片段和源链接
- **多入口支持**：Web API、Skill Wrapper、MCP Server

## 技术栈

- **API 框架**：FastAPI
- **向量数据库**：Qdrant
- **元数据存储**：SQLite
- **Embedding**：SiliconFlow `Qwen/Qwen3-Embedding-4B`
- **LLM**：环境变量指定的 OpenAI 兼容聊天模型

## 项目结构

```
openharmony-docs-rag/
├── app/                    # 应用代码
│   ├── core/              # 核心模块（解析、切分、嵌入）
│   ├── services/          # 服务层（检索、问答）
│   ├── storage/           # 存储层（Qdrant、SQLite）
│   ├── api/               # API 端点
│   └── utils/             # 工具函数
├── scripts/               # 脚本（同步、建库、评测）
├── data/                  # 数据目录
├── storage/               # SQLite 数据库
├── mcp/                   # MCP Server
├── skill/                 # Skill Wrapper
└── tests/                 # 测试
```

## 对外交付部署（推荐）

### 1. 部署前准备

- 安装 Docker Engine 和 Docker Compose
- 准备可访问外部模型服务的网络环境
- 预留端口：`8000`（Web + API）、`6333/6334`（Qdrant）
- 预留持久化目录：`./data`、`./storage`
- 默认交付镜像：`ghcr.io/charmingyouyou/openharmony-docs-rag-app:latest`

### 2. 配置环境变量

如果你已经拿到了仓库，直接在根目录执行：

```bash
cd openharmony-docs-rag
cp .env.example .env
```

如果你只想按 `docker-compose.yml` 直接安装，最小只需要这两个文件：

- `docker-compose.yml`
- `.env.example`

然后执行：

```bash
cp .env.example .env
```

默认至少需要填写这些核心变量：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_CHAT_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`
- `RERANK_ENABLED`
- `RERANK_MODEL`
- `DOCS_LOCAL_PATH`

其中：

- `RERANK_API_KEY` 和 `RERANK_BASE_URL` 默认复用 `EMBEDDING_*`
- `EMBEDDING_DOCUMENT_INPUT_TYPE` / `EMBEDDING_QUERY_INPUT_TYPE` 默认分别是 `document` / `query`
- `EMBEDDING_QUERY_PREFIX` 保留在 env 中，便于按模型调整检索 instruction
- 其余 batch、重试、chunk 大小等都属于可选高级配置

```bash
grep -E '^(API_|LLM_|EMBEDDING_|RERANK_|DOCS_)' .env
```

如果你需要覆盖默认镜像地址，可以在 `.env` 里追加：

```bash
OPENHARMONY_RAG_IMAGE=ghcr.io/charmingyouyou/openharmony-docs-rag-app:latest
```

### 3. 一键部署

推荐直接按 Compose 安装：

```bash
docker compose pull
docker compose up -d
```

如果你已经拿到了完整仓库，也可以使用仓库内置脚本：

```bash
./deploy/deploy.sh
```

它会执行：

- 检查 `.env` 是否存在
- 执行 `docker compose pull`
- 执行 `docker compose up -d`
- 等待 `http://127.0.0.1:${API_PORT}/health` 返回成功
- 输出 Web / API 入口和常用运维命令

### 4. 启动后访问方式

- Web 控制台：`http://localhost:8000/`
- 健康检查：`http://localhost:8000/health`
- OpenAPI 文档：`http://localhost:8000/docs`
- 关键接口：
  - `POST /query`
  - `POST /retrieve`
  - `GET /stats`
  - `GET /web/services`

### 5. 常用运维命令

```bash
# 拉取最新镜像
docker compose pull

# 启动或更新
docker compose up -d

# 查看状态
docker compose ps

# 查看应用日志
docker compose logs -f app

# 查看 Qdrant 日志
docker compose logs -f qdrant

# 停止服务
docker compose down
```

### 6. 数据目录说明

- `./data/raw/openharmony-docs`：同步下来的 OpenHarmony 文档仓库
- `./storage/metadata.db`：SQLite 元数据
- `qdrant_storage` volume：Qdrant 向量数据

默认部署不会自动触发建库。你可以在 Web 控制台中执行“同步文档并增量构建”，也可以手工执行：

```bash
# 默认增量构建
python scripts/build_index.py

# 显式全量重建
python scripts/build_index.py --full-rebuild
```

### 7. skill / MCP 接入

部署完成后，将 `OPENHARMONY_RAG_API_BASE_URL` 指向你的交付地址，例如：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://<部署地址>:8000
```

- Skill 分发文件：`skill/SKILL.md`、`skill/rag_skill_wrapper.py`
- MCP 分发文件：`mcp/server.example.json`、`rag_mcp.stdio_server`

### 8. 故障排查

#### 端口被占用

```bash
lsof -i :8000
lsof -i :6333
```

#### `.env` 缺失或配置不完整

```bash
cp .env.example .env
grep -E '^(LLM_|EMBEDDING_|RERANK_)' .env
```

#### Qdrant 未就绪

```bash
docker compose logs -f qdrant
curl http://localhost:6333/collections
```

#### Web 页面空白或资源未加载

```bash
docker compose logs -f app
curl http://localhost:8000/health
curl -I http://localhost:8000/
```

## 镜像发布（维护者）

仓库内置了两条 GitHub Actions 发布链路：

- `.github/workflows/release.yml`
  - 在推送 `main` 后自动运行 `semantic-release`
  - 基于 Conventional Commits 自动更新 `CHANGELOG.md`
  - 自动创建 Git tag（格式 `vX.Y.Z`）
  - 自动创建 GitHub Release
- `.github/workflows/publish-image.yml`
  - 在推送 `main` 时发布 `latest` 镜像
  - 在推送 `v*` tag 时发布对应版本镜像

默认镜像会推送到：

```bash
ghcr.io/charmingyouyou/openharmony-docs-rag-app:latest
```

如果你使用不同的镜像仓库，请同步调整：

- `docker-compose.yml` 中的 `OPENHARMONY_RAG_IMAGE` 默认值
- `.env.example` 中的镜像示例值
- `.github/workflows/publish-image.yml` 中的 `IMAGE_NAME`

如果你希望自动 release 生效，提交信息需要遵循 Conventional Commits，例如：

```text
feat: add incremental build controls
fix: handle paused build status in web console
feat!: change deployment image naming convention
```

推送顺序会是：

1. 推送到 `main`
2. `release.yml` 自动生成 `CHANGELOG.md`、tag 和 GitHub Release
3. 新建的 `v*` tag 继续触发 `publish-image.yml`
4. GHCR 同时拥有 `latest` 和版本号镜像

## 开发者本地运行

### 1. 安装依赖

```bash
cd openharmony-docs-rag
pip install -r requirements.txt
cd web && npm install && cd ..
```

### 2. 同步文档

```bash
python scripts/sync_openharmony_docs.py
```

### 3. 本地启动

```bash
# 启动 Qdrant
docker run -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant

# 启动 API
python app/main.py

# 启动前端开发服务器
cd web
npm run dev
```

### 4. 本地验证

```bash
# 健康检查
curl http://localhost:8000/health

# 检索测试
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 5
  }'

# 问答测试
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 6
  }'
```

### 5. 运行评测

```bash
python scripts/eval.py
python data/eval/eval_dataset.py
```

## API 文档

### POST /query

完整问答（检索 + 生成答案）。

**请求示例**：

```json
{
  "query": "如何创建 UIAbility 组件？",
  "top_k": 6,
  "filters": {
    "top_dir": "application-dev",
    "exclude_readme": true
  }
}
```

**响应示例**：

```json
{
  "answer": "创建 UIAbility 组件的步骤如下：\n\n1. 在 DevEco Studio 中...",
  "citations": [
    {
      "path": "zh-cn/application-dev/application-models/uiability-overview.md",
      "title": "UIAbility 组件概述",
      "heading_path": "应用开发 > 应用模型 > UIAbility",
      "snippet": "UIAbility 是...",
      "source_url": "https://gitee.com/openharmony/docs/blob/master/zh-cn/..."
    }
  ],
  "trace_id": "trace-20260314-abc123",
  "latency_ms": 2345,
  "used_chunks": 6,
  "intent": {
    "type": "guide",
    "confidence": 0.89
  }
}
```

### POST /retrieve

检索相关文档块（不生成答案）。

**请求示例**：

```json
{
  "query": "如何使用 ArkUI 组件？",
  "top_k": 10,
  "filters": {
    "top_dir": "application-dev",
    "kit": "ArkUI",
    "exclude_readme": true
  }
}
```

**响应示例**：

```json
{
  "chunks": [
    {
      "chunk_id": "abc123",
      "text": "ArkUI 是...",
      "heading_path": "应用开发 > ArkUI > 组件开发",
      "score": 0.89,
      "metadata": {
        "path": "zh-cn/application-dev/ui/arkui-overview.md",
        "kit": "ArkUI",
        "page_kind": "guide",
        "is_guide": true
      }
    }
  ],
  "trace_id": "trace-20260314-abc123",
  "latency_ms": 456
}
```

### GET /health

健康检查。

**响应示例**：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "qdrant_connected": true,
  "sqlite_connected": true,
  "indexed_documents": 5299
}
```

### GET /capabilities

查询系统能力。

**响应示例**：

```json
{
  "supported_intents": ["guide", "api_usage", "design_spec", "concept", "general"],
  "supported_filters": ["top_dir", "kit", "subsystem", "page_kind", "exclude_readme"],
  "max_top_k": 50,
  "embedding_model": "Qwen/Qwen3-Embedding-4B",
  "chat_model": "kimi-k2.5"
}
```

## 核心设计

### 意图识别

系统自动识别 5 种查询意图：

1. **guide**：如何做、指南、快速入门、最佳实践
2. **api_usage**：API 使用、接口调用、方法说明
3. **design_spec**：设计规范、UX 指南、组件设计
4. **concept**：概念、定义、区别
5. **general**：通用查询

### 文档类型感知切分

- **API 参考文档**：保持接口定义完整性，一个接口一个 chunk
- **指南文档**：保持步骤连贯性，避免在步骤中间切分
- **设计规范文档**：保持规范完整性，一个规范点一个 chunk
- **README 文档**：创建较大的 chunk，降低检索权重

### 检索策略

```
Query → 意图识别 → 混合检索 → 意图增强 → 元数据过滤 → Top-K
```

- **意图增强**：根据意图类型对不同文档类型进行加权
- **元数据过滤**：支持按目录、Kit、子系统、文档类型过滤
- **排除 README**：可选择排除导航类文档

## 开发指南

### 添加新的 API 端点

1. 在 `app/api/` 下创建新的路由文件
2. 在 `app/main.py` 中注册路由
3. 在 `app/schemas.py` 中定义请求/响应模型

### 自定义切分策略

编辑 `app/core/chunker.py`，修改或添加新的切分方法。

### 调整检索参数

编辑 `.env` 文件：

```bash
CHUNK_TARGET_SIZE=600        # 目标块大小
CHUNK_OVERLAP=100            # 重叠大小
RETRIEVAL_TOP_K=8            # 默认返回数量
RERANK_ENABLED=true          # 是否启用二阶段重排
RERANK_BASE_URL=https://api.siliconflow.cn
RERANK_MODEL=Qwen/Qwen3-Reranker-4B
RERANK_TOP_K=15             # 参与重排的候选数量
HYBRID_ALPHA=0.5             # 向量检索权重
```

## 故障排查

### Qdrant 连接失败

```bash
# 检查 Qdrant 是否运行
docker ps | grep qdrant

# 查看 Qdrant 日志
docker logs openharmony-qdrant
```

### 索引构建失败

```bash
# 检查文档是否已同步
ls -la data/raw/openharmony-docs/zh-cn/

# 查看详细日志
python scripts/build_index.py 2>&1 | tee build.log
```

### API 调用失败

```bash
# 检查模型配置
grep -E '^(LLM_|EMBEDDING_|RERANK_)' .env

# 测试 embedding 生成
python -c "from app.core.embedder import Embedder; e = Embedder(); print(len(e.embed_text('test')))"
```

### 评测失败

```bash
# 确保索引已构建
curl http://localhost:8000/health

# 检查评测数据集
python data/eval/eval_dataset.py

# 运行单个问题测试
python -c "
from app.services.retriever import HybridRetriever
r = HybridRetriever()
chunks = r.retrieve('如何创建 UIAbility 组件？', top_k=5)
print(f'Retrieved {len(chunks)} chunks')
"
```

## 评测指标

评测系统会计算以下指标：

### 1. 意图识别
- **意图准确率**：预测意图与期望意图的匹配率
- **意图置信度**：意图识别的置信度分数

### 2. 检索质量
- **文档召回率**：检索结果中包含期望文档的比例
- **Top-1 分数**：最相关文档的相似度分数
- **平均分数**：所有检索文档的平均相似度

### 3. 答案质量
- **关键词召回率**：答案中包含期望关键词的比例
- **有效答案率**：生成有效答案（非"未找到"）的比例
- **引用率**：答案包含引用的比例

### 4. 整体成功率
综合考虑意图识别、文档召回、关键词召回和答案有效性的整体成功率。

## Skill 和 MCP 集成

### Skill Wrapper

现在有两种 skill 形态：

- `skill/SKILL.md`：给 agent 平台分发使用的技能说明
- `skill/rag_skill_wrapper.py`：给 Python 代码直接调用的 wrapper

Python wrapper 示例：

```python
from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://<部署地址>:8000")

# 问答
result = await skill.ask_question("如何创建 UIAbility 组件？")
print(skill.format_answer(result))

# 搜索
result = await skill.search_docs("ArkUI 组件", top_k=5)
print(skill.format_search_results(result))

# 同步仓库
result = await skill.sync_repository()

# 获取统计
result = await skill.get_stats()
```

详见 [skill/README.md](skill/README.md)

### MCP Server

真正可运行的 MCP Server 入口是 `rag_mcp.stdio_server`：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://<部署地址>:8000 \
./venv/bin/python -m rag_mcp.stdio_server
```

**可用的 MCP 工具**：
- `oh_docs_rag_query` - 完整问答
- `oh_docs_rag_retrieve` - 仅检索
- `oh_docs_rag_sync_repo` - 同步仓库
- `oh_docs_rag_stats` - 获取统计

如果你只想在 Python 里直接复用 MCP 风格工具定义，而不启动 stdio server，可以用：

```python
from rag_mcp.http_adapter import OpenHarmonyDocsRAGMCP

mcp = OpenHarmonyDocsRAGMCP(api_base_url="http://<部署地址>:8000")
tools = mcp.get_tools()
result = await mcp.call_tool("oh_docs_rag_query", {"query": "如何创建 UIAbility 组件？"})
```

详见 [mcp/README.md](mcp/README.md)

## 管理端点

### POST /sync-repo

同步 OpenHarmony 文档仓库。

```bash
curl -X POST http://localhost:8000/sync-repo
```

### POST /reindex

重建文档索引（长时间运行操作）。

```bash
curl -X POST http://localhost:8000/reindex
```

### GET /documents

列出已索引的文档（支持过滤和分页）。

```bash
# 列出所有文档
curl "http://localhost:8000/documents?limit=10&offset=0"

# 按 Kit 过滤
curl "http://localhost:8000/documents?kit=ArkUI&limit=10"

# 按目录过滤
curl "http://localhost:8000/documents?top_dir=application-dev&limit=10"
```

### GET /stats

获取系统统计信息。

```bash
curl http://localhost:8000/stats
```

**响应示例**：
```json
{
  "total_documents": 5299,
  "by_top_dir": {
    "application-dev": 5232,
    "design": 67
  },
  "by_kit": {
    "ArkUI": 1127,
    "ArkTS": 856,
    ...
  },
  "document_types": {
    "api_reference": 1234,
    "guide": 2345,
    "design_spec": 67
  }
}
```

## 路线图

- [x] Phase 1: 建库可用（文档导入和检索）
- [x] Phase 2: 问答可用（端到端问答链路）
- [x] Phase 3: 接入可复用（Skill 和 MCP 支持）
- [x] Phase 4: 文档同步（设计文档和飞书）

## 文档

### 本地文档
- [完整实施计划](docs/openharmony_docs_rag_implementation_plan.md)
- [架构图和流程图](docs/architecture_diagrams.md)
- [Phase 1 总结](docs/PHASE1_SUMMARY.md)
- [Phase 2 总结](docs/PHASE2_SUMMARY.md)
- [Phase 3 总结](docs/PHASE3_SUMMARY.md)
- [快速参考](docs/QUICK_REFERENCE.md)
- [实施报告](docs/IMPLEMENTATION_REPORT.md)

### 飞书文档
- [完整实施计划（飞书）](https://feishu.cn/docx/Il8Jd5smKofKPHxqSdEcOwb2nLb)
- [架构图和流程图（飞书）](https://feishu.cn/docx/C2DpdbULvoeT5vxb9BXcvGMmnoh)

## 许可证

MIT

## 参考

- [OpenHarmony 文档仓库](https://gitee.com/openharmony/docs)
- [设计文档](../docs/openharmony_docs_rag_system_design.md)
