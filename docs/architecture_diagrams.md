# OpenHarmony 文档 RAG 系统 - 架构图和流程图

## 系统架构图

```mermaid
graph TB
    subgraph "入口层"
        UI[Web UI]
        Skill[Skill Wrapper]
        MCP[MCP Server]
    end

    subgraph "API 层 - FastAPI"
        API[API 端点]
        Query[/query]
        Retrieve[/retrieve]
        Health[/health]
        SyncRepo[/sync-repo]
        Stats[/stats]

        API --> Query
        API --> Retrieve
        API --> Health
        API --> SyncRepo
        API --> Stats
    end

    subgraph "服务层"
        QP[Query Preprocessor<br/>意图识别]
        Retriever[Hybrid Retriever<br/>混合检索]
        AnswerService[Answer Service<br/>答案生成]
    end

    subgraph "核心层"
        Parser[Parser<br/>文档解析]
        Chunker[Chunker<br/>文档切分]
        Embedder[Embedder<br/>向量生成]
    end

    subgraph "存储层"
        Qdrant[(Qdrant<br/>向量存储<br/>30000+ chunks)]
        SQLite[(SQLite<br/>元数据存储<br/>5299 docs)]
    end

    subgraph "外部服务"
        OpenAI[OpenAI API<br/>Embedding + LLM]
        GitRepo[OpenHarmony Docs<br/>Gitee Repository]
    end

    UI --> API
    Skill --> API
    MCP --> API

    Query --> QP
    Query --> Retriever
    Query --> AnswerService

    Retrieve --> QP
    Retrieve --> Retriever

    QP --> Retriever
    Retriever --> AnswerService

    Retriever --> Qdrant
    Retriever --> SQLite

    AnswerService --> OpenAI

    SyncRepo --> GitRepo

    Parser --> Chunker
    Chunker --> Embedder
    Embedder --> OpenAI
    Embedder --> Qdrant
    Embedder --> SQLite

    style UI fill:#e1f5ff
    style Skill fill:#e1f5ff
    style MCP fill:#e1f5ff
    style API fill:#fff4e1
    style Qdrant fill:#f0f0f0
    style SQLite fill:#f0f0f0
    style OpenAI fill:#ffe1e1
```

## 离线建库流程图

```mermaid
flowchart TD
    Start([开始建库]) --> Clone[克隆/更新<br/>OpenHarmony Docs]
    Clone --> Scan[扫描 Markdown 文件<br/>application-dev + design]

    Scan --> Parse[Parser 解析文档]
    Parse --> ExtractMeta[提取元数据<br/>Kit, Subsystem, Owner]
    ExtractMeta --> IdentifyType[识别文档类型<br/>API/Guide/Design]

    IdentifyType --> Chunk[Chunker 切分文档]
    Chunk --> ChunkAPI{文档类型?}

    ChunkAPI -->|API 参考| ChunkAPILogic[保持接口<br/>定义完整性]
    ChunkAPI -->|开发指南| ChunkGuideLogic[保持步骤<br/>连贯性]
    ChunkAPI -->|设计规范| ChunkDesignLogic[保持规范<br/>完整性]
    ChunkAPI -->|其他| ChunkGeneric[通用切分]

    ChunkAPILogic --> Embed[Embedder 生成向量]
    ChunkGuideLogic --> Embed
    ChunkDesignLogic --> Embed
    ChunkGeneric --> Embed

    Embed --> CallOpenAI[调用 OpenAI API<br/>text-embedding-v3]
    CallOpenAI --> GetVector[获取 1024 维向量]

    GetVector --> SaveQdrant[保存到 Qdrant<br/>向量 + payload]
    GetVector --> SaveSQLite[保存到 SQLite<br/>文档元数据]

    SaveQdrant --> CheckMore{还有文档?}
    SaveSQLite --> CheckMore

    CheckMore -->|是| Parse
    CheckMore -->|否| Summary[生成统计报告]

    Summary --> End([建库完成<br/>~30000 chunks])

    style Start fill:#e1f5ff
    style End fill:#e1ffe1
    style CallOpenAI fill:#ffe1e1
    style SaveQdrant fill:#f0f0f0
    style SaveSQLite fill:#f0f0f0
```

## 在线问答流程图

