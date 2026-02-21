"""
RAG-based BRD Generation Service.

Replaces the fully agentic loop (up to 30 Gemini iterations with document tools)
with a RAG pipeline:
1. Load all project chunks with embeddings from Firestore
2. Embed section-specific queries
3. Retrieve top-k relevant chunks via cosine similarity
4. Pass pre-retrieved context to Gemini with virtual tools only
5. Gemini generates sections via submit_brd_section (same interception pattern)

Key improvement: Reduces ~15-25 Gemini API calls to 1-3 calls.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.genai import types

from ..models.brd import BRD, BRDSection, Citation, Conflict, Sentiment
from ..utils import generate_brd_id
from ..utils.prompts import prompts
from ..agent.tools import (
    RAG_BRD_GENERATION_TOOLS,
    VIRTUAL_TOOLS,
)
from ..config.firebase import firestore_client, storage_bucket
from ..config import genai_client, settings
from ..utils.token_tracking import calculate_cost, extract_gemini_usage, log_usage
from ..utils.retry import with_retry
from .embedding_service import embedding_service
from .firestore_service import firestore_service

logger = logging.getLogger(__name__)


class BRDGenerationService:
    """
    RAG-based BRD generation.

    The pipeline:
    1. Loads all project chunks (with embeddings) from Firestore
    2. Generates queries for BRD section topics
    3. Retrieves top-k relevant chunks via cosine similarity
    4. Passes pre-retrieved context to Gemini in a single prompt
    5. Gemini generates sections via submit_brd_section virtual tool
    6. Gemini submits analysis via submit_analysis virtual tool
    """

    # Section-specific retrieval queries for RAG
    SECTION_QUERIES = [
        "executive summary project overview objectives goals",
        "project background context current situation business opportunity",
        "business objectives goals targets success criteria SMART",
        "project scope in scope out of scope boundaries deliverables",
        "stakeholders roles responsibilities interests influence",
        "functional requirements features capabilities user stories acceptance criteria",
        "non-functional requirements performance security scalability reliability",
        "dependencies external systems vendors integrations prerequisites",
        "risks mitigation risk assessment probability impact",
        "assumptions constraints limitations budget timeline resource",
        "cost benefit analysis ROI budget investment return",
        "success metrics KPIs measurement targets evaluation",
        "timeline milestones phases schedule deadlines critical path",
        "conflicts contradictions disagreements stakeholder concerns sentiment",
    ]

    def __init__(self):
        self.model_name = settings.gemini_model
        self.embedding_service = embedding_service

        # Build Gemini tool declarations — virtual tools only (no document tools)
        self._rag_tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=schema["name"],
                        description=schema["description"],
                        parameters_json_schema=schema["parameters"],
                    )
                    for schema in RAG_BRD_GENERATION_TOOLS
                ]
            )
        ]

    async def generate_brd(self, project_id: str) -> BRD:
        """
        Generate a complete BRD using the RAG pipeline.

        Args:
            project_id: Project ID to generate BRD for

        Returns:
            Complete BRD model with all 13 sections
        """
        logger.info(f"Starting RAG-based BRD generation for project {project_id}")

        # Execute the RAG workflow
        result = await self._execute_brd_generation_workflow(project_id)

        # Assemble BRD model from collected sections + analysis
        brd_id = generate_brd_id()
        sections = result["sections"]
        analysis = result.get("analysis", {})

        # Build conflict models
        conflicts = []
        for c in analysis.get("conflicts", []):
            try:
                conflicts.append(Conflict(
                    conflict_type=c.get("conflict_type", "unknown"),
                    description=c.get("description", ""),
                    affected_requirements=c.get("affected_requirements", []),
                    severity=c.get("severity", "medium"),
                    sources=c.get("sources", []),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse conflict: {e}")

        # Build sentiment model
        sentiment_data = analysis.get("sentiment", {})
        sentiment = None
        if sentiment_data:
            try:
                sentiment = Sentiment(
                    overall_sentiment=sentiment_data.get("overall_sentiment", "neutral"),
                    confidence=sentiment_data.get("confidence", 0.7),
                    stakeholder_breakdown=sentiment_data.get("stakeholder_breakdown", {}),
                    key_concerns=sentiment_data.get("key_concerns", []),
                )
            except Exception as e:
                logger.warning(f"Failed to parse sentiment: {e}")

        # Helper to build a BRDSection from collected data
        def make_section(key: str) -> Optional[BRDSection]:
            data = sections.get(key)
            if not data:
                return None
            citations = []
            for cit in data.get("citations", []):
                try:
                    citations.append(Citation(
                        doc_id=cit.get("doc_id", ""),
                        chunk_id=cit.get("chunk_id", ""),
                        filename=cit.get("filename", ""),
                        quote=cit.get("quote", ""),
                        relevance_score=min(max(cit.get("relevance_score", 0.5), 0.0), 1.0),
                    ))
                except Exception:
                    pass
            return BRDSection(
                title=data.get("title", key.replace("_", " ").title()),
                content=data.get("content", ""),
                citations=citations,
            )

        brd = BRD(
            brd_id=brd_id,
            project_id=project_id,
            generated_at=datetime.utcnow(),
            document_count=len(result.get("sources_used", [])),
            total_citations=sum(
                len(s.get("citations", []))
                for s in sections.values()
            ),
            # Core sections (required)
            executive_summary=make_section("executive_summary") or BRDSection(title="Executive Summary", content="Not generated"),
            business_objectives=make_section("business_objectives") or BRDSection(title="Business Objectives", content="Not generated"),
            stakeholders=make_section("stakeholders") or BRDSection(title="Stakeholders", content="Not generated"),
            functional_requirements=make_section("functional_requirements") or BRDSection(title="Functional Requirements", content="Not generated"),
            non_functional_requirements=make_section("non_functional_requirements") or BRDSection(title="Non-Functional Requirements", content="Not generated"),
            assumptions=make_section("assumptions") or BRDSection(title="Assumptions", content="Not generated"),
            success_metrics=make_section("success_metrics") or BRDSection(title="Success Metrics", content="Not generated"),
            timeline=make_section("timeline") or BRDSection(title="Timeline", content="Not generated"),
            # Extended sections (optional)
            project_background=make_section("project_background"),
            project_scope=make_section("project_scope"),
            dependencies=make_section("dependencies"),
            risks=make_section("risks"),
            cost_benefit=make_section("cost_benefit"),
            # Analysis
            conflicts=conflicts,
            sentiment=sentiment,
            # Metadata
            generation_metadata={
                "pipeline": "rag",
                "model": self.model_name,
                "sections_generated": len(sections),
                "tool_calls": result.get("tool_calls", []),
                "sources_used": result.get("sources_used", []),
                "iterations": result.get("iterations", 0),
                "token_usage": result.get("token_usage", {}),
                "chunks_retrieved": result.get("chunks_retrieved", 0),
            },
        )

        logger.info(
            f"RAG BRD generation complete: {brd_id} — "
            f"{len(sections)} sections, {len(conflicts)} conflicts, "
            f"{result.get('chunks_retrieved', 0)} chunks retrieved"
        )
        return brd

    async def _execute_brd_generation_workflow(
        self,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Execute the RAG-based BRD generation pipeline.

        Steps:
        1. Load all project chunks with embeddings
        2. Retrieve relevant chunks using multi-query similarity search
        3. Build document summaries from metadata
        4. Format RAG prompt with pre-retrieved context
        5. Call Gemini with virtual tools only
        6. Intercept virtual tool calls to collect sections + analysis
        """
        # Step 1: Load chunks with embeddings
        logger.info("RAG Step 1: Loading project chunks with embeddings")
        chunks = await firestore_service.get_project_chunks_with_embeddings(project_id)
        logger.info(f"Loaded {len(chunks)} chunks with embeddings")

        if not chunks:
            logger.warning("No chunks with embeddings found — proceeding with empty context")

        # Step 2: Retrieve relevant chunks via multi-query search
        logger.info("RAG Step 2: Retrieving relevant chunks via similarity search")
        relevant_chunks = []
        if chunks:
            relevant_chunks = await self.embedding_service.retrieve_for_multiple_queries(
                queries=self.SECTION_QUERIES,
                chunks_with_embeddings=chunks,
                top_k_per_query=settings.rag_top_k,
            )
        logger.info(f"Retrieved {len(relevant_chunks)} unique relevant chunks")

        # Step 3: Build document summaries
        logger.info("RAG Step 3: Building document summaries")
        document_summaries = await self._build_document_summaries(project_id)

        # Step 4: Format the RAG prompt
        logger.info("RAG Step 4: Formatting RAG prompt with retrieved context")
        retrieved_context = self._format_retrieved_context(relevant_chunks)

        prompt = prompts.format(
            "brd_generation_rag",
            project_id=project_id,
            document_count=len(set(c.get("doc_id", "") for c in relevant_chunks)),
            chunk_count=len(relevant_chunks),
            document_summaries=document_summaries,
            retrieved_context=retrieved_context,
        )

        # Step 5-6: Call Gemini and intercept responses
        logger.info("RAG Step 5: Calling Gemini with pre-retrieved context")
        result = await self._execute_rag_generation_loop(prompt, project_id, relevant_chunks)

        return result

    async def _build_document_summaries(self, project_id: str) -> str:
        """Build document summaries from Firestore metadata."""
        docs_ref = firestore_client.collection("documents")
        query = docs_ref.where("project_id", "==", project_id)

        summaries = []
        async for doc in query.stream():
            data = doc.to_dict()
            ai_meta = data.get("ai_metadata", {})
            summary = ai_meta.get("summary", "No summary available")
            tags = ai_meta.get("tags", [])
            doc_type = ai_meta.get("document_type", "unknown")
            filename = data.get("filename", "unknown")

            summaries.append(
                f"- **{filename}** (doc_id: {doc.id}, type: {doc_type})\n"
                f"  Summary: {summary}\n"
                f"  Tags: {', '.join(tags[:8])}"
            )

        return "\n".join(summaries) if summaries else "(No documents found)"

    @staticmethod
    def _format_retrieved_context(chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a text block for the prompt."""
        if not chunks:
            return "(No relevant chunks retrieved. Generate sections noting insufficient data.)"

        context_parts = []
        for i, chunk in enumerate(chunks):
            header = (
                f"--- CHUNK {i+1}/{len(chunks)} ---\n"
                f"chunk_id: {chunk.get('chunk_id', 'unknown')}\n"
                f"doc_id: {chunk.get('doc_id', 'unknown')}\n"
                f"filename: {chunk.get('filename', 'unknown')}\n"
                f"similarity_score: {chunk.get('similarity_score', 0.0)}\n"
                f"chunk_index: {chunk.get('chunk_index', 0)}\n"
            )
            text = chunk.get("text", "")
            context_parts.append(f"{header}\n{text}\n")

        return "\n".join(context_parts)

    async def _execute_rag_generation_loop(
        self,
        prompt: str,
        project_id: str,
        relevant_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute the Gemini generation loop with virtual tools only.

        Simplified version of the old agentic loop — no document tools,
        only intercepts submit_brd_section and submit_analysis.
        Typically completes in 1-3 iterations.
        """
        messages = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        sources_used = set(c.get("filename", "") for c in relevant_chunks if c.get("filename"))
        tool_calls = []
        collected_sections: Dict[str, Dict] = {}
        collected_analysis: Dict[str, Any] = {}
        total_input_tokens = 0
        total_output_tokens = 0
        max_iterations = settings.rag_max_iterations

        for iteration in range(max_iterations):
            logger.info(
                f"RAG generation iteration {iteration + 1}/{max_iterations} — "
                f"{len(collected_sections)} sections collected"
            )

            response = await asyncio.to_thread(
                self._call_gemini_rag,
                messages,
            )

            # Accumulate token usage
            usage = extract_gemini_usage(response)
            if usage:
                total_input_tokens += usage["input_tokens"]
                total_output_tokens += usage["output_tokens"]

            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)

            if not candidate.content or not candidate.content.parts:
                finish_str = str(finish_reason) if finish_reason else "unknown"
                logger.warning(f"Empty response from Gemini (finish_reason={finish_str})")

                if "MALFORMED_FUNCTION_CALL" in finish_str:
                    logger.info("Retrying after malformed function call")
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text=(
                                    "Your previous function call was malformed. "
                                    "All arguments MUST be valid JSON with double-quoted strings. "
                                    "Try the same call again with properly formatted JSON."
                                )
                            )],
                        )
                    )
                    continue

                if not collected_sections:
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text=(
                                    "You returned an empty response. Please begin generating "
                                    "BRD sections now by calling submit_brd_section for each "
                                    "of the 13 sections, using the retrieved context provided."
                                )
                            )],
                        )
                    )
                    continue
                break

            has_function_calls = any(
                part.function_call is not None
                for part in candidate.content.parts
            )

            if not has_function_calls:
                text_preview = ""
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_preview = part.text[:200]
                        break
                logger.info(
                    f"AI returned final text (no more tool calls, "
                    f"finish_reason={finish_reason}): {text_preview!r}"
                )
                break

            function_response_parts = []

            for part in candidate.content.parts:
                if part.function_call is None:
                    continue

                function_call = part.function_call
                fn_name = function_call.name
                logger.info(f"AI called tool: {fn_name}")
                tool_calls.append(fn_name)

                # Intercept submit_brd_section (same logic as before)
                if fn_name == "submit_brd_section":
                    args = dict(function_call.args)
                    section_key = args.get("section_key", "unknown")
                    collected_sections[section_key] = {
                        "title": args.get("title", section_key.replace("_", " ").title()),
                        "content": args.get("content", ""),
                        "citations": list(args.get("citations", [])),
                    }
                    logger.info(f"Collected section: {section_key} ({len(args.get('content', ''))} chars)")

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"status": "accepted", "section_key": section_key},
                        )
                    )
                    continue

                # Intercept submit_analysis (same logic as before)
                if fn_name == "submit_analysis":
                    args = dict(function_call.args)

                    # Parse flattened conflicts
                    raw_conflicts = list(args.get("conflicts", []))
                    parsed_conflicts = []
                    for c in raw_conflicts:
                        c = dict(c) if not isinstance(c, dict) else c
                        aff = c.get("affected_requirements", "")
                        src = c.get("sources", "")
                        parsed_conflicts.append({
                            "conflict_type": c.get("conflict_type", "unknown"),
                            "description": c.get("description", ""),
                            "affected_requirements": [s.strip() for s in aff.split(",") if s.strip()] if isinstance(aff, str) else list(aff),
                            "severity": c.get("severity", "medium"),
                            "sources": [s.strip() for s in src.split(",") if s.strip()] if isinstance(src, str) else list(src),
                        })

                    # Parse flattened sentiment
                    stakeholder_str = args.get("stakeholder_sentiments", "")
                    stakeholder_breakdown = {}
                    if stakeholder_str:
                        for pair in stakeholder_str.split(";"):
                            pair = pair.strip()
                            if ":" in pair:
                                name, sent = pair.rsplit(":", 1)
                                stakeholder_breakdown[name.strip()] = sent.strip()

                    concerns_str = args.get("key_concerns", "")
                    key_concerns = [c.strip() for c in concerns_str.split(";") if c.strip()] if concerns_str else []

                    collected_analysis = {
                        "conflicts": parsed_conflicts,
                        "sentiment": {
                            "overall_sentiment": args.get("overall_sentiment", "neutral"),
                            "confidence": args.get("confidence", 0.7),
                            "stakeholder_breakdown": stakeholder_breakdown,
                            "key_concerns": key_concerns,
                        },
                    }
                    logger.info(
                        f"Collected analysis: {len(parsed_conflicts)} conflicts, "
                        f"sentiment={args.get('overall_sentiment')}"
                    )

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"status": "accepted"},
                        )
                    )
                    continue

                # Unexpected tool call
                logger.warning(f"Unexpected tool call: {fn_name}")
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"error": f"Unknown tool: {fn_name}"},
                    )
                )

            # Feed function responses back to Gemini
            if function_response_parts:
                messages.append(candidate.content)
                messages.append(types.Content(role="user", parts=function_response_parts))
            else:
                break

        # Check completeness
        expected_sections = {
            "executive_summary", "business_objectives", "stakeholders",
            "project_scope", "functional_requirements",
            "non_functional_requirements", "assumptions",
            "success_metrics", "timeline", "project_background",
            "dependencies", "risks", "cost_benefit",
        }
        missing = expected_sections - set(collected_sections.keys())
        if missing:
            logger.warning(f"Missing sections: {missing}")

        # Calculate cost
        estimated_cost = calculate_cost(self.model_name, total_input_tokens, total_output_tokens)

        logger.info(
            f"Token usage: {total_input_tokens} input + {total_output_tokens} output "
            f"= {total_input_tokens + total_output_tokens} total, ~${estimated_cost}"
        )

        # Persist usage (fire-and-forget)
        asyncio.create_task(log_usage(
            firestore_client, project_id, "brd_generation",
            self.model_name, total_input_tokens, total_output_tokens,
        ))

        return {
            "sections": collected_sections,
            "analysis": collected_analysis,
            "sources_used": list(sources_used),
            "tool_calls": [t for t in tool_calls if t not in VIRTUAL_TOOLS],
            "iterations": min(iteration + 1, max_iterations),
            "chunks_retrieved": len(relevant_chunks),
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "estimated_cost_usd": estimated_cost,
            },
        }

    @with_retry()
    def _call_gemini_rag(self, messages: List) -> Any:
        """Call Gemini with RAG tools (virtual tools only)."""
        return genai_client.models.generate_content(
            model=self.model_name,
            contents=messages,
            config={
                "tools": self._rag_tools,
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 65536,
            },
        )


# Singleton instance
brd_generation_service = BRDGenerationService()
