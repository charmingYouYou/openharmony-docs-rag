# OpenHarmony Docs RAG - Quick Reference

## 项目位置

```
/Volumes/PM9A1/code/codex/openharmony-docs-rag/
```

## 核心命令

### 开发环境设置

```bash
# 进入项目目录
cd /Volumes/PM9A1/code/codex/openharmony-docs-rag

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 OPENAI_API_KEY
```

### 数据准备

```bash
# 同步 OpenHarmony 文档仓库
python scripts/sync_openharmony_docs.py

# 构建索引（需要 OpenAI API Key）
python scripts/build_index.py
```

### 启动服务

```bash
# 方式 1：使用 Docker Compose（推荐）
docker-compose up -d

# 方式 2：手动启动
# 启动 Qdrant
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name openharmony-qdrant \
  qdrant/qdrant

# 启动 API 服务
python app/main.py
```

### 测试

```bash
# 运行基础测试
python tests/test_basic.py

# 健康检查
curl http://localhost:8000/health

# 测试检索
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 5
  }'
```

## 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| Parser | `app/core/parser.py` | Markdown 解析、元数据提取、文档类型识别 |
| Chunker | `app/core/chunker.py` | 文档切分（heading-aware + 类型感知） |
| Embedder | `app/core/embedder.py` | Embedding 生成（OpenAI） |
| Retriever | `app/services/retriever.py` | 混合检索 + 意图增强 |
| Query Preprocessor | `app/utils/query_preprocessor.py` | 查询预处理 + 意图识别 |
| Qdrant Client | `app/storage/qdrant_client.py` | 向量存储 |
| SQLite Client | `app/storage/sqlite_client.py` | 元数据存储 |

## API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/retrieve` | POST | 检索相关文档块 |
| `/health` | GET | 健康检查 |
| `/capabilities` | GET | 系统能力查询 |

## 配置项（.env）

```bash
# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_EMBEDDING_MODEL=text-embedding-v3
OPENAI_CHAT_MODEL=kimi-k2.5

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=openharmony-docs-zh-cn

# SQLite
SQLITE_DB_PATH=./storage/metadata.db

# 文档仓库
DOCS_REPO_URL=https://gitee.com/openharmony/docs.git
DOCS_BRANCH=master
DOCS_INCLUDE_DIRS=zh-cn/application-dev,zh-cn/design

# Chunking
CHUNK_TARGET_SIZE=600
CHUNK_OVERLAP=100

# Retrieval
RETRIEVAL_TOP_K=8
```

## 意图类型

| 意图 | 触发词 | 检索策略 |
|------|--------|----------|
| `guide` | 如何、指南、快速入门、最佳实践 | boost guide 文档，降低 readme |
| `api_usage` | API、接口、方法、参数 | boost API reference 文档 |
| `design_spec` | 设计规范、UX 指南、组件设计 | boost design 目录文档 |
| `concept` | 概念、定义、介绍、区别 | boost concept 文档 |
| `general` | 其他 | 通用检索 |

## 文档类型

| 类型 | 标识 | 切分策略 |
|------|------|----------|
| API Reference | `is_api_reference=true` | 保持接口定义完整性 |
| Guide | `is_guide=true` | 保持步骤连贯性 |
| Design Spec | `is_design_spec=true` | 保持规范完整性 |
| README | `page_kind=readme` | 较大 chunk，降低权重 |

## 常见问题

### Q: 如何更新文档索引？

```bash
# 1. 同步最新文档
python scripts/sync_openharmony_docs.py

# 2. 重建索引
python scripts/build_index.py
```

### Q: 如何调整 chunk 大小？

编辑 `.env` 文件：
```bash
CHUNK_TARGET_SIZE=800  # 增大到 800 字符
CHUNK_OVERLAP=150      # 增大重叠到 150 字符
```

### Q: 如何查看索引状态？

```bash
# 查看 Qdrant 点数
curl http://localhost:6333/collections/openharmony-docs-zh-cn

# 查看 SQLite 文档数
sqlite3 storage/metadata.db "SELECT COUNT(*) FROM documents;"
```

### Q: 如何添加新的意图类型？

1. 在 `app/schemas.py` 中添加新的 `QueryIntent` 枚举值
2. 在 `app/utils/query_preprocessor.py` 中添加新的模式匹配规则
3. 在 `app/services/retriever.py` 中添加新的 boost 逻辑

## 性能指标

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| 文档数 | ~5299 | 待测试 |
| Chunk 数 | ~30000 | 待测试 |
| 检索延迟 | < 500ms | 待测试 |
| 索引构建时间 | 30-60 分钟 | 待测试 |

## 下一步

- [ ] Phase 2: 实现完整问答功能
- [ ] Phase 3: 实现 Skill 和 MCP 接入
- [ ] Phase 4: 同步设计文档到飞书

## 相关文档

- [README.md](../README.md) - 项目文档
- [PHASE1_SUMMARY.md](./PHASE1_SUMMARY.md) - Phase 1 实施总结
- [openharmony_docs_rag_system_design.md](../../docs/openharmony_docs_rag_system_design.md) - 系统设计文档
