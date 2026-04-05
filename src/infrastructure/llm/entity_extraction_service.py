"""LLM-based entity extraction service implementation."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import Relationship, SemanticEntry
from src.domain.entities.thought import ThoughtMetadata
from src.domain.exceptions import EntityExtractionError
from src.domain.services.entity_extraction_service import EntityExtractionService
from src.infrastructure.llm.llm_service import LLMService
from src.infrastructure.logging import LoggerMixin, log_function_call, log_external_api_call
from src.infrastructure.retry import llm_retry


class LLMEntityExtractionService(EntityExtractionService, LoggerMixin):
    """LLM-based implementation of the entity extraction service."""

    def __init__(
        self,
        llm_service: LLMService,
        prompts_dir: str = None,
    ):
        """Initialize the entity extraction service.

        Args:
            llm_service: The LLM service to use for extraction
            prompts_dir: Directory containing prompt templates (defaults to src/infrastructure/llm/prompts)
        """
        self._llm_service = llm_service
        self._prompts_dir = prompts_dir or os.path.join(
            os.path.dirname(__file__), "prompts"
        )

        # Load prompt templates
        self._system_prompt = self._load_prompt("entity_extraction_system.txt")
        self._extraction_prompt = self._load_prompt("entity_extraction.txt")

        # Load JSON schema for structured output
        self._extraction_schema = self._load_json_schema(
            "entity_extraction_schema.json"
        )
        
        self.logger.info("LLM entity extraction service initialized")

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from file.

        Args:
            filename: The name of the prompt file

        Returns:
            The prompt template as a string
        """
        try:
            with open(os.path.join(self._prompts_dir, filename), "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            # Return empty string if file doesn't exist
            # This allows for optional prompt files
            return ""

    def _load_json_schema(self, filename: str) -> Optional[Dict]:
        """Load a JSON schema from file.

        Args:
            filename: The name of the schema file

        Returns:
            The JSON schema as a dictionary, or None if file doesn't exist
        """
        try:
            with open(os.path.join(self._prompts_dir, filename), "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    @llm_retry
    async def extract_entities(
        self,
        content: str,
        thought_id: uuid.UUID,
        metadata: Optional[ThoughtMetadata] = None,
    ) -> List[SemanticEntry]:
        """Extract semantic entities from thought content.

        Args:
            content: The raw thought content to analyze
            thought_id: The ID of the thought being analyzed
            metadata: Optional metadata to provide context for extraction

        Returns:
            A list of extracted semantic entries

        Raises:
            EntityExtractionError: If extraction fails
        """
        args = {
            "content_length": len(content),
            "thought_id": str(thought_id),
            "has_metadata": metadata is not None,
        }
        
        try:
            self.logger.info(
                "Starting entity extraction",
                extra={
                    "thought_id": str(thought_id),
                    "content_length": len(content),
                    "has_metadata": metadata is not None,
                }
            )
            
            # Format the extraction prompt with content and metadata
            formatted_prompt = self._format_extraction_prompt(content, metadata)

            # Call the LLM to extract entities
            extraction_result = await self._llm_service.generate(
                prompt=formatted_prompt,
                system_prompt=self._system_prompt,
                json_mode=True,
                json_schema=self._extraction_schema,
            )

            # Convert the LLM response to SemanticEntry objects
            semantic_entries = self._convert_to_semantic_entries(extraction_result, thought_id)
            
            self.logger.info(
                "Entity extraction completed",
                extra={
                    "thought_id": str(thought_id),
                    "entities_extracted": len(semantic_entries),
                    "entity_types": list(set(entry.entity_type.value for entry in semantic_entries)),
                }
            )
            
            log_function_call("extract_entities", args, semantic_entries)
            return semantic_entries

        except Exception as e:
            self.logger.error(
                "Entity extraction failed",
                extra={
                    "thought_id": str(thought_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            log_function_call("extract_entities", args, error=e)
            raise EntityExtractionError(f"Entity extraction failed: {str(e)}")

    def _format_extraction_prompt(
        self, content: str, metadata: Optional[ThoughtMetadata]
    ) -> str:
        """Format the extraction prompt with content and metadata.

        Args:
            content: The thought content
            metadata: Optional thought metadata

        Returns:
            The formatted prompt
        """
        # Start with the base extraction prompt
        prompt = self._extraction_prompt

        # Replace placeholders with actual content
        prompt = prompt.replace("{CONTENT}", content)

        # Add metadata if available
        if metadata:
            metadata_str = json.dumps(metadata.dict(exclude_none=True), indent=2)
            prompt = prompt.replace("{METADATA}", metadata_str)
        else:
            prompt = prompt.replace("{METADATA}", "{}")

        return prompt

    def _convert_to_semantic_entries(
        self, extraction_result: Dict, thought_id: uuid.UUID
    ) -> List[SemanticEntry]:
        """Convert the LLM extraction result to SemanticEntry objects.

        Args:
            extraction_result: The parsed JSON result from the LLM
            thought_id: The ID of the thought being analyzed

        Returns:
            A list of SemanticEntry objects

        Raises:
            EntityExtractionError: If the result format is invalid
        """
        try:
            entities = extraction_result.get("entities", [])
            semantic_entries = []

            # Create a dictionary to store entries by their temporary IDs
            entry_map = {}

            # First pass: Create all semantic entries
            for entity in entities:
                # Validate entity type
                try:
                    entity_type = EntityType(entity["type"].lower())
                except ValueError:
                    # Skip entities with invalid types
                    continue

                # Create a new semantic entry
                entry = SemanticEntry(
                    id=uuid.uuid4(),
                    thought_id=thought_id,
                    entity_type=entity_type,
                    entity_value=entity["value"],
                    confidence=entity.get("confidence", 0.9),
                    context=entity.get("context", ""),
                    relationships=[],
                    extracted_at=datetime.now(),
                )

                semantic_entries.append(entry)

                # Store the entry with its temporary ID for relationship mapping
                entry_map[entity.get("id", str(len(entry_map)))] = entry

            # Second pass: Add relationships
            for entity in entities:
                if "relationships" not in entity:
                    continue

                source_entry = entry_map.get(entity.get("id", ""))
                if not source_entry:
                    continue

                for rel in entity["relationships"]:
                    target_entry = entry_map.get(rel.get("target_id", ""))
                    if not target_entry:
                        continue

                    # Create relationship
                    relationship = Relationship(
                        id=uuid.uuid4(),
                        source_entity_id=source_entry.id,
                        target_entity_id=target_entry.id,
                        relationship_type=rel.get("type", "related_to"),
                        strength=rel.get("strength", 0.9),
                        created_at=datetime.now(),
                    )

                    # Add to source entry's relationships
                    source_entry.relationships.append(relationship)

            return semantic_entries

        except Exception as e:
            raise EntityExtractionError(
                f"Failed to process extraction result: {str(e)}"
            )
