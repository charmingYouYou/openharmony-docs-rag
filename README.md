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

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd openharmony-docs-rag

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，只填核心模型配置即可
```

### 2. 同步文档

```bash
# 克隆 OpenHarmony 文档仓库
python scripts/sync_openharmony_docs.py
```

### 3. 配置模型环境变量

现在默认只需要填这 9 个核心变量：

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
- `EMBEDDING_QUERY_PREFIX` 仍然保留在 env 中，便于按模型调整检索 instruction
- 其余 batch、重试、chunk 大小等都放到“可选高级配置”，不填就走默认值

当前默认示例使用 SiliconFlow 的 `Qwen/Qwen3-Embedding-4B` 和 `Qwen/Qwen3-Reranker-4B`；其中 `EMBEDDING_QUERY_PREFIX` 支持从环境变量注入检索前缀，`\n` 会在运行时转换成真实换行。

```bash
grep -E '^(LLM_|EMBEDDING_|RERANK_)' .env
```

### 4. 构建索引

```bash
# 默认增量构建：只为新增、变更、失败过的文档重建索引
python scripts/build_index.py

# 显式全量重建：清空 SQLite/Qdrant 后重新构建全部索引
python scripts/build_index.py --full-rebuild
```

这个过程会：
- 解析约 5299 个 Markdown 文件（application-dev + design 目录）
- 生成约 30000+ 个文档块
- 为每个块生成 embedding
- 存储到 Qdrant 和 SQLite

默认模式下，构建器会把每个文档的 `content_hash` 和当前索引签名持久化到 SQLite。未变更且已成功入库的文档会直接跳过，因此中断后重跑不会重复消耗已经完成文档的 embedding token。

失败文档会标记为 `failed` 并记录 `last_error`；下次执行 `python scripts/build_index.py` 时只会重试这些失败文档，而不是从头清空再来。

**预计耗时**：取决于 embeddings 服务吞吐、文档规模以及本次实际变更的文档数量

### 5. 启动服务

#### 方式 1：本地运行

```bash
# 启动 Qdrant（需要 Docker）
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant

# 启动 API 服务
python app/main.py
```

#### 方式 2：Docker Compose

```bash
docker-compose up -d
```

### 6. 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 检索测试（仅检索，不生成答案）
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 5
  }'

# 问答测试（完整 RAG，生成答案）
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 6
  }'
```

### 7. 运行评测

```bash
# 运行完整评测（需要先构建索引）
python scripts/eval.py

# 查看评测数据集统计
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

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://127.0.0.1:8000")

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
OPENHARMONY_RAG_API_BASE_URL=http://127.0.0.1:8000 \
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

mcp = OpenHarmonyDocsRAGMCP(api_base_url="http://127.0.0.1:8000")
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