```mermaid
flowchart TD
    Start([用户提问]) --> Preprocess[Query Preprocessor<br/>查询预处理]

    Preprocess --> Normalize[规范化查询<br/>空格/大小写]
    Normalize --> Intent[识别意图]

    Intent --> IntentType{意图类型?}
    IntentType -->|guide| IntentGuide[指南意图<br/>如何做/步骤]
    IntentType -->|api_usage| IntentAPI[API 使用意图<br/>接口/参数]
    IntentType -->|design_spec| IntentDesign[设计规范意图<br/>UX/组件设计]
    IntentType -->|concept| IntentConcept[概念意图<br/>定义/区别]
    IntentType -->|general| IntentGeneral[通用意图]

    IntentGuide --> GenEmbed[生成查询向量]
    IntentAPI --> GenEmbed
    IntentDesign --> GenEmbed
    IntentConcept --> GenEmbed
    IntentGeneral --> GenEmbed

    GenEmbed --> VectorSearch[向量检索<br/>Qdrant Top-30]
    VectorSearch --> IntentBoost[意图增强<br/>boost/penalize]

    IntentBoost --> BoostLogic{意图类型?}
    BoostLogic -->|guide| BoostGuide[boost guide 文档 1.3x<br/>降低 readme 0.7x]
    BoostLogic -->|api_usage| BoostAPI[boost API 文档 1.3x]
    BoostLogic -->|design_spec| BoostDesign[boost design 文档 1.3x]
    BoostLogic -->|其他| BoostNone[不调整]

    BoostGuide --> MetaFilter[元数据过滤]
    BoostAPI --> MetaFilter
    BoostDesign --> MetaFilter
    BoostNone --> MetaFilter

    MetaFilter --> TopK[选择 Top-K<br/>默认 6-8 个]
    TopK --> CheckRelevance{相关性检查}

    CheckRelevance -->|相关| BuildContext[构建上下文<br/>从 chunks]
    CheckRelevance -->|不相关| ReturnNoResult[返回友好提示<br/>未找到相关信息]

    BuildContext --> DynamicPrompt[动态 Prompt<br/>根据意图调整]
    DynamicPrompt --> CallLLM[调用 LLM<br/>kimi-k2.5]
    CallLLM --> GenAnswer[生成答案]

    GenAnswer --> BuildCitation[构建引用<br/>文档路径/片段]
    BuildCitation --> ReturnAnswer[返回结果<br/>答案+引用+意图]

    ReturnNoResult --> End([返回用户])
    ReturnAnswer --> End

    style Start fill:#e1f5ff
    style End fill:#e1ffe1
    style CallLLM fill:#ffe1e1
    style VectorSearch fill:#f0f0f0
    style CheckRelevance fill:#fff4e1
```

## 意图识别流程图

```mermaid
flowchart TD
    Start([查询文本]) --> Normalize[规范化<br/>空格/大小写]

    Normalize --> CheckGuide{匹配指南模式?<br/>如何/怎么/步骤}
    CheckGuide -->|是| GuideScore[guide_score++]
    CheckGuide -->|否| CheckAPI

    GuideScore --> CheckAPI{匹配 API 模式?<br/>API/接口/方法}
    CheckAPI -->|是| APIScore[api_score++]
    CheckAPI -->|否| CheckDesign

    APIScore --> CheckDesign{匹配设计模式?<br/>设计规范/UX}
    CheckDesign -->|是| DesignScore[design_score++]
    CheckDesign -->|否| CheckConcept

    DesignScore --> CheckConcept{匹配概念模式?<br/>是什么/定义}
    CheckConcept -->|是| ConceptScore[concept_score++]
    CheckConcept -->|否| CalcMax

    ConceptScore --> CalcMax[计算最高分数]

    CalcMax --> HasScore{有匹配分数?}
    HasScore -->|否| ReturnGeneral[返回 general 意图<br/>置信度 0.5]
    HasScore -->|是| FindMax[找到最高分意图]

    FindMax --> CalcConfidence[计算置信度<br/>min分数/3, 1.0]
    CalcConfidence --> ExtractFilters[提取过滤条件<br/>Kit/目录]

    ExtractFilters --> ReturnIntent[返回意图+置信度+过滤器]

    ReturnGeneral --> End([返回结果])
    ReturnIntent --> End

    style Start fill:#e1f5ff
    style End fill:#e1ffe1
    style HasScore fill:#fff4e1
```

## 文档类型感知切分流程图

```mermaid
flowchart TD
    Start([文档内容]) --> IdentifyType{识别文档类型}

    IdentifyType -->|is_api_reference| APIChunk[API 参考切分]
    IdentifyType -->|is_guide| GuideChunk[指南切分]
    IdentifyType -->|is_design_spec| DesignChunk[设计规范切分]
    IdentifyType -->|page_kind=readme| ReadmeChunk[README 切分]
    IdentifyType -->|其他| GenericChunk[通用切分]

    APIChunk --> APISplit[按 H2/H3 切分<br/>保持接口完整]
    APISplit --> APICheck{长度检查}
    APICheck -->|过长| APISplitCode[按代码块拆分]
    APICheck -->|合适| APICreate[创建 chunk]
    APISplitCode --> APICreate

    GuideChunk --> GuideSplit[按 H2 切分]
    GuideSplit --> GuideSteps{包含步骤?}
    GuideSteps -->|是| GuideKeepSteps[保持步骤连贯<br/>不在中间切分]
    GuideSteps -->|否| GuideOverlap[常规重叠切分]
    GuideKeepSteps --> GuideCreate[创建 chunk]
    GuideOverlap --> GuideCreate

    DesignChunk --> DesignSplit[按 H2/H3 切分<br/>保持规范完整]
    DesignSplit --> DesignCheck{长度检查}
    DesignCheck -->|过长| DesignOverlap[重叠切分]
    DesignCheck -->|合适| DesignCreate[创建 chunk]
    DesignOverlap --> DesignCreate

    ReadmeChunk --> ReadmeSplit[按 H2 切分<br/>较大 chunk]
    ReadmeSplit --> ReadmeCreate[创建 chunk<br/>标记 page_kind=readme]

    GenericChunk --> GenericSplit[按 H2/H3 切分]
    GenericSplit --> GenericOverlap[重叠切分<br/>600 字符/100 重叠]
    GenericOverlap --> GenericCreate[创建 chunk]

    APICreate --> AddMeta[添加元数据<br/>path/kit/page_kind]
    GuideCreate --> AddMeta
    DesignCreate --> AddMeta
    ReadmeCreate --> AddMeta
    GenericCreate --> AddMeta

    AddMeta --> End([返回 chunks])

    style Start fill:#e1f5ff
    style End fill:#e1ffe1
    style IdentifyType fill:#fff4e1
```
