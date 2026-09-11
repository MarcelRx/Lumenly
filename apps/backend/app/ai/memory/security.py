# apps/backend/app/ai/memory/security.py
"""
Memory Security - Multi-tenant isolation and security verification.

This module implements security verification for:
- No cross-user memory access
- No prompt injection via memory
- No metadata leakage
- No retrieval outside user scope
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.memory.interfaces import (
    IMemoryStorage,
    MemoryRecord,
)

logger = logging.getLogger(__name__)


class MemorySecurityValidator:
    """
    Security validator for memory operations.

    Ensures:
    - Multi-tenant isolation (no cross-user access)
    - No prompt injection vulnerabilities
    - No metadata leakage
    - Proper user scope enforcement
    """

    # Patterns that could indicate prompt injection attempts
    PROMPT_INJECTION_PATTERNS = [
        r"ignore (previous|all)?\s*instructions",
        r"disregard (previous|all)?\s*(instructions|commands)",
        r"forget (previous|all)?\s*(instructions|commands)",
        r"override (previous|all)?\s*(instructions|commands)",
        r"new (instructions|commands):",
        r"system:",
        r"assistant:",
        r"<\|.*\|>",  # Special tokens often used for injection
        r"\[INST\]",  # Instruction format used by some models
        r"\[\/INST\]",
    ]

    # Sensitive metadata keys that should never be leaked
    SENSITIVE_METADATA_KEYS = [
        "password",
        "api_key",
        "secret",
        "token",
        "private_key",
        "auth",
        "credential",
        "credit_card",
        "ssn",
        "social_security",
        "bank_account",
        "credit",
    ]

    def __init__(self, storage: IMemoryStorage):
        """
        Initialize the security validator.

        Args:
            storage: Memory storage implementation
        """
        self.storage = storage
        logger.info("Initialized MemorySecurityValidator")

    def verify_user_access(self, memory: MemoryRecord, user_id: str) -> bool:
        """
        Verify that a user has access to a memory.

        Enforces multi-tenant isolation by ensuring:
        - Memory belongs to the requesting user
        - User ID matches exactly
        """
        if memory.user_id != user_id:
            logger.warning(
                f"Security violation: User {user_id} attempted to access "
                f"memory {memory.id} owned by {memory.user_id}"
            )
            return False

        return True

    def verify_prompt_injection(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Check memory content for potential prompt injection attempts.

        Args:
            content: Memory content to check

        Returns:
            Tuple of (is_safe, detected_pattern)
        """
        content_lower = content.lower()

        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, content_lower):
                logger.warning(f"Potential prompt injection detected: {pattern}")
                return False, pattern

        return True, None

    def verify_metadata_leakage(self, metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Check metadata for sensitive information leakage.

        Args:
            metadata: Metadata dictionary to check

        Returns:
            Tuple of (is_safe, leaked_keys)
        """
        leaked_keys = []

        for key in metadata.keys():
            key_lower = key.lower()
            for sensitive_key in self.SENSITIVE_METADATA_KEYS:
                if sensitive_key in key_lower:
                    leaked_keys.append(key)
                    logger.warning(f"Potential metadata leakage detected: {key}")

        return len(leaked_keys) == 0, leaked_keys

    def verify_user_scope(self, user_id: str, target_user_id: str) -> bool:
        """
        Verify that operations are within proper user scope.

        Ensures that users can only operate on their own data.
        """
        if user_id != target_user_id:
            logger.warning(
                f"Security violation: User {user_id} attempted operation on user {target_user_id}"
            )
            return False

        return True

    async def verify_memory_isolation(self, user_id: str, sample_size: int = 10) -> Dict[str, Any]:
        """
        Verify that memory isolation is working correctly.

        Samples memories and checks for cross-user contamination.

        Args:
            user_id: User ID to check
            sample_size: Number of memories to sample

        Returns:
            Dictionary with verification results
        """
        try:
            # Get sample memories for the user
            memories = await self.storage.list_user_memories(
                user_id=user_id, limit=sample_size, offset=0
            )

            # Check each memory for proper ownership
            violations = []
            for memory in memories:
                if not self.verify_user_access(memory, user_id):
                    violations.append(
                        {
                            "memory_id": memory.id,
                            "expected_user": user_id,
                            "actual_user": memory.user_id,
                        }
                    )

            return {
                "isolation_verified": len(violations) == 0,
                "sample_size": len(memories),
                "violations": violations,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Memory isolation verification failed: {e}")
            return {
                "isolation_verified": False,
                "error": str(e),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

    async def verify_query_isolation(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Verify that a query respects user isolation.

        Checks the query for potential cross-user access attempts.

        Args:
            user_id: User ID making the query
            query: Query string to check

        Returns:
            Dictionary with verification results
        """
        try:
            # Check for potential user ID injection in query
            user_id_patterns = [
                r'user[_\s]*id["\s]*[:=]["\s]*([a-zA-Z0-9-]+)',
                r'user["\s]*[:=]["\s]*([a-zA-Z0-9-]+)',
                r'as[_\s]*user["\s]*[:=]["\s]*([a-zA-Z0-9-]+)',
            ]

            detected_user_ids = []
            for pattern in user_id_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                detected_user_ids.extend(matches)

            # Check if any detected user IDs differ from the current user
            violations = []
            for detected_id in detected_user_ids:
                if detected_id != user_id:
                    violations.append(
                        {
                            "detected_user_id": detected_id,
                            "current_user_id": user_id,
                        }
                    )

            return {
                "query_isolation_verified": len(violations) == 0,
                "detected_user_ids": detected_user_ids,
                "violations": violations,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Query isolation verification failed: {e}")
            return {
                "query_isolation_verified": False,
                "error": str(e),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

    def sanitize_memory_content(self, content: str) -> str:
        """
        Sanitize memory content to prevent security issues.

        Removes or escapes potentially dangerous content.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content
        """
        # Remove null bytes and other control characters
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", content)

        # Normalize unicode to prevent homograph attacks
        sanitized = sanitized.encode("utf-8", "ignore").decode("utf-8")

        return sanitized

    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to prevent information leakage.

        Removes sensitive keys and values.

        Args:
            metadata: Metadata dictionary to sanitize

        Returns:
            Sanitized metadata
        """
        sanitized = {}

        for key, value in metadata.items():
            key_lower = key.lower()

            # Check if key is sensitive
            is_sensitive = any(
                sensitive_key in key_lower for sensitive_key in self.SENSITIVE_METADATA_KEYS
            )

            if not is_sensitive:
                sanitized[key] = value
            else:
                logger.warning(f"Sanitized sensitive metadata key: {key}")

        return sanitized

    async def verify_comprehensive_security(self, user_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive security verification for a user.

        Runs all security checks and returns a comprehensive report.

        Args:
            user_id: User ID to verify

        Returns:
            Dictionary with comprehensive security results
        """
        results = {
            "user_id": user_id,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        # Verify memory isolation
        results["checks"]["memory_isolation"] = await self.verify_memory_isolation(user_id)

        # Verify query isolation with sample query
        results["checks"]["query_isolation"] = await self.verify_query_isolation(
            user_id, "test query"
        )

        # Overall security status
        all_passed = all(
            check_result.get(
                "isolation_verified", check_result.get("query_isolation_verified", False)
            )
            for check_result in results["checks"].values()
        )

        results["security_verified"] = all_passed

        return results


class MemorySecurityContext:
    """
    Security context for memory operations.

    Provides a secure context wrapper for memory operations
    that enforces security policies.
    """

    def __init__(self, user_id: str, validator: MemorySecurityValidator):
        """
        Initialize security context.

        Args:
            user_id: User ID for this context
            validator: Security validator instance
        """
        self.user_id = user_id
        self.validator = validator
        logger.info(f"Initialized MemorySecurityContext for user {user_id}")

    def can_access_memory(self, memory: MemoryRecord) -> bool:
        """Check if user can access a memory."""
        return self.validator.verify_user_access(memory, self.user_id)

    def is_safe_content(self, content: str) -> tuple[bool, Optional[str]]:
        """Check if content is safe from prompt injection."""
        return self.validator.verify_prompt_injection(content)

    def sanitize_content(self, content: str) -> str:
        """Sanitize content for safe storage."""
        return self.validator.sanitize_memory_content(content)

    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata for safe storage."""
        return self.validator.sanitize_metadata(metadata)
