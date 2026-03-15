# Build and run the OpenHarmony Docs RAG single-entry deployment image.
FROM node:22-alpine AS web-build

WORKDIR /web

# Install frontend dependencies and build the production web bundle.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# Install git for repository cloning during sync/build workflows.
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install backend dependencies.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy runtime sources required by the API, skill, MCP adapter, and deployment scripts.
COPY app ./app
COPY deploy ./deploy
COPY rag_mcp ./rag_mcp
COPY scripts ./scripts
COPY skill ./skill
COPY mcp ./mcp
COPY .env.example ./.env.example
COPY README.md ./README.md

# Copy the built web bundle into the path served by the FastAPI app.
COPY --from=web-build /web/dist ./web/dist

# Expose the single external entrypoint.
EXPOSE 8000

# Run the combined API and built web console.
CMD ["sh", "-c", "uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}"]
