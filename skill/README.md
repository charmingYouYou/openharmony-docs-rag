# OpenHarmony Docs RAG - Skill

这个目录现在同时包含两种形态：

- `SKILL.md`：给 agent 平台分发使用的技能说明
- `rag_skill_wrapper.py`：给 Python 代码直接调用的异步 wrapper

## 1. Agent Skill

如果你要把它作为 Codex / Claude 风格的本地 skill 使用，直接分发 [skill/SKILL.md](/Volumes/PM9A1/code/codex/openharmony-docs-rag/skill/SKILL.md) 即可。

技能默认访问：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://localhost:8000
```

## 2. Python Wrapper

```python
from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://127.0.0.1:8000")

result = await skill.ask_question("如何创建 UIAbility 组件？")
print(skill.format_answer(result))

chunks = await skill.search_docs("router.pushUrl 方法如何使用？", top_k=5)
print(skill.format_search_results(chunks))
```

## 3. Environment Variable

如果不在构造函数里传 `api_base_url`，wrapper 会读取：

```bash
OPENHARMONY_RAG_API_BASE_URL=http://127.0.0.1:8000
```

## 4. Available Actions

- `ask_question`
- `search_docs`
- `sync_repository`
- `get_stats`

## Notes

- 所有请求都会带 `X-Caller-Type: skill`
- `ask_question` 调用 `/query`
- `search_docs` 调用 `/retrieve`
- 具体技能说明和 `curl` 用法见 `SKILL.md`
