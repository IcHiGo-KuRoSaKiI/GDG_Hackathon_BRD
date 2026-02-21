"""
BRD Agent Service - REACT Pattern Implementation.

Implements the Reason-Act-Observe pattern for intelligent BRD generation:
1. REASON: Analyze which documents are relevant
2. ACT: Extract requirements from relevant documents
3. OBSERVE: Detect conflicts and analyze sentiment
4. GENERATE: Create BRD sections with citations
"""
import asyncio
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..models import (
    BRD,
    BRDSection,
    Citation,
    Conflict,
    Sentiment
)
from ..utils import generate_brd_id
from .firestore_service import firestore_service
from .storage_service import storage_service
from .gemini_service import gemini_service
from ..agent.tools import AgentTools
from ..config import firestore_client, storage_bucket

logger = logging.getLogger(__name__)


class BRDAgentService:
    """Service for BRD generation using REACT agent pattern."""

    def __init__(self):
        """Initialize agent service with tools."""
        self.firestore = firestore_service
        self.storage = storage_service
        self.gemini = gemini_service

        # Initialize agent tools
        self.tools = AgentTools(
            firestore_client=firestore_client,
            storage_client=storage_bucket.client
        )

    async def generate_brd(self, project_id: str) -> BRD:
        """
        Generate complete BRD using REACT pattern.

        Args:
            project_id: Project ID to generate BRD for

        Returns:
            Complete BRD with all 8 sections, citations, conflicts, and sentiment
        """
        logger.info(f"Starting BRD generation for project {project_id}")

        # REACT Pattern
        logger.info("PHASE 1: REASON - Analyzing relevant documents")
        context = await self._reason_phase(project_id)

        logger.info("PHASE 2: ACT - Extracting requirements")
        requirements = await self._act_phase(context)

        logger.info("PHASE 3: OBSERVE - Detecting conflicts and analyzing sentiment")
        conflicts, sentiment = await self._observe_phase(requirements, context)

        logger.info("PHASE 4: GENERATE - Creating BRD sections")
        sections = await self._generate_sections(requirements, conflicts, sentiment, context)

        # Assemble final BRD
        brd_id = generate_brd_id()
        brd = BRD(
            brd_id=brd_id,
            project_id=project_id,
            generated_at=datetime.utcnow(),
            document_count=len(context["relevant_documents"]),
            total_citations=sum(len(s.citations) for s in sections.values()),
            executive_summary=sections["executive_summary"],
            business_objectives=sections["business_objectives"],
            stakeholders=sections["stakeholders"],
            functional_requirements=sections["functional_requirements"],
            non_functional_requirements=sections["non_functional_requirements"],
            assumptions=sections["assumptions"],
            success_metrics=sections["success_metrics"],
            timeline=sections["timeline"],
            conflicts=conflicts,
            sentiment=sentiment,
            generation_metadata={
                "relevant_docs": len(context["relevant_documents"]),
                "total_requirements": len(requirements),
                "conflicts_detected": len(conflicts),
                "phases_completed": ["REASON", "ACT", "OBSERVE", "GENERATE"]
            }
        )

        logger.info(f"BRD generation complete: {brd_id}")
        return brd

    async def _reason_phase(self, project_id: str) -> Dict[str, Any]:
        """
        PHASE 1: REASON - Determine which documents are relevant.

        Args:
            project_id: Project ID

        Returns:
            Context dict with relevant_documents list
        """
        # List all documents with metadata
        logger.info(f"🔧 TOOL CALL: list_project_documents(project_id={project_id})")
        all_docs = await self.tools.list_project_documents(project_id)
        logger.info(f"📊 TOOL RESULT: Found {len(all_docs)} documents")

        # Filter for relevant documents
        # Documents are relevant if they have AI metadata with content indicators
        # This is domain-agnostic - works for any type of document
        relevant_docs = []
        for doc in all_docs:
            # Check if document has AI metadata
            ai_metadata = doc.get("ai_metadata")
            if not ai_metadata:
                logger.debug(f"Doc {doc.get('filename')} has no ai_metadata, skipping")
                continue

            # Check if it has any content indicators that are True
            content_indicators = ai_metadata.get("content_indicators", {})
            indicators = content_indicators.get("indicators", {})

            logger.debug(f"Doc {doc.get('filename')} indicators: {indicators}")

            # Document is relevant if it has ANY True indicator
            if any(indicators.values()):
                relevant_docs.append(doc)
                logger.debug(f"Doc {doc.get('filename')} marked as RELEVANT")
            else:
                logger.debug(f"Doc {doc.get('filename')} has no True indicators, skipping")

        logger.info(f"Found {len(relevant_docs)} relevant documents out of {len(all_docs)} total")

        return {
            "project_id": project_id,
            "all_documents": all_docs,
            "relevant_documents": relevant_docs
        }

    async def _act_phase(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        PHASE 2: ACT - Extract requirements from relevant documents.

        Args:
            context: Context from REASON phase

        Returns:
            List of all requirements extracted
        """
        relevant_docs = context["relevant_documents"]

        # Extract requirements from each document in parallel
        extraction_tasks = []

        for doc in relevant_docs:
            task = self._extract_requirements_from_doc(doc)
            extraction_tasks.append(task)

        # Run all extractions in parallel
        all_requirements = await asyncio.gather(*extraction_tasks)

        # Flatten results and add doc_id to each requirement
        flattened_requirements = []
        for doc_reqs, doc in zip(all_requirements, relevant_docs):
            for req in doc_reqs:
                req["source_doc_id"] = doc["doc_id"]
                req["source_filename"] = doc["filename"]
                flattened_requirements.append(req)

        logger.info(f"Extracted {len(flattened_requirements)} total requirements")

        return flattened_requirements

    async def _extract_requirements_from_doc(self, doc: Dict) -> List[Dict[str, Any]]:
        """
        Extract requirements from a single document.

        Args:
            doc: Document metadata dict

        Returns:
            List of requirements from this document
        """
        try:
            # Get full document text
            logger.info(f"🔧 TOOL CALL: get_full_document_text(doc_id={doc['doc_id']}, filename={doc['filename']})")
            full_text = await self.tools.get_full_document_text(doc["doc_id"])
            logger.info(f"📄 TOOL RESULT: Retrieved {len(full_text)} characters from {doc['filename']}")

            # Extract requirements using Gemini
            requirements = await self.gemini.extract_requirements(full_text)

            return requirements

        except Exception as e:
            logger.error(f"Failed to extract requirements from {doc['filename']}: {e}")
            return []

    async def _observe_phase(
        self,
        requirements: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> tuple[List[Conflict], Sentiment]:
        """
        PHASE 3: OBSERVE - Detect conflicts and analyze sentiment.

        Args:
            requirements: All extracted requirements
            context: Context from REASON phase

        Returns:
            Tuple of (conflicts, sentiment)
        """
        # Convert requirements to JSON for analysis
        requirements_json = json.dumps(requirements, indent=2)

        # Get all stakeholders from documents
        all_stakeholders = set()
        for doc in context["relevant_documents"]:
            all_stakeholders.update(doc.get("key_stakeholders", []))

        stakeholders_json = json.dumps(list(all_stakeholders))

        # Combine all document texts for sentiment analysis
        doc_texts = []
        for doc in context["relevant_documents"]:
            try:
                text = await self.tools.get_full_document_text(doc["doc_id"])
                doc_texts.append(text)
            except Exception as e:
                logger.warning(f"Could not fetch text for {doc['filename']}: {e}")

        combined_text = "\n\n---\n\n".join(doc_texts)

        # Run conflict detection and sentiment analysis in parallel
        conflicts_task = self.gemini.detect_conflicts(requirements_json)
        sentiment_task = self.gemini.analyze_sentiment(combined_text, stakeholders_json)

        conflicts_data, sentiment_data = await asyncio.gather(
            conflicts_task,
            sentiment_task
        )

        # Convert to Pydantic models
        conflicts = [
            Conflict(**conflict) for conflict in conflicts_data
        ]

        # Transform sentiment data to match Sentiment model
        sentiment = Sentiment(
            overall_sentiment=sentiment_data.get("overall", "neutral"),
            confidence=0.8,  # Default confidence for sentiment analysis
            stakeholder_breakdown={
                name: data.get("sentiment", "neutral")
                for name, data in sentiment_data.get("stakeholder_sentiment", {}).items()
            },
            key_concerns=[]  # Extract from stakeholder concerns if needed
        )

        logger.info(f"Detected {len(conflicts)} conflicts")
        logger.info(f"Overall sentiment: {sentiment.overall_sentiment}")

        return conflicts, sentiment

    async def _generate_sections(
        self,
        requirements: List[Dict[str, Any]],
        conflicts: List[Conflict],
        sentiment: Sentiment,
        context: Dict[str, Any]
    ) -> Dict[str, BRDSection]:
        """
        PHASE 4: GENERATE - Create all 8 BRD sections in parallel.

        Args:
            requirements: All extracted requirements
            conflicts: Detected conflicts
            sentiment: Sentiment analysis
            context: Context from REASON phase

        Returns:
            Dict of section_name -> BRDSection
        """
        # Prepare base context (common across all sections)
        base_context = {
            "context": json.dumps({
                "project_id": context["project_id"],
                "documents": [
                    {
                        "filename": doc["filename"],
                        "type": doc.get("ai_metadata", {}).get("document_type", "unknown")
                    }
                    for doc in context["relevant_documents"]
                ]
            }, indent=2),
            "requirements_summary": json.dumps(requirements[:20], indent=2),  # First 20 for summary
            "conflicts_summary": json.dumps([c.model_dump() for c in conflicts], indent=2),
            "sentiment_summary": json.dumps(sentiment.model_dump(), indent=2)
        }

        # Prepare section-specific contexts
        functional_reqs = [r for r in requirements if r.get("type") == "functional"]
        non_functional_reqs = [r for r in requirements if r.get("type") == "non_functional"]
        stakeholders_list = list(sentiment.stakeholder_breakdown.keys())
        dates_extracted = [
            entity for doc in context["relevant_documents"]
            for entity in doc.get("ai_metadata", {}).get("key_entities", {}).get("dates", [])
        ]

        section_contexts = {
            "executive_summary": base_context,
            "business_objectives": {**base_context},
            "stakeholders": {
                **base_context,
                "stakeholders_list": json.dumps(stakeholders_list)
            },
            "functional_requirements": {
                **base_context,
                "functional_requirements": json.dumps(functional_reqs, indent=2)
            },
            "non_functional_requirements": {
                **base_context,
                "non_functional_requirements": json.dumps(non_functional_reqs, indent=2)
            },
            "assumptions": {
                **base_context,
                "all_requirements": json.dumps(requirements, indent=2)
            },
            "success_metrics": {
                **base_context,
                "business_objectives": base_context["requirements_summary"]  # Use requirements as proxy
            },
            "timeline": {
                **base_context,
                "dates_extracted": json.dumps(dates_extracted, indent=2)
            }
        }

        # Generate all 8 sections in parallel with their specific contexts
        generation_tasks = [
            self._generate_single_section(name, section_contexts[name])
            for name in section_contexts.keys()
        ]

        section_results = await asyncio.gather(*generation_tasks)

        # Convert to dict
        sections = {
            name: section
            for name, section in zip(section_contexts.keys(), section_results)
        }

        return sections

    async def _generate_single_section(
        self,
        section_name: str,
        context: Dict[str, Any]
    ) -> BRDSection:
        """
        Generate a single BRD section.

        Args:
            section_name: Name of section to generate
            context: Generation context

        Returns:
            BRDSection with content and citations
        """
        try:
            # Generate section using Gemini
            section_data = await self.gemini.generate_brd_section(
                section_name,
                context
            )

            # Convert citations to Citation models
            citations = [
                Citation(**citation)
                for citation in section_data.get("citations", [])
            ]

            # Create BRDSection
            section = BRDSection(
                title=section_name.replace("_", " ").title(),
                content=section_data.get("content", ""),
                citations=citations,
                subsections=section_data.get("subsections")
            )

            return section

        except Exception as e:
            logger.error(f"Failed to generate section {section_name}: {e}")

            # Return error section
            return BRDSection(
                title=section_name.replace("_", " ").title(),
                content=f"Error generating section: {str(e)}",
                citations=[],
                subsections=None
            )


# Global service instance
agent_service = BRDAgentService()
