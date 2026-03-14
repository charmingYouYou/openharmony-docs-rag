"""
OpenHarmony 文档 RAG 系统评测数据集

包含 5 种问题类型：
1. 导航类（Navigation）- 查找文档位置
2. 指南类（Guide）- 如何做某事
3. API 使用类（API Usage）- API 接口使用
4. 设计规范类（Design Spec）- 设计规范和 UX 指南
5. 概念类（Concept）- 概念解释和对比

每个问题包含：
- question: 问题文本
- type: 问题类型
- expected_intent: 期望的意图识别结果
- expected_docs: 期望出现的文档路径关键词
- expected_keywords: 期望答案中包含的关键词
"""

EVAL_DATASET = [
    # ========== 指南类问题（Guide）==========
    {
        "question": "如何创建一个 UIAbility 组件？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["uiability", "application-dev"],
        "expected_keywords": ["UIAbility", "创建", "步骤", "生命周期"]
    },
    {
        "question": "如何使用 ArkTS 开发一个简单的页面？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["arkts", "quick-start", "application-dev"],
        "expected_keywords": ["ArkTS", "页面", "组件", "@Entry"]
    },
    {
        "question": "如何实现应用间的数据共享？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["data-share", "application-dev"],
        "expected_keywords": ["数据共享", "DataShare", "Provider"]
    },
    {
        "question": "如何使用 Preferences 存储数据？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["preferences", "application-dev"],
        "expected_keywords": ["Preferences", "存储", "键值对"]
    },
    {
        "question": "如何实现页面路由跳转？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["router", "arkui", "application-dev"],
        "expected_keywords": ["路由", "跳转", "router", "页面"]
    },
    {
        "question": "如何使用 HTTP 请求网络数据？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["http", "network", "application-dev"],
        "expected_keywords": ["HTTP", "网络", "请求", "request"]
    },
    {
        "question": "如何实现应用的国际化？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["i18n", "internationalization", "application-dev"],
        "expected_keywords": ["国际化", "多语言", "资源"]
    },
    {
        "question": "如何使用通知功能？",
        "type": "guide",
        "expected_intent": "guide",
        "expected_docs": ["notification", "application-dev"],
        "expected_keywords": ["通知", "Notification", "发送"]
    },

    # ========== API 使用类问题（API Usage）==========
    {
        "question": "UIAbility 的 onCreate 方法有哪些参数？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["uiability", "reference", "api"],
        "expected_keywords": ["onCreate", "参数", "want", "launchParam"]
    },
    {
        "question": "router.pushUrl 方法如何使用？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["router", "reference", "api"],
        "expected_keywords": ["pushUrl", "url", "params", "跳转"]
    },
    {
        "question": "Preferences.put 方法的参数类型是什么？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["preferences", "reference", "api"],
        "expected_keywords": ["put", "key", "value", "参数"]
    },
    {
        "question": "http.request 方法返回什么类型？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["http", "reference", "api"],
        "expected_keywords": ["request", "返回", "Promise", "HttpResponse"]
    },
    {
        "question": "@State 装饰器如何使用？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["state", "arkui", "reference"],
        "expected_keywords": ["@State", "状态", "装饰器", "变量"]
    },
    {
        "question": "Text 组件有哪些属性？",
        "type": "api_usage",
        "expected_intent": "api_usage",
        "expected_docs": ["text", "arkui", "reference"],
        "expected_keywords": ["Text", "属性", "fontSize", "fontColor"]
    },

    # ========== 设计规范类问题（Design Spec）==========
    {
        "question": "ArkUI 组件的设计规范是什么？",
        "type": "design_spec",
        "expected_intent": "design_spec",
        "expected_docs": ["design", "arkui"],
        "expected_keywords": ["设计规范", "组件", "ArkUI"]
    },
    {
        "question": "OpenHarmony 的 UX 设计原则有哪些？",
        "type": "design_spec",
        "expected_intent": "design_spec",
        "expected_docs": ["design", "ux"],
        "expected_keywords": ["UX", "设计原则", "用户体验"]
    },
    {
        "question": "按钮组件的设计规范是什么？",
        "type": "design_spec",
        "expected_intent": "design_spec",
        "expected_docs": ["design", "button"],
        "expected_keywords": ["按钮", "设计", "规范"]
    },

    # ========== 概念类问题（Concept）==========
    {
        "question": "什么是 UIAbility？",
        "type": "concept",
        "expected_intent": "concept",
        "expected_docs": ["uiability", "application-dev"],
        "expected_keywords": ["UIAbility", "组件", "应用", "生命周期"]
    },
    {
        "question": "ArkTS 和 TypeScript 有什么区别？",
        "type": "concept",
        "expected_intent": "concept",
        "expected_docs": ["arkts", "application-dev"],
        "expected_keywords": ["ArkTS", "TypeScript", "区别", "扩展"]
    },
    {
        "question": "什么是 Stage 模型？",
        "type": "concept",
        "expected_intent": "concept",
        "expected_docs": ["stage", "application-dev"],
        "expected_keywords": ["Stage", "模型", "应用模型"]
    },
    {
        "question": "什么是 DataAbility？",
        "type": "concept",
        "expected_intent": "concept",
        "expected_docs": ["dataability", "application-dev"],
        "expected_keywords": ["DataAbility", "数据", "共享"]
    },
    {
        "question": "什么是 Want？",
        "type": "concept",
        "expected_intent": "concept",
        "expected_docs": ["want", "application-dev"],
        "expected_keywords": ["Want", "意图", "信息载体"]
    },

    # ========== 导航类问题（Navigation）==========
    {
        "question": "在哪里可以找到 ArkUI 的开发文档？",
        "type": "navigation",
        "expected_intent": "general",
        "expected_docs": ["arkui", "application-dev"],
        "expected_keywords": ["ArkUI", "文档", "开发"]
    },
    {
        "question": "OpenHarmony 有哪些 Kit？",
        "type": "navigation",
        "expected_intent": "general",
        "expected_docs": ["application-dev"],
        "expected_keywords": ["Kit", "ArkUI", "ArkTS"]
    },

    # ========== 边界情况（Out of Scope）==========
    {
        "question": "如何在 Android 上开发应用？",
        "type": "out_of_scope",
        "expected_intent": "general",
        "expected_docs": [],
        "expected_keywords": ["没有找到", "相关信息", "OpenHarmony"]
    },
    {
        "question": "Python 如何读取文件？",
        "type": "out_of_scope",
        "expected_intent": "general",
        "expected_docs": [],
        "expected_keywords": ["没有找到", "相关信息"]
    },
]


def get_dataset_by_type(question_type: str):
    """Get questions by type."""
    return [q for q in EVAL_DATASET if q["type"] == question_type]


def get_dataset_stats():
    """Get dataset statistics."""
    from collections import Counter
    type_counts = Counter(q["type"] for q in EVAL_DATASET)
    return {
        "total": len(EVAL_DATASET),
        "by_type": dict(type_counts)
    }


if __name__ == "__main__":
    stats = get_dataset_stats()
    print("评测数据集统计：")
    print(f"总问题数: {stats['total']}")
    print("\n各类型问题数：")
    for qtype, count in stats['by_type'].items():
        print(f"  {qtype}: {count}")
