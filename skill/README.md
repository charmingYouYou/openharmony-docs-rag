# OpenHarmony Docs RAG Skill

这个目录交付的是一个面向 Codex / Claude 风格 agent 的本地 skill。

它的目标很单一：当用户询问 OpenHarmony 官方文档相关问题时，统一通过本地 RAG 服务的 `/query` 接口获取带引用的答案。

## 适用范围

- OpenHarmony 开发文档问答
- API 用法说明
- 设计规范与概念解释
- 最佳实践与官方路径引用

## 接入方式

将 [skill/SKILL.md](/Volumes/PM9A1/code/codex/openharmony-docs-rag/skill/SKILL.md) 分发为本地 skill，并配置：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://<部署地址>:8000
```

## 调用约束

- 只能调用 `/query`
- 不调用 `/retrieve`
- 不调用 `/health`
- 不调用 `/stats`
- 回答必须以接口返回的 `answer` 和 `citations` 为准

## 请求示例

```bash
curl -s "${OPENHARMONY_RAG_API_BASE_URL:-http://127.0.0.1:8000}/query" \
  -H "Content-Type: application/json" \
  -H "X-Caller-Type: skill" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 6
  }'
```

## 使用原则

- 需要范围约束时，在 `/query` 的 `filters` 中传递条件
- 有引用就基于引用回答
- 没有引用或接口明确表示未找到相关信息时，直接说明当前无法从文档服务确认
- 不要凭模型记忆补全文档中不存在的 API 细节
