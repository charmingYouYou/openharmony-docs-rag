"""API endpoints for retrieval and query."""

from fastapi import APIRouter, HTTPException
from time import time

from app.schemas import (
    RetrieveRequest,
    RetrieveResponse,
    QueryRequest,
    QueryResponse
)
from app.services.retriever import HybridRetriever
from app.services.answer_service import AnswerService
from app.utils.logger import setup_logger, generate_trace_id
from app.utils.citation_builder import CitationBuilder
from app.utils.query_preprocessor import QueryPreprocessor

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest):
    """
    Retrieve relevant document chunks for a query.

    This endpoint performs semantic search without generating an answer.
    """
    trace_id = generate_trace_id()
    start_time = time()

    try:
        logger.info(f"[{trace_id}] Retrieve request: {request.query}")

        # Initialize retriever
        retriever = HybridRetriever()

        # Retrieve chunks
        chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        latency_ms = int((time() - start_time) * 1000)

        logger.info(f"[{trace_id}] Retrieved {len(chunks)} chunks in {latency_ms}ms")

        return RetrieveResponse(
            chunks=chunks,
            trace_id=trace_id,
            latency_ms=latency_ms
        )

    except Exception as e:
        logger.error(f"[{trace_id}] Retrieve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Answer a query using RAG.

    This endpoint retrieves relevant documents and generates an answer using LLM.
    """
    trace_id = generate_trace_id()
    start_time = time()

    try:
        logger.info(f"[{trace_id}] Query request: {request.query}")

        # Initialize services
        preprocessor = QueryPreprocessor()
        retriever = HybridRetriever()
        answer_service = AnswerService()
        citation_builder = CitationBuilder()

        # Preprocess query
        preprocessed = preprocessor.preprocess(request.query)
        logger.info(f"[{trace_id}] Intent: {preprocessed.intent} (confidence: {preprocessed.confidence:.2f})")

        # Retrieve chunks
        chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            preprocessed_query=preprocessed
        )

        if not chunks:
            logger.warning(f"[{trace_id}] No relevant chunks found")
            return QueryResponse(
                answer="抱歉，我在文档中没有找到相关信息。请尝试换一种方式提问，或者查看 OpenHarmony 官方文档。",
                citations=[],
                trace_id=trace_id,
                latency_ms=int((time() - start_time) * 1000),
                used_chunks=0,
                intent={
                    "type": preprocessed.intent.value,
                    "confidence": preprocessed.confidence
                }
            )

        # Check relevance
        if not answer_service.check_relevance(request.query, chunks):
            logger.warning(f"[{trace_id}] Retrieved chunks not relevant enough")
            return QueryResponse(
                answer="抱歉，我在文档中没有找到足够相关的信息来回答您的问题。建议您：\n1. 尝试换一种方式提问\n2. 查看 OpenHarmony 官方文档\n3. 在开发者社区提问",
                citations=[],
                trace_id=trace_id,
                latency_ms=int((time() - start_time) * 1000),
                used_chunks=len(chunks),
                intent={
                    "type": preprocessed.intent.value,
                    "confidence": preprocessed.confidence
                }
            )

        # Generate answer
        answer = answer_service.generate_answer(
            query=request.query,
            chunks=chunks,
            intent=preprocessed.intent
        )

        # Build citations
        citations = citation_builder.build_citations(chunks)

        latency_ms = int((time() - start_time) * 1000)

        logger.info(f"[{trace_id}] Generated answer with {len(citations)} citations in {latency_ms}ms")

        return QueryResponse(
            answer=answer,
            citations=citations,
            trace_id=trace_id,
            latency_ms=latency_ms,
            used_chunks=len(chunks),
            intent={
                "type": preprocessed.intent.value,
                "confidence": preprocessed.confidence
            }
        )

    except Exception as e:
        logger.error(f"[{trace_id}] Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
