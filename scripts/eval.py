#!/usr/bin/env python3
"""Evaluation script for OpenHarmony Docs RAG system."""

import sys
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.eval.eval_dataset import EVAL_DATASET, get_dataset_stats
from app.services.retriever import HybridRetriever
from app.services.answer_service import AnswerService
from app.utils.query_preprocessor import QueryPreprocessor
from app.utils.citation_builder import CitationBuilder
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGEvaluator:
    """Evaluator for RAG system."""

    def __init__(self):
        self.preprocessor = QueryPreprocessor()
        self.retriever = HybridRetriever()
        self.answer_service = AnswerService()
        self.citation_builder = CitationBuilder()

    async def evaluate_single(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single question.

        Returns:
            Evaluation result with metrics
        """
        question = question_data["question"]
        expected_intent = question_data["expected_intent"]
        expected_docs = question_data["expected_docs"]
        expected_keywords = question_data["expected_keywords"]

        logger.info(f"Evaluating: {question}")

        try:
            # Preprocess query
            preprocessed = self.preprocessor.preprocess(question)

            # Retrieve chunks
            chunks = self.retriever.retrieve(
                query=question,
                top_k=8,
                preprocessed_query=preprocessed
            )

            # Generate answer
            if chunks and self.answer_service.check_relevance(question, chunks):
                answer = self.answer_service.generate_answer(
                    query=question,
                    chunks=chunks,
                    intent=preprocessed.intent
                )
                citations = self.citation_builder.build_citations(chunks)
            else:
                answer = "未找到相关信息"
                citations = []

            # Calculate metrics
            metrics = self._calculate_metrics(
                preprocessed=preprocessed,
                chunks=chunks,
                answer=answer,
                citations=citations,
                expected_intent=expected_intent,
                expected_docs=expected_docs,
                expected_keywords=expected_keywords,
                question_type=question_data["type"],
            )

            return {
                "question": question,
                "type": question_data["type"],
                "predicted_intent": preprocessed.intent.value,
                "expected_intent": expected_intent,
                "answer": answer,
                "num_chunks": len(chunks),
                "num_citations": len(citations),
                "metrics": metrics,
                "success": metrics["overall_success"]
            }

        except Exception as e:
            logger.error(f"Failed to evaluate question: {e}")
            return {
                "question": question,
                "type": question_data["type"],
                "error": str(e),
                "success": False
            }

    def _calculate_metrics(
        self,
        preprocessed,
        chunks,
        answer,
        citations,
        expected_intent,
        expected_docs,
        expected_keywords,
        question_type: str,
    ) -> Dict[str, Any]:
        """Calculate evaluation metrics."""
        metrics = {}

        # 1. Intent accuracy
        metrics["intent_correct"] = preprocessed.intent.value == expected_intent
        metrics["intent_confidence"] = preprocessed.confidence

        # 2. Retrieval metrics
        if chunks:
            # Check if expected docs are in retrieved chunks
            retrieved_paths = [chunk.metadata.get("path", "").lower() for chunk in chunks]
            doc_matches = sum(
                1 for expected_doc in expected_docs
                if any(expected_doc.lower() in path for path in retrieved_paths)
            )
            metrics["doc_recall"] = doc_matches / len(expected_docs) if expected_docs else 1.0
            metrics["top1_score"] = chunks[0].score
            metrics["avg_score"] = sum(c.score for c in chunks) / len(chunks)
        else:
            metrics["doc_recall"] = 1.0 if not expected_docs else 0
            metrics["top1_score"] = 0
            metrics["avg_score"] = 0

        # 3. Answer quality metrics
        answer_lower = answer.lower()
        keyword_matches = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in answer_lower
        )
        metrics["keyword_recall"] = keyword_matches / len(expected_keywords) if expected_keywords else 0

        # Check if answer indicates "not found"
        not_found_indicators = ["没有找到", "未找到", "抱歉", "无法", "不确定"]
        metrics["has_answer"] = not any(indicator in answer for indicator in not_found_indicators)

        # 4. Citation metrics
        metrics["has_citations"] = len(citations) > 0
        metrics["num_citations"] = len(citations)

        # 5. Overall success
        if question_type == "out_of_scope":
            metrics["overall_success"] = (
                metrics["intent_correct"]
                and metrics["keyword_recall"] >= 0.3
                and not metrics["has_answer"]
                and not metrics["has_citations"]
            )
        else:
            metrics["overall_success"] = (
                metrics["intent_correct"] and
                metrics["doc_recall"] >= 0.5 and
                metrics["keyword_recall"] >= 0.3 and
                metrics["has_answer"]
            )

        return metrics

    async def evaluate_all(self, dataset: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate entire dataset.

        Returns:
            Aggregated evaluation results
        """
        if dataset is None:
            dataset = EVAL_DATASET

        logger.info(f"Starting evaluation on {len(dataset)} questions")

        results = []
        for question_data in dataset:
            result = await self.evaluate_single(question_data)
            results.append(result)

        # Aggregate metrics
        aggregated = self._aggregate_results(results)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(dataset),
            "results": results,
            "aggregated_metrics": aggregated
        }

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate evaluation results."""
        # Filter out errors
        valid_results = [r for r in results if "metrics" in r]

        if not valid_results:
            return {"error": "No valid results"}

        # Overall metrics
        total = len(valid_results)
        success_count = sum(1 for r in valid_results if r["success"])

        aggregated = {
            "total_evaluated": total,
            "success_count": success_count,
            "success_rate": success_count / total if total > 0 else 0,
        }

        # Average metrics
        metric_keys = [
            "intent_correct",
            "intent_confidence",
            "doc_recall",
            "top1_score",
            "avg_score",
            "keyword_recall",
            "has_answer",
            "has_citations"
        ]

        for key in metric_keys:
            values = [r["metrics"][key] for r in valid_results if key in r["metrics"]]
            if values:
                if isinstance(values[0], bool):
                    aggregated[f"avg_{key}"] = sum(values) / len(values)
                else:
                    aggregated[f"avg_{key}"] = sum(values) / len(values)

        # By question type
        by_type = defaultdict(list)
        for r in valid_results:
            by_type[r["type"]].append(r)

        aggregated["by_type"] = {}
        for qtype, type_results in by_type.items():
            type_success = sum(1 for r in type_results if r["success"])
            aggregated["by_type"][qtype] = {
                "count": len(type_results),
                "success_count": type_success,
                "success_rate": type_success / len(type_results) if type_results else 0
            }

        return aggregated

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save evaluation results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {output_path}")

    def print_summary(self, results: Dict[str, Any]):
        """Print evaluation summary."""
        agg = results["aggregated_metrics"]

        print("\n" + "=" * 60)
        print("评测结果摘要")
        print("=" * 60)

        print(f"\n总问题数: {agg['total_evaluated']}")
        print(f"成功数: {agg['success_count']}")
        print(f"成功率: {agg['success_rate']:.2%}")

        print("\n平均指标:")
        print(f"  意图识别准确率: {agg.get('avg_intent_correct', 0):.2%}")
        print(f"  意图识别置信度: {agg.get('avg_intent_confidence', 0):.2f}")
        print(f"  文档召回率: {agg.get('avg_doc_recall', 0):.2%}")
        print(f"  Top-1 分数: {agg.get('avg_top1_score', 0):.2f}")
        print(f"  关键词召回率: {agg.get('avg_keyword_recall', 0):.2%}")
        print(f"  有效答案率: {agg.get('avg_has_answer', 0):.2%}")
        print(f"  引用率: {agg.get('avg_has_citations', 0):.2%}")

        print("\n各类型问题成功率:")
        for qtype, stats in agg.get("by_type", {}).items():
            print(f"  {qtype}: {stats['success_rate']:.2%} ({stats['success_count']}/{stats['count']})")

        print("\n" + "=" * 60)


async def main():
    """Main entry point."""
    # Get dataset stats
    stats = get_dataset_stats()
    print("评测数据集统计：")
    print(f"总问题数: {stats['total']}")
    print("\n各类型问题数：")
    for qtype, count in stats['by_type'].items():
        print(f"  {qtype}: {count}")

    print("\n开始评测...")

    # Run evaluation
    evaluator = RAGEvaluator()
    results = await evaluator.evaluate_all()

    # Print summary
    evaluator.print_summary(results)

    # Save results
    output_path = "data/eval/eval_results.json"
    evaluator.save_results(results, output_path)

    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)
