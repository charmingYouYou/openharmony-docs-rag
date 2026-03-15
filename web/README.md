# OpenHarmony Docs RAG Web

这个目录存放 Web 控制台的前端源码，技术栈为 `React 19 + Vite + shadcn/ui`。

正式交付不直接运行 Vite。根目录 `Dockerfile` 会在镜像构建阶段完成前端打包，并由 FastAPI 在运行时托管构建后的静态资源。

实际部署方式、运行时配置入口和运维命令请以根目录 [README.md](/Volumes/PM9A1/code/codex/openharmony-docs-rag/README.md) 为准。
