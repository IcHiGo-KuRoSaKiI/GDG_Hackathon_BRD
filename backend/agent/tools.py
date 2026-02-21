"""
Agent Tools for BRD Generation

These tools allow the Gemini agent to:
1. List all documents in a project (with AI metadata)
2. Read the full text of specific documents
3. Search documents by topic relevance

These are used during the REACT agent flow for BRD generation.
"""

from typing import List, Dict, Optional
from google.cloud import firestore, storage
import asyncio
from functools import lru_cache


class AgentTools:
    """
    Tools that Gemini can use to access project documents.

    All tools are async for FastAPI compatibility.
    """

    def __init__(self, firestore_client: firestore.AsyncClient, storage_client: storage.Client):
        self.firestore = firestore_client
        self.storage = storage_client

    async def list_project_documents(self, project_id: str) -> List[Dict]:
        """
        List all documents in a project with AI-generated metadata.

        The agent uses this to SEE what documents are available and
        DECIDE which ones to read based on their metadata.

        Args:
            project_id: The project ID

        Returns:
            List of documents with metadata:
            [
                {
                    "doc_id": "doc_123",
                    "filename": "meeting_notes.pdf",
                    "summary": "Sprint planning discussion...",
                    "tags": ["authentication", "OAuth", "security"],
                    "topics": {
                        "authentication": 0.95,
                        "security": 0.85
                    },
                    "contains": {
                        "functional_requirements": true,
                        "decisions": true
                    },
                    "key_stakeholders": ["Security Team", "UX Team"],
                    "key_features": ["OAuth 2.0", "2FA"],
                    "doc_type": "meeting_notes"
                }
            ]
        """
        # Query Firestore for all documents in this project
        docs_ref = self.firestore.collection("documents")
        query = docs_ref.where("project_id", "==", project_id)

        docs = []
        async for doc in query.stream():
            doc_data = doc.to_dict()

            # Extract AI metadata if available
            ai_metadata = doc_data.get("ai_metadata", {})

            # Handle both old and new schema for content indicators
            # Old: ai_metadata["contains"] = {"requirements": True, ...}
            # New: ai_metadata["content_indicators"]["indicators"] = {"requirements": True, ...}
            content_indicators = ai_metadata.get("content_indicators", {})
            indicators = content_indicators.get("indicators", {})
            # Fallback to old schema if new one not present
            if not indicators:
                indicators = ai_metadata.get("contains", {})

            # Handle both old and new schema for topics
            # Old: ai_metadata["topics"] = {"auth": 0.9, ...}
            # New: ai_metadata["topic_relevance"]["topics"] = {"auth": 0.9, ...}
            topic_relevance = ai_metadata.get("topic_relevance", {})
            topics = topic_relevance.get("topics", {})
            # Fallback to old schema
            if not topics:
                topics = ai_metadata.get("topics", {})

            docs.append({
                "doc_id": doc.id,
                "filename": doc_data.get("filename", ""),
                "uploaded_at": doc_data.get("uploaded_at"),

                # AI-generated metadata (for agent reasoning)
                "summary": ai_metadata.get("summary", ""),
                "tags": ai_metadata.get("tags", []),
                "topics": topics,
                "doc_type": ai_metadata.get("document_type", ai_metadata.get("doc_type", "unknown")),
                "contains": indicators,  # Domain-agnostic indicators
                "ai_metadata": ai_metadata,  # Include full metadata for advanced filtering

                # Key entities (for relevance assessment)
                "key_stakeholders": ai_metadata.get("key_entities", {}).get("stakeholders", []),
                "key_features": ai_metadata.get("key_entities", {}).get("features", []),
                "key_decisions": ai_metadata.get("key_entities", {}).get("decisions", []),

                # Sentiment (for stakeholder analysis)
                "sentiment": ai_metadata.get("sentiment", {}).get("overall", "neutral")
            })

        # Sort by upload date (newest first)
        docs.sort(key=lambda d: d.get("uploaded_at", ""), reverse=True)

        return docs

    async def get_full_document_text(self, doc_id: str) -> str:
        """
        Fetch the FULL text of a specific document.

        The agent uses this to READ the complete document content
        when it needs to extract detailed information.

        IMPORTANT: Returns FULL text, not chunks!
        This avoids context loss and allows the agent to see
        the entire document for accurate analysis.

        Args:
            doc_id: Document ID to fetch

        Returns:
            Full document text as string

        Raises:
            ValueError: If document not found
        """
        # Get document metadata from Firestore
        doc_ref = self.firestore.collection("documents").document(doc_id)
        doc = await doc_ref.get()

        if not doc.exists:
            raise ValueError(f"Document {doc_id} not found")

        doc_data = doc.to_dict()

        # Get the Cloud Storage path for parsed full text
        text_path = doc_data.get("text_path")

        if not text_path:
            raise ValueError(f"Document {doc_id} has no parsed text")

        # Download full text from Cloud Storage
        # Format: projects/{project_id}/documents/{doc_id}/text.txt
        # The text_path is a relative path in the bucket
        from ..config import settings
        bucket = self.storage.bucket(settings.storage_bucket)
        blob = bucket.blob(text_path)

        # Download as string (run in thread pool since it's sync)
        full_text = await asyncio.to_thread(blob.download_as_text)

        return full_text

    async def search_documents_by_topic(
        self,
        project_id: str,
        topic: str,
        min_relevance: float = 0.5
    ) -> List[Dict]:
        """
        Search for documents relevant to a specific topic.

        The agent uses this to FILTER documents by topic when
        generating specific sections of the BRD.

        Uses the AI-generated topic relevance scores from metadata.

        Args:
            project_id: Project ID
            topic: Topic to search for (e.g., "authentication", "security")
            min_relevance: Minimum relevance score (0.0-1.0)

        Returns:
            List of relevant documents, sorted by relevance (highest first)

        Example:
            # Find docs about authentication
            auth_docs = await search_documents_by_topic(
                project_id="proj_123",
                topic="authentication",
                min_relevance=0.7
            )
        """
        # Get all documents in project
        all_docs = await self.list_project_documents(project_id)

        # Filter by topic relevance
        relevant_docs = [
            doc for doc in all_docs
            if doc.get("topics", {}).get(topic, 0.0) >= min_relevance
        ]

        # Sort by relevance (highest first)
        relevant_docs.sort(
            key=lambda d: d.get("topics", {}).get(topic, 0.0),
            reverse=True
        )

        return relevant_docs

    async def search_documents_by_content(
        self,
        project_id: str,
        content_type: str
    ) -> List[Dict]:
        """
        Search for documents that contain specific content types.

        Additional tool for finding docs with specific content.

        Args:
            project_id: Project ID
            content_type: Type of content to search for:
                - "functional_requirements"
                - "non_functional_requirements"
                - "decisions"
                - "timeline"
                - "stakeholder_feedback"

        Returns:
            List of documents containing the specified content type
        """
        # Get all documents
        all_docs = await self.list_project_documents(project_id)

        # Filter by content indicators
        matching_docs = [
            doc for doc in all_docs
            if doc.get("contains", {}).get(content_type, False)
        ]

        return matching_docs


