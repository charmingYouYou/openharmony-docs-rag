# OpenHarmony Docs RAG Web

这个目录存放 Web 控制台的前端源码，技术栈为 `React 19 + Vite + shadcn/ui`。

## 开发用途

```bash
cd web
npm install
npm run dev
```

默认开发态 API 地址来自 `VITE_API_BASE_URL`；未显式配置时会自动使用当前页面同源地址。

## 生产部署

正式部署不直接运行 Vite。根目录 `Dockerfile` 会在镜像构建阶段完成前端打包，并由 FastAPI 在运行时托管构建后的静态资源。

对外交付和部署步骤请以根目录 [README.md](/Volumes/PM9A1/code/codex/openharmony-docs-rag/README.md) 为准。
