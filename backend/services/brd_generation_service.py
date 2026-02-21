"""
Fully Agentic BRD Generation Service.

Replaces the Python-orchestrated REACT pipeline with a true agentic loop
where Gemini autonomously decides what documents to read, analyzes them,
and generates BRD sections via virtual tool calls.

Key concept: "Virtual tools" (submit_brd_section, submit_analysis) are
intercepted before reaching ToolExecutor. Their function call arguments
provide structured JSON without needing response_mime_type (which can't
be combined with tools in the Gemini API).
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
    BRD_GENERATION_TOOLS,
    VIRTUAL_TOOLS,
    ToolExecutor,
    AgentTools,
)
from ..config.firebase import firestore_client, storage_bucket
from ..config import genai_client, settings

logger = logging.getLogger(__name__)


class BRDGenerationService:
    """
    Fully agentic BRD generation.

    The AI autonomously:
    1. Lists project documents (list_project_documents)
    2. Reads relevant documents (get_full_document_text)
    3. Searches by topic/content as needed
    4. Generates each BRD section (submit_brd_section virtual tool)
    5. Submits analysis (submit_analysis virtual tool)
    """

    def __init__(self):
        self.model_name = settings.gemini_model

        # Initialize agent tools for document access
        tools = AgentTools(
            firestore_client=firestore_client,
            storage_client=storage_bucket.client,
        )
        self.tool_executor = ToolExecutor(tools)

        # Build Gemini tool declarations for BRD generation
        self._brd_gen_tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=schema["name"],
                        description=schema["description"],
                        parameters_json_schema=schema["parameters"],
                    )
                    for schema in BRD_GENERATION_TOOLS
                ]
            )
        ]

    async def generate_brd(self, project_id: str) -> BRD:
        """
        Generate a complete BRD using the fully agentic pipeline.

        Args:
            project_id: Project ID to generate BRD for

        Returns:
            Complete BRD model with all 13 sections
        """
        logger.info(f"Starting agentic BRD generation for project {project_id}")

        # Format the agentic prompt
        prompt = prompts.format(
            "brd_generation_agentic",
            project_id=project_id,
        )

        # Execute the agentic workflow
        result = await self._execute_brd_generation_workflow(prompt, project_id)

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
                "pipeline": "fully_agentic",
                "model": self.model_name,
                "sections_generated": len(sections),
                "tool_calls": result.get("tool_calls", []),
                "sources_used": result.get("sources_used", []),
                "iterations": result.get("iterations", 0),
                "token_usage": result.get("token_usage", {}),
            },
        )

        logger.info(
            f"Agentic BRD generation complete: {brd_id} — "
            f"{len(sections)} sections, {len(conflicts)} conflicts, "
            f"{len(result.get('tool_calls', []))} tool calls"
        )
        return brd

    async def _execute_brd_generation_workflow(
        self,
        initial_prompt: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Execute the agentic BRD generation loop.

        The AI calls document tools to gather info, then submits sections
        via submit_brd_section and analysis via submit_analysis.

        Args:
            initial_prompt: Formatted BRD generation prompt
            project_id: Project ID for tool execution

        Returns:
            Dict with sections, analysis, sources_used, tool_calls, iterations
        """
        messages = [types.Content(role="user", parts=[types.Part.from_text(text=initial_prompt)])]
        sources_used = set()
        tool_calls = []
        collected_sections: Dict[str, Dict] = {}
        collected_analysis: Dict[str, Any] = {}
        total_input_tokens = 0
        total_output_tokens = 0
        max_iterations = 30

        logger.info("Starting agentic BRD generation workflow")

        for iteration in range(max_iterations):
            logger.info(
                f"BRD gen iteration {iteration + 1}/{max_iterations} — "
                f"{len(collected_sections)} sections collected"
            )

            response = await asyncio.to_thread(
                self._call_gemini_brd_gen,
                messages,
            )

            # Accumulate token usage
            usage = getattr(response, "usage_metadata", None)
            if usage:
                total_input_tokens += getattr(usage, "prompt_token_count", 0) or 0
                total_output_tokens += getattr(usage, "candidates_token_count", 0) or 0

            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)

            if not candidate.content or not candidate.content.parts:
                finish_str = str(finish_reason) if finish_reason else "unknown"
                logger.warning(
                    f"Empty response from Gemini (finish_reason={finish_str})"
                )

                # Handle malformed function calls — Gemini sometimes outputs
                # Python-style dicts instead of valid JSON for complex schemas
                if "MALFORMED_FUNCTION_CALL" in finish_str:
                    logger.info("Retrying after malformed function call")
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text=(
                                    "Your previous function call was malformed. "
                                    "When calling tools, all arguments MUST be valid JSON "
                                    "with double-quoted strings. Do NOT use single quotes "
                                    "or unquoted values. Try the same call again with "
                                    "properly formatted JSON arguments."
                                )
                            )],
                        )
                    )
                    continue

                # If we haven't collected any sections yet, nudge the AI
                if not collected_sections:
                    logger.info("Nudging AI to begin section generation")
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text=(
                                    "You returned an empty response. Please begin generating "
                                    "BRD sections now. Start by calling submit_brd_section "
                                    "for the executive_summary section, then continue with "
                                    "the remaining sections one at a time."
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
                # AI stopped making calls — we're done
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

                # Intercept virtual tools
                if fn_name == "submit_brd_section":
                    args = dict(function_call.args)
                    section_key = args.get("section_key", "unknown")
                    collected_sections[section_key] = {
                        "title": args.get("title", section_key.replace("_", " ").title()),
                        "content": args.get("content", ""),
                        "citations": list(args.get("citations", [])),
                    }
                    logger.info(f"Collected section: {section_key} ({len(args.get('content', ''))} chars)")

                    # Acknowledge receipt so AI knows to continue
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"status": "accepted", "section_key": section_key},
                        )
                    )
                    continue

                if fn_name == "submit_analysis":
                    args = dict(function_call.args)

                    # Parse flattened conflicts — inner arrays are comma-separated strings
                    raw_conflicts = list(args.get("conflicts", []))
                    parsed_conflicts = []
                    for c in raw_conflicts:
                        c = dict(c) if not isinstance(c, dict) else c
                        # Split comma-separated strings back into lists
                        aff = c.get("affected_requirements", "")
                        src = c.get("sources", "")
                        parsed_conflicts.append({
                            "conflict_type": c.get("conflict_type", "unknown"),
                            "description": c.get("description", ""),
                            "affected_requirements": [s.strip() for s in aff.split(",") if s.strip()] if isinstance(aff, str) else list(aff),
                            "severity": c.get("severity", "medium"),
                            "sources": [s.strip() for s in src.split(",") if s.strip()] if isinstance(src, str) else list(src),
                        })

                    # Parse flattened sentiment — stakeholder_sentiments is semicolon-separated
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

                # Execute real tools
                try:
                    args = dict(function_call.args)
                    if "project_id" in args:
                        args["project_id"] = project_id

                    result = await self.tool_executor.execute(fn_name, args)

                    # Track sources
                    if fn_name == "get_full_document_text":
                        if isinstance(result, dict) and "filename" in result:
                            sources_used.add(result["filename"])
                    elif fn_name == "list_project_documents":
                        if isinstance(result, list):
                            for doc in result:
                                if isinstance(doc, dict) and "filename" in doc:
                                    sources_used.add(doc["filename"])

                    if not isinstance(result, dict):
                        result = {"result": str(result)}

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response=result,
                        )
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed ({fn_name}): {e}")
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"error": str(e)},
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

        # Estimate cost (Gemini 2.5 Pro pricing: $1.25/1M input, $10/1M output)
        cost_input = (total_input_tokens / 1_000_000) * 1.25
        cost_output = (total_output_tokens / 1_000_000) * 10.0
        estimated_cost = round(cost_input + cost_output, 4)

        logger.info(
            f"Token usage: {total_input_tokens} input + {total_output_tokens} output "
            f"= {total_input_tokens + total_output_tokens} total, ~${estimated_cost}"
        )

        return {
            "sections": collected_sections,
            "analysis": collected_analysis,
            "sources_used": list(sources_used),
            "tool_calls": [t for t in tool_calls if t not in VIRTUAL_TOOLS],
            "iterations": min(iteration + 1, max_iterations),
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "estimated_cost_usd": estimated_cost,
            },
        }

    def _call_gemini_brd_gen(self, messages: List) -> Any:
        """Call Gemini with BRD generation tools."""
        return genai_client.models.generate_content(
            model=self.model_name,
            contents=messages,
            config={
                "tools": self._brd_gen_tools,
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 65536,
            },
        )


# Singleton instance
brd_generation_service = BRDGenerationService()