# ============================================
# Gemini Function Calling Schemas
# ============================================
# These schemas define how Gemini can call the agent tools

AGENT_TOOLS_SCHEMAS = [
    {
        "name": "list_project_documents",
        "description": """
        Lists all documents in a project with AI-generated metadata.

        Use this tool FIRST to see what documents are available.

        The metadata includes:
        - Summary of the document
        - Tags and topics (with relevance scores)
        - What the document contains (requirements, decisions, etc.)
        - Key stakeholders and features mentioned

        Use this to decide which documents to read in detail.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID to list documents for"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "get_full_document_text",
        "description": """
        Fetches the FULL text of a specific document.

        Use this tool when you need to read the complete content of a document
        to extract detailed requirements, decisions, or other information.

        Returns the entire document text (not chunks) to avoid context loss.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "The document ID to fetch"
                }
            },
            "required": ["doc_id"]
        }
    },
    {
        "name": "search_documents_by_topic",
        "description": """
        Searches for documents relevant to a specific topic.

        Use this tool to find documents about a particular subject when
        generating specific sections of the BRD.

        Topics include: authentication, security, performance, user_experience,
        infrastructure, budget, timeline, technical_architecture, etc.

        Returns documents sorted by relevance (highest first).
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "topic": {
                    "type": "string",
                    "description": "Topic to search for (e.g., 'authentication', 'security')"
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score (0.0-1.0). Default: 0.5",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["project_id", "topic"]
        }
    },
    {
        "name": "search_documents_by_content",
        "description": """
        Searches for documents containing specific types of content.

        Use this tool to find documents with:
        - functional_requirements
        - non_functional_requirements
        - decisions
        - timeline
        - stakeholder_feedback
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "content_type": {
                    "type": "string",
                    "enum": [
                        "functional_requirements",
                        "non_functional_requirements",
                        "decisions",
                        "timeline",
                        "stakeholder_feedback"
                    ],
                    "description": "Type of content to search for"
                }
            },
            "required": ["project_id", "content_type"]
        }
    }
]


# ============================================
# Tool Executor for Gemini Function Calling
# ============================================

class ToolExecutor:
    """
    Executes agent tools called by Gemini.

    Maps Gemini function calls to actual Python methods.
    """

    def __init__(self, tools: AgentTools):
        self.tools = tools

    async def execute(self, function_name: str, arguments: Dict) -> any:
        """
        Execute a tool function by name.

        Args:
            function_name: Name of the tool to execute
            arguments: Arguments for the tool (from Gemini)

        Returns:
            Tool execution result

        Raises:
            ValueError: If function not found
        """
        # Map function names to methods
        function_map = {
            "list_project_documents": self.tools.list_project_documents,
            "get_full_document_text": self.tools.get_full_document_text,
            "search_documents_by_topic": self.tools.search_documents_by_topic,
            "search_documents_by_content": self.tools.search_documents_by_content,
        }

        if function_name not in function_map:
            raise ValueError(f"Unknown function: {function_name}")

        # Execute the function
        function = function_map[function_name]
        result = await function(**arguments)

        return result
