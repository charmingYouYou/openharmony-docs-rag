---
name: openharmony-docs-rag
description: 当用户询问 OpenHarmony 官方开发文档、API 用法、设计规范或最佳实践，并且需要基于本地 RAG 服务给出带引用的答案时使用。
allowed-tools: Bash(curl)
---

# OpenHarmony 文档问答 Skill

使用本地 OpenHarmony 文档 RAG API 回答问题，不要凭记忆补全答案。

## 适用场景

- OpenHarmony 开发文档问答
- API 用法、参数和返回值说明
- 设计规范、概念解释和最佳实践
- 需要基于官方文档返回带引用的结论

## 配置

- 默认 API 地址建议为 `http://127.0.0.1:8000`
- 可通过环境变量 `OPENHARMONY_RAG_API_BASE_URL` 覆盖

## 唯一调用方式

始终只调用 `/query`。

```bash
curl -s "${OPENHARMONY_RAG_API_BASE_URL:-http://127.0.0.1:8000}/query" \
  -H "Content-Type: application/json" \
  -H "X-Caller-Type: skill" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 6
  }'
```

如果需要限定目录或 Kit，继续通过同一个 `/query` 请求传 `filters`：

```bash
curl -s "${OPENHARMONY_RAG_API_BASE_URL:-http://127.0.0.1:8000}/query" \
  -H "Content-Type: application/json" \
  -H "X-Caller-Type: skill" \
  -d '{
    "query": "router.pushUrl 方法如何使用？",
    "top_k": 6,
    "filters": {
      "kit": "Ability Kit",
      "top_dir": "application-dev"
    }
  }'
```

## 工作规则

- 只能调用 `/query`，不要调用其他接口
- 优先使用接口返回的 `answer` 和 `citations`
- 如果返回内容表明未找到相关信息，或者没有可用引用，不要自行补充未经检索验证的细节
- 不要编造 OpenHarmony API、参数、版本行为或设计规范
- 如果接口调用失败，明确告诉用户当前无法从文档服务确认答案
