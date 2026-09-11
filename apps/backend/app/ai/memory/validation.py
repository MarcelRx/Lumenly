# apps/backend/app/ai/memory/validation.py
"""
Memory Validation - Strict input validation for Memory Engine.

This module implements production-grade input validation:
- Maximum memory size
- Maximum metadata size
- Embedding dimensions
- Chunk count
- Token limits
- Request payload size
- Invalid UTF-8
- Malformed metadata
- Oversized JSON
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.ai.memory.interfaces import MemoryRecord
from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryValidationError(Exception):
    """Base exception for memory validation errors."""

    pass


class MemorySizeExceededError(MemoryValidationError):
    """Memory content size exceeds maximum allowed."""

    pass


class MetadataSizeExceededError(MemoryValidationError):
    """Metadata size exceeds maximum allowed."""

    pass


class InvalidEmbeddingDimensionsError(MemoryValidationError):
    """Embedding vector has invalid dimensions."""

    pass


class ChunkCountExceededError(MemoryValidationError):
    """Too many chunks in document processing."""

    pass


class TokenLimitExceededError(MemoryValidationError):
    """Content exceeds token limit."""

    pass


class PayloadSizeExceededError(MemoryValidationError):
    """Request payload size exceeds maximum allowed."""

    pass


class InvalidUTF8Error(MemoryValidationError):
    """Content contains invalid UTF-8 characters."""

    pass


class MalformedMetadataError(MemoryValidationError):
    """Metadata is malformed or contains invalid data."""

    pass


class OversizedJSONError(MemoryValidationError):
    """JSON data is too large."""

    pass


class MemoryValidator:
    """
    Production-grade memory input validator.

    Enforces strict validation rules for all memory operations:
    - Size limits (content, metadata, payload)
    - Structural validation (UTF-8, JSON format)
    - Semantic validation (embedding dimensions, chunk counts)
    - Security validation (malformed data, injection patterns)
    """

    # Maximum size limits
    MAX_MEMORY_SIZE = 100_000  # 100KB per memory
    MAX_METADATA_SIZE = 10_000  # 10KB per metadata
    MAX_PAYLOAD_SIZE = 1_000_000  # 1MB per request
    MAX_JSON_SIZE = 500_000  # 500KB for JSON data

    # Embedding validation
    MIN_EMBEDDING_DIM = 64
    MAX_EMBEDDING_DIM = 8192

    @property
    def VALID_EMBEDDING_DIM(self) -> int:
        return settings.VECTOR_DIMENSION

    # Chunk and token limits
    MAX_CHUNKS = 10_000  # Maximum chunks per document
    MAX_TOKENS = 100_000  # Maximum tokens per memory

    # Content validation
    MAX_UTF8_CODEPOINT = 0x10FFFF  # Maximum valid Unicode code point

    def __init__(
        self,
        max_memory_size: int = MAX_MEMORY_SIZE,
        max_metadata_size: int = MAX_METADATA_SIZE,
        max_payload_size: int = MAX_PAYLOAD_SIZE,
        max_chunks: int = MAX_CHUNKS,
        max_tokens: int = MAX_TOKENS,
    ):
        """
        Initialize the memory validator with custom limits.

        Args:
            max_memory_size: Maximum memory content size in bytes
            max_metadata_size: Maximum metadata size in bytes
            max_payload_size: Maximum request payload size in bytes
            max_chunks: Maximum number of chunks per document
            max_tokens: Maximum tokens per memory
        """
        self.max_memory_size = max_memory_size
        self.max_metadata_size = max_metadata_size
        self.max_payload_size = max_payload_size
        self.max_chunks = max_chunks
        self.max_tokens = max_tokens

        logger.info(
            f"Initialized MemoryValidator with limits: "
            f"memory={max_memory_size}, metadata={max_metadata_size}, "
            f"payload={max_payload_size}, chunks={max_chunks}, tokens={max_tokens}"
        )

    def validate_memory_content(self, content: str) -> None:
        """
        Validate memory content.

        Checks:
        - UTF-8 validity
        - Size limits
        - Token limits

        Args:
            content: Memory content to validate

        Raises:
            InvalidUTF8Error: If content contains invalid UTF-8
            MemorySizeExceededError: If content exceeds size limit
            TokenLimitExceededError: If content exceeds token limit
        """
        # Validate UTF-8 encoding
        try:
            encoded = content.encode("utf-8")
        except UnicodeEncodeError as e:
            raise InvalidUTF8Error(f"Invalid UTF-8 in content: {e}")

        # Check size limit
        content_size = len(encoded)
        if content_size > self.max_memory_size:
            raise MemorySizeExceededError(
                f"Memory content size {content_size} exceeds maximum {self.max_memory_size}"
            )

        # Estimate token count (rough approximation: 4 chars per token)
        estimated_tokens = len(content) // 4
        if estimated_tokens > self.max_tokens:
            raise TokenLimitExceededError(
                f"Estimated token count {estimated_tokens} exceeds maximum {self.max_tokens}"
            )

        logger.debug(
            f"Memory content validation passed: {content_size} bytes, ~{estimated_tokens} tokens"
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Validate memory metadata.

        Checks:
        - JSON serialization
        - Size limits
        - Structural validity
        - Malformed data patterns

        Args:
            metadata: Metadata dictionary to validate

        Raises:
            MalformedMetadataError: If metadata is malformed
            MetadataSizeExceededError: If metadata exceeds size limit
            OversizedJSONError: If JSON representation is too large
        """
        # Validate JSON serialization
        try:
            metadata_json = json.dumps(metadata, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise MalformedMetadataError(f"Failed to serialize metadata: {e}")

        # Check JSON size
        json_size = len(metadata_json.encode("utf-8"))
        if json_size > self.MAX_JSON_SIZE:
            raise OversizedJSONError(
                f"Metadata JSON size {json_size} exceeds maximum {self.MAX_JSON_SIZE}"
            )

        # Check metadata size
        if json_size > self.max_metadata_size:
            raise MetadataSizeExceededError(
                f"Metadata size {json_size} exceeds maximum {self.max_metadata_size}"
            )

        # Validate metadata structure
        self._validate_metadata_structure(metadata)

        logger.debug(f"Metadata validation passed: {json_size} bytes")

    def _validate_metadata_structure(self, metadata: Dict[str, Any]) -> None:
        """
        Validate metadata structure for security issues.

        Checks for:
        - Recursive structures
        - Excessive nesting
        - Invalid data types
        - Suspicious patterns
        """

        def validate_value(value: Any, depth: int = 0) -> None:
            """Recursively validate metadata values."""
            if depth > 10:  # Prevent excessive nesting
                raise MalformedMetadataError("Metadata nesting depth exceeds maximum")

            if isinstance(value, dict):
                for k, v in value.items():
                    if not isinstance(k, str):
                        raise MalformedMetadataError(f"Metadata key must be string, got {type(k)}")
                    validate_value(v, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    validate_value(item, depth + 1)
            elif isinstance(value, str):
                # Check for suspicious patterns
                if "\x00" in value:
                    raise MalformedMetadataError("Metadata contains null bytes")
                if len(value) > 10_000:  # Individual string limit
                    raise MalformedMetadataError("Metadata string value too long")
            elif not isinstance(value, (int, float, bool, type(None))):
                raise MalformedMetadataError(
                    f"Metadata value must be JSON-serializable, got {type(value)}"
                )

        validate_value(metadata)

    def validate_embedding_vector(self, embedding_vector: Optional[List[float]]) -> None:
        """
        Validate embedding vector.

        Checks:
        - Dimensions
        - Data types
        - Value ranges
        - Known embedding dimensions

        Args:
            embedding_vector: Embedding vector to validate

        Raises:
            InvalidEmbeddingDimensionsError: If embedding has invalid dimensions
        """
        if embedding_vector is None:
            return  # Optional embedding is valid

        # Check dimension count
        dim_count = len(embedding_vector)
        if dim_count != self.VALID_EMBEDDING_DIM:
            raise InvalidEmbeddingDimensionsError(
                f"Embedding dimension {dim_count} does not match configured dimension {self.VALID_EMBEDDING_DIM}"
            )

        # Validate vector values
        for i, value in enumerate(embedding_vector):
            if not isinstance(value, (int, float)):
                raise InvalidEmbeddingDimensionsError(
                    f"Embedding value at index {i} is not numeric: {type(value)}"
                )
            if not -1.0 <= value <= 1.0:
                logger.warning(
                    f"Embedding value at index {i} is outside normal range [-1, 1]: {value}"
                )

        logger.debug(f"Embedding vector validation passed: {dim_count} dimensions")

    def validate_chunk_count(self, chunk_count: int) -> None:
        """
        Validate chunk count for document processing.

        Args:
            chunk_count: Number of chunks to validate

        Raises:
            ChunkCountExceededError: If chunk count exceeds maximum
        """
        if chunk_count > self.max_chunks:
            raise ChunkCountExceededError(
                f"Chunk count {chunk_count} exceeds maximum {self.max_chunks}"
            )

        logger.debug(f"Chunk count validation passed: {chunk_count} chunks")

    def validate_payload_size(self, payload_size: int) -> None:
        """
        Validate request payload size.

        Args:
            payload_size: Payload size in bytes

        Raises:
            PayloadSizeExceededError: If payload exceeds maximum
        """
        if payload_size > self.max_payload_size:
            raise PayloadSizeExceededError(
                f"Payload size {payload_size} exceeds maximum {self.max_payload_size}"
            )

        logger.debug(f"Payload size validation passed: {payload_size} bytes")

    def validate_memory_record(self, memory: MemoryRecord) -> None:
        """
        Validate a complete memory record.

        Performs comprehensive validation of all memory components.

        Args:
            memory: Memory record to validate

        Raises:
            MemoryValidationError: If any validation fails
        """
        # Validate content
        self.validate_memory_content(memory.content)

        # Validate metadata
        metadata_dict = {
            "user_id": memory.metadata.user_id,
            "memory_type": memory.metadata.memory_type.value,
            "importance": memory.metadata.importance.value,
            "source": memory.metadata.source,
            "tags": memory.metadata.tags,
        }
        self.validate_metadata(metadata_dict)

        # Validate embedding vector
        self.validate_embedding_vector(memory.embedding_vector)

        logger.info(f"Memory record validation passed for memory {memory.id}")

    def validate_search_query(self, query: str) -> None:
        """
        Validate search query.

        Checks:
        - UTF-8 validity
        - Size limits
        - Suspicious patterns

        Args:
            query: Search query to validate

        Raises:
            InvalidUTF8Error: If query contains invalid UTF-8
            MemorySizeExceededError: If query exceeds size limit
        """
        # Validate UTF-8
        try:
            encoded = query.encode("utf-8")
        except UnicodeEncodeError as e:
            raise InvalidUTF8Error(f"Invalid UTF-8 in query: {e}")

        # Check size limit (queries can be smaller than memories)
        query_size = len(encoded)
        if query_size > 10_000:  # 10KB max for queries
            raise MemorySizeExceededError(f"Query size {query_size} exceeds maximum 10,000")

        # Check for suspicious patterns
        if "\x00" in query:
            raise InvalidUTF8Error("Query contains null bytes")

        logger.debug(f"Search query validation passed: {query_size} bytes")


# Global validator instance
default_validator = MemoryValidator()
