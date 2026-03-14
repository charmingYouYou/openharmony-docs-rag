# Voyage Embedding Switch Design

## Goal

Replace the current DashScope `text-embedding-async-v2` pipeline with a Voyage-based embedding pipeline, and move all model-related configuration into environment variables so application code no longer carries provider-specific defaults.

## Scope

- Switch document and query embeddings to a synchronous Voyage embeddings API flow.
- Keep answer generation on its current chat client path, but remove hardcoded model/base-url defaults from code.
- Remove async-v2-only file hosting, task polling, and public batch input plumbing from the active embedding path.
- Update health/capabilities surfaces, tests, and quickstart docs to reflect env-driven model settings.

## Design

### Configuration

Model configuration is split into generic chat settings and generic embedding settings, all loaded from `.env`:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_CHAT_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`
- `EMBEDDING_DOCUMENT_INPUT_TYPE`
- `EMBEDDING_QUERY_INPUT_TYPE`

No provider or model default values remain in `app/settings.py`. Code only consumes environment-backed settings.

### Embedding Flow

`app/core/embedder.py` will call the configured embeddings endpoint synchronously with Voyage-compatible request bodies:

- document indexing uses `input_type=document`
- retrieval/query embedding uses `input_type=query`

The embedder will normalize the configured base URL to the embeddings endpoint and parse the returned `data[].embedding` list in order.

### Storage

Qdrant collection size must match the returned vector length. Initialization continues to derive vector size from the first embedding instead of storing a provider-specific constant in code.

### Cleanup

The previous async-v2-specific helpers and public static mount are removed from the active runtime path. Tests and docs are rewritten around the Voyage flow.

## Risk

The provided local base URL (`http://127.0.0.1:23333`) currently identifies itself as Cherry Studio API and exposes `GET /v1/models`, but local probing returned `404 Cannot POST /v1/embeddings`. The code will be updated to the official Voyage request shape, but end-to-end verification against this local base URL can only pass if that service actually exposes a compatible embeddings route.
