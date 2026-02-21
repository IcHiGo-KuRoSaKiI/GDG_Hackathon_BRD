"""
Text Refinement Service - Inline BRD editing with AI assistance.

Supports two modes:
1. Simple: Direct text refinement (2-3 seconds)
2. Agentic: AI uses tools to access project documents (4-8 seconds)

Security: Defense-in-depth against prompt injection attacks.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from ..models.brd import (
    RefineTextRequest,
    RefineTextResponse,
    SimpleRefinementResult,
    AgenticGenerationResult,
    TextRefinementMode
)
from ..utils.prompts import prompts
from ..utils.sanitization import escape_user_input
from ..agent.tools import AGENT_TOOLS_SCHEMAS, ToolExecutor, AgentTools
from ..config.firebase import firestore_client, storage_bucket

logger = logging.getLogger(__name__)


class TextRefinementService:
    """
    Service for AI-powered text refinement in BRD sections.

    Security Architecture (Defense-in-Depth):
    1. Request validation (Pydantic) - validates length, format
    2. Pattern detection (Python) - catches known injection attacks
    3. Defensive prompts (AI instruction) - instructs AI to ignore user instructions
    """

    def __init__(self):
        """Initialize the text refinement service."""
        self.model_name = "gemini-2.0-flash-exp"

        # Initialize agent tools for document access
        tools = AgentTools(
            firestore_client=firestore_client,
            storage_client=storage_bucket.client
        )
        self.tool_executor = ToolExecutor(tools)

    async def refine_text(
        self,
        project_id: str,
        brd_id: str,
        request: RefineTextRequest
    ) -> RefineTextResponse:
        """
        Main entry point for text refinement.

        Args:
            project_id: Project ID for document access
            brd_id: BRD ID being edited
            request: Refinement request with instruction and text

        Returns:
            Refined text with metadata

        Raises:
            ValueError: If validation fails or prompt injection detected
            Exception: If AI generation fails

        Security:
            - All inputs validated by Pydantic (Layer 1)
            - Instruction checked for injection patterns (Layer 2)
            - Defensive prompts prevent bypass (Layer 3)
        """
        logger.info(
            f"Text refinement request - Project: {project_id}, "
            f"Mode: {request.mode}, Section: {request.section_context}"
        )

        # Route to appropriate handler based on mode
        if request.mode == TextRefinementMode.SIMPLE:
            return await self._refine_simple(project_id, brd_id, request)
        else:
            return await self._refine_agentic(project_id, brd_id, request)

    async def _refine_simple(
        self,
        project_id: str,
        brd_id: str,
        request: RefineTextRequest
    ) -> RefineTextResponse:
        """
        Simple refinement mode - direct text refinement without document access.

        Flow:
        1. Escape user inputs (wrap in <user_input> tags)
        2. Format defensive prompt with escaped inputs
        3. Call Gemini with structured output (Pydantic schema)
        4. Return refined text

        Args:
            project_id: Project ID
            brd_id: BRD ID
            request: Refinement request

        Returns:
            Refined text response
        """
        logger.info("Simple refinement mode - direct text processing")

        # Layer 3 Security: Escape user inputs to prevent prompt injection
        escaped_instruction = escape_user_input(request.instruction)
        escaped_text = escape_user_input(request.selected_text)

        # Format defensive prompt
        prompt = prompts.format(
            "text_refinement_simple",
            instruction=escaped_instruction,
            text=escaped_text,
            section=request.section_context.value
        )

        # Call Gemini with structured output
        try:
            result = await self._generate_structured(
                prompt,
                SimpleRefinementResult
            )

            logger.info(f"Simple refinement successful - Changes: {result.changes_made}")

            return RefineTextResponse(
                original=request.selected_text,
                refined=result.refined_text,
                sources_used=[],  # No documents used in simple mode
                tool_calls_made=[],  # No tools called
                mode=TextRefinementMode.SIMPLE
            )

        except Exception as e:
            logger.error(f"Simple refinement failed: {e}", exc_info=True)
            raise Exception(f"Text refinement failed: {str(e)}")

    async def _refine_agentic(
        self,
        project_id: str,
        brd_id: str,
        request: RefineTextRequest
    ) -> RefineTextResponse:
        """
        Agentic refinement mode - AI uses tools to access project documents.

        Flow:
        1. Escape user inputs
        2. Format defensive prompt with tool descriptions
        3. Execute agentic workflow (Gemini function calling loop)
        4. AI can call: list_documents, get_document_content, search_documents
        5. Track which documents were accessed
        6. Return generated text with source citations

        Args:
            project_id: Project ID for document access
            brd_id: BRD ID
            request: Refinement request

        Returns:
            Generated text with sources
        """
        logger.info("Agentic refinement mode - document access enabled")

        # Layer 3 Security: Escape user inputs
        escaped_instruction = escape_user_input(request.instruction)
        escaped_text = escape_user_input(request.selected_text)

        # Format defensive prompt with tools
        prompt = prompts.format(
            "text_generation_agentic",
            instruction=escaped_instruction,
            text=escaped_text,
            section=request.section_context.value,
            project_id=project_id
        )

        # Execute agentic workflow with function calling
        try:
            result = await self._execute_agentic_workflow(
                prompt,
                project_id
            )

            logger.info(
                f"Agentic generation successful - "
                f"Sources: {len(result['sources_used'])}, "
                f"Tool calls: {len(result['tool_calls'])}"
            )

            return RefineTextResponse(
                original=request.selected_text,
                refined=result['text'],
                sources_used=result['sources_used'],
                tool_calls_made=result['tool_calls'],
                mode=TextRefinementMode.AGENTIC
            )

        except Exception as e:
            logger.error(f"Agentic refinement failed: {e}", exc_info=True)
            raise Exception(f"Text generation failed: {str(e)}")

    async def _execute_agentic_workflow(
        self,
        initial_prompt: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Execute agentic workflow with Gemini function calling.

        Flow:
        1. Call Gemini with tools enabled
        2. If AI makes function calls:
           - Execute each tool via ToolExecutor
           - Track sources (document filenames)
           - Feed results back to Gemini
        3. Repeat until AI returns final answer (max 5 iterations)
        4. Extract structured output

        Args:
            initial_prompt: Defensive prompt with user instruction
            project_id: Project ID for tool execution

        Returns:
            Dict with:
                - text: Generated text
                - sources_used: List of document filenames
                - tool_calls: List of tool names called
        """
        messages = [{"role": "user", "parts": [initial_prompt]}]
        sources_used = set()  # Track unique document filenames
        tool_calls = []  # Track tool names called
        max_iterations = 5

        logger.info("Starting agentic workflow with function calling")

        for iteration in range(max_iterations):
            logger.info(f"Agentic iteration {iteration + 1}/{max_iterations}")

            # Call Gemini with tools
            response = await asyncio.to_thread(
                self._call_gemini_with_tools,
                messages
            )

            # Check for function calls
            candidate = response.candidates[0]

            if hasattr(candidate.content, 'parts'):
                # Check if any part is a function call
                has_function_calls = any(
                    hasattr(part, 'function_call')
                    for part in candidate.content.parts
                )

                if has_function_calls:
                    # Execute function calls
                    function_responses = []

                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            function_call = part.function_call
                            logger.info(f"AI called tool: {function_call.name}")

                            # Track tool call
                            tool_calls.append(function_call.name)

                            # Execute tool
                            try:
                                # Inject project_id for security
                                args = dict(function_call.args)
                                if 'project_id' in args:
                                    args['project_id'] = project_id

                                result = await self.tool_executor.execute(
                                    function_call.name,
                                    args
                                )

                                # Track sources if document was accessed
                                if function_call.name == "get_full_document_text":
                                    # Extract filename from result if available
                                    if isinstance(result, dict) and 'filename' in result:
                                        sources_used.add(result['filename'])

                                function_responses.append({
                                    "function_call": function_call,
                                    "function_response": {
                                        "name": function_call.name,
                                        "response": result
                                    }
                                })

                            except Exception as e:
                                logger.error(f"Tool execution failed: {e}")
                                function_responses.append({
                                    "function_call": function_call,
                                    "function_response": {
                                        "name": function_call.name,
                                        "response": {"error": str(e)}
                                    }
                                })

                    # Add function responses to conversation
                    messages.append({
                        "role": "model",
                        "parts": [part for part in candidate.content.parts]
                    })
                    messages.append({
                        "role": "user",
                        "parts": [resp["function_response"] for resp in function_responses]
                    })

                    # Continue loop for next iteration
                    continue

            # No function calls - AI has final answer
            logger.info("AI returned final answer (no more tool calls)")

            # Extract final text from response
            final_text = candidate.content.parts[0].text if candidate.content.parts else ""

            return {
                'text': final_text,
                'sources_used': list(sources_used),
                'tool_calls': tool_calls
            }

        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached")
        raise Exception("Maximum iterations reached without final answer")

    def _call_gemini_with_tools(self, messages: List[Dict]) -> Any:
        """
        Call Gemini with tools enabled (synchronous).

        Args:
            messages: Conversation history

        Returns:
            Gemini response
        """
        model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=AGENT_TOOLS_SCHEMAS
        )

        response = model.generate_content(
            contents=messages,
            generation_config={
                "temperature": 0.3,  # Lower for consistency
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )

        return response

    async def _generate_structured(
        self,
        prompt: str,
        response_model: Any
    ) -> Any:
        """
        Generate structured output using Gemini with Pydantic schema.

        Args:
            prompt: Formatted prompt
            response_model: Pydantic model for response schema

        Returns:
            Parsed Pydantic model instance
        """
        model = genai.GenerativeModel(
            model_name=self.model_name
        )

        # Call Gemini in thread pool (blocking call)
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": response_model.model_json_schema(),
                "temperature": 0.3,
                "max_output_tokens": 2048,
            }
        )

        # Parse JSON response into Pydantic model
        import json
        result_json = response.text
        result = response_model.model_validate_json(result_json)

        return result


# Singleton instance
text_refinement_service = TextRefinementService()
