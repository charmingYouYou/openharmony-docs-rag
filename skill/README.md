# OpenHarmony Docs RAG - Skill Wrapper

Skill wrapper for OpenHarmony Chinese documentation RAG system.

## Available Actions

### 1. search_docs

Search OpenHarmony documentation and retrieve relevant chunks.

**Parameters:**
- `query` (required): Search query
- `top_k` (optional): Number of results to return (default: 10)
- `filters` (optional): Filter conditions

**Example:**
```python
result = await skill.search_docs(
    query="ArkUI 组件",
    top_k=5,
    filters={"kit": "ArkUI"}
)
```

### 2. ask_question

Ask a question about OpenHarmony documentation and get an answer with citations.

**Parameters:**
- `query` (required): Question to ask
- `top_k` (optional): Number of documents to retrieve (default: 6)
- `filters` (optional): Filter conditions

**Example:**
```python
result = await skill.ask_question(
    query="如何创建 UIAbility 组件？",
    top_k=6
)
```

### 3. sync_repository

Sync OpenHarmony documentation repository to get the latest updates.

**Example:**
```python
result = await skill.sync_repository()
```

### 4. get_stats

Get statistics about the indexed OpenHarmony documentation.

**Example:**
```python
result = await skill.get_stats()
```

## Setup

### 1. Start the RAG API

```bash
cd openharmony-docs-rag
python app/main.py
```

### 2. Use the Skill

```python
from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://localhost:8000")

# Ask a question
result = await skill.ask_question("如何创建 UIAbility 组件？")
print(skill.format_answer(result))

# Search documents
result = await skill.search_docs("ArkUI 组件", top_k=5)
print(skill.format_search_results(result))
```

## Helper Methods

### format_answer

Format answer result for display.

```python
formatted = skill.format_answer(result)
```

### format_search_results

Format search results for display.

```python
formatted = skill.format_search_results(result)
```

## Configuration

The skill connects to the RAG API at `http://localhost:8000` by default.

To use a different URL:

```python
skill = OpenHarmonyDocsRAGSkill(api_base_url="http://your-api-url:8000")
```

## Notes

- All requests include `X-Caller-Type: skill` header for tracking
- Question answering has 60s timeout (for LLM generation)
- Search has 30s timeout
- Repository sync has 300s timeout (5 minutes)

## Example Output

### Question Answer

```
创建 UIAbility 组件的步骤如下：

1. 在 DevEco Studio 中创建项目
2. 定义 UIAbility 类
3. 配置 module.json5
4. 实现生命周期回调

**参考文档：**
1. [UIAbility 组件概述](https://gitee.com/openharmony/docs/blob/master/zh-cn/...)
   路径: zh-cn/application-dev/application-models/uiability-overview.md
2. [UIAbility 组件生命周期](https://gitee.com/openharmony/docs/blob/master/zh-cn/...)
   路径: zh-cn/application-dev/application-models/uiability-lifecycle.md

*意图: guide (置信度: 0.89)*
```

### Search Results

```
找到 5 个相关文档片段：

**1. ArkUI 组件开发指南**
路径: zh-cn/application-dev/ui/arkui-overview.md
标题路径: 应用开发 > UI 开发 > ArkUI 概述
相关度: 0.92
内容: ArkUI 是一套构建分布式应用界面的声明式 UI 开发框架...

**2. ArkUI 组件参考**
路径: zh-cn/application-dev/reference/arkui-ts/ts-components-summary.md
标题路径: 应用开发 > API 参考 > ArkUI 组件
相关度: 0.88
内容: ArkUI 提供了丰富的组件库，包括基础组件、容器组件...
```
