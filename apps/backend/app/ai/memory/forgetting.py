# apps/backend/app/ai/memory/forgetting.py
"""
Memory Forgetting - Configurable forgetting policies implementation.

This module implements forgetting policies:
- Never delete high importance memories
- Archive old memories
- Compress redundant memories
- Summarize large memory groups
- Configurable per-user policies
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from enum import Enum

from app.ai.memory.interfaces import (
    IMemoryForgetting,
    IMemoryStorage,
    IMemoryConsolidator,
    MemoryRecord,
    MemoryType,
    MemoryImportance,
)

logger = logging.getLogger(__name__)


class ForgettingAction(str, Enum):
    """Types of forgetting actions."""
    ARCHIVE = "archive"  # Move to archive storage
    COMPRESS = "compress"  # Reduce memory footprint
    SUMMARIZE = "summarize"  # Create summary, archive original
    DELETE = "delete"  # Only for low-importance, expired memories
    KEEP = "keep"  # No action


class ForgettingPolicy:
    """Configuration for a forgetting policy."""
    
    def __init__(
        self,
        name: str,
        importance_threshold: MemoryImportance = MemoryImportance.MEDIUM,
        age_threshold_days: int = 365,
        access_threshold: int = 10,
        max_memories_per_type: Dict[MemoryType, int] = None,
        default_action: ForgettingAction = ForgettingAction.ARCHIVE,
    ):
        """
        Initialize a forgetting policy.
        
        Args:
            name: Policy name
            importance_threshold: Minimum importance to protect from deletion
            age_threshold_days: Age threshold for considering forgetting
            access_threshold: Minimum access count to protect from forgetting
            max_memories_per_type: Maximum memories per type before forgetting
            default_action: Default action for memories that meet forgetting criteria
        """
        self.name = name
        self.importance_threshold = importance_threshold
        self.age_threshold_days = age_threshold_days
        self.access_threshold = access_threshold
        self.max_memories_per_type = max_memories_per_type or {}
        self.default_action = default_action
        
        logger.info(f"Initialized forgetting policy: {name}")


class MemoryForgetting(IMemoryForgetting):
    """
    Memory forgetting implementation with configurable policies.
    
    Implements intelligent forgetting that:
    - Protects high-importance memories
    - Archives old or low-access memories
    - Compresses redundant memories
    - Summarizes large memory groups
    - Never loses critical information
    """
    
    # Default forgetting policies
    DEFAULT_POLICIES = {
        "conservative": ForgettingPolicy(
            name="conservative",
            importance_threshold=MemoryImportance.LOW,
            age_threshold_days=730,  # 2 years
            access_threshold=5,
            max_memories_per_type={
                MemoryType.CONVERSATION: 100,
                MemoryType.JOURNAL: 2000,
                MemoryType.GOAL: 200,
                MemoryType.HABIT: 100,
                MemoryType.PREFERENCE: 1000,
                MemoryType.BEHAVIORAL: 500,
                MemoryType.KNOWLEDGE: None,  # No limit
                MemoryType.EPISODIC: 1000,
            },
            default_action=ForgettingAction.ARCHIVE,
        ),
        "aggressive": ForgettingPolicy(
            name="aggressive",
            importance_threshold=MemoryImportance.MEDIUM,
            age_threshold_days=365,  # 1 year
            access_threshold=10,
            max_memories_per_type={
                MemoryType.CONVERSATION: 50,
                MemoryType.JOURNAL: 1000,
                MemoryType.GOAL: 100,
                MemoryType.HABIT: 50,
                MemoryType.PREFERENCE: 500,
                MemoryType.BEHAVIORAL: 200,
                MemoryType.KNOWLEDGE: None,
                MemoryType.EPISODIC: 500,
            },
            default_action=ForgettingAction.COMPRESS,
        ),
        "default": ForgettingPolicy(
            name="default",
            importance_threshold=MemoryImportance.MEDIUM,
            age_threshold_days=365,
            access_threshold=5,
            max_memories_per_type={
                MemoryType.CONVERSATION: 100,
                MemoryType.JOURNAL: 1000,
                MemoryType.GOAL: 100,
                MemoryType.HABIT: 50,
                MemoryType.PREFERENCE: 500,
                MemoryType.BEHAVIORAL: 200,
                MemoryType.KNOWLEDGE: None,
                MemoryType.EPISODIC: 500,
            },
            default_action=ForgettingAction.ARCHIVE,
        ),
    }
    
    def __init__(
        self,
        storage: IMemoryStorage,
        consolidator: Optional[IMemoryConsolidator] = None,
        policies: Dict[str, ForgettingPolicy] = None,
    ):
        """
        Initialize the memory forgetting system.
        
        Args:
            storage: Memory storage implementation
            consolidator: Optional memory consolidator for summarization
            policies: Custom forgetting policies (uses defaults if None)
        """
        self.storage = storage
        self.consolidator = consolidator
        self.policies = policies or self.DEFAULT_POLICIES
        
        logger.info(f"Initialized MemoryForgetting with {len(self.policies)} policies")
    
    async def should_forget(self, memory: MemoryRecord) -> bool:
        """
        Determine if a memory should be forgotten based on policy.
        
        A memory should be forgotten if:
        - It's below the importance threshold
        - It's older than the age threshold
        - It has low access count
        - The memory type has exceeded maximum count
        
        High-importance memories (CRITICAL, HIGH) are never forgotten.
        """
        # Never forget critical or high importance memories
        if memory.metadata.importance in [MemoryImportance.CRITICAL, MemoryImportance.HIGH]:
            return False
        
        # Check if memory has expired
        if memory.metadata.expires_at and datetime.now(timezone.utc) > memory.metadata.expires_at:
            return True
        
        # Check age threshold
        age_days = (datetime.now(timezone.utc) - memory.created_at).days
        if age_days > 365:  # Default 1 year threshold
            return True
        
        # Check access count
        if memory.metadata.access_count < 5:  # Default threshold
            return True
        
        return False
    
    async def archive_memory(self, memory_id: str, user_id: str) -> bool:
        """
        Archive a memory instead of deleting it.
        
        Archiving preserves the memory but moves it to long-term storage.
        Archived memories are not returned in normal searches but can be
        explicitly retrieved if needed.
        """
        try:
            # Mark memory as archived
            success = await self.storage.update(
                memory_id=memory_id,
                user_id=user_id,
                updates={
                    "archived": True,
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            
            if success:
                logger.info(f"Archived memory {memory_id} for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to archive memory {memory_id}: {e}")
            return False
    
    async def compress_memory(self, memory_id: str, user_id: str) -> bool:
        """
        Compress a memory to reduce storage while preserving core information.
        
        Compression reduces the memory footprint by:
        - Truncating long content while preserving key information
        - Removing redundant metadata
        - Summarizing if content is very long
        """
        try:
            memory = await self.storage.retrieve(memory_id, user_id)
            if not memory:
                return False
            
            # Compress content if very long (> 2000 chars)
            compressed_content = memory.content
            if len(memory.content) > 2000:
                # Simple truncation with ellipsis
                compressed_content = memory.content[:1900] + "... [truncated]"
            
            # Update memory with compressed content
            success = await self.storage.update(
                memory_id=memory_id,
                user_id=user_id,
                updates={
                    "content": compressed_content,
                    "compressed": True,
                    "compressed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            
            if success:
                logger.info(f"Compressed memory {memory_id} for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to compress memory {memory_id}: {e}")
            return False
    
    async def apply_forgetting_policy(
        self,
        user_id: str,
        policy_name: str = "default"
    ) -> Dict[str, int]:
        """
        Apply forgetting policy to user's memories.
        
        Evaluates all memories for a user and applies appropriate actions:
        - Keep: High importance or frequently accessed memories
        - Archive: Old or low-access memories
        - Compress: Large memories
        - Summarize: Groups of similar memories
        - Delete: Only low-importance, expired memories
        
        Args:
            user_id: User ID for multi-tenant isolation
            policy_name: Name of the policy to apply
        
        Returns:
            Dictionary with counts of actions taken
        """
        policy = self.policies.get(policy_name, self.policies["default"])
        
        results = {
            "kept": 0,
            "archived": 0,
            "compressed": 0,
            "summarized": 0,
            "deleted": 0,
            "total_evaluated": 0,
        }
        
        try:
            # Get all memories for user
            memories = await self.storage.list_user_memories(
                user_id=user_id,
                limit=10000,
                offset=0
            )
            
            results["total_evaluated"] = len(memories)
            
            # Group memories by type for per-type limits
            memories_by_type: Dict[MemoryType, List[MemoryRecord]] = {}
            for memory in memories:
                if memory.memory_type not in memories_by_type:
                    memories_by_type[memory.memory_type] = []
                memories_by_type[memory.memory_type].append(memory)
            
            # Process each memory type
            for memory_type, type_memories in memories_by_type.items():
                # Check if type has exceeded maximum
                max_count = policy.max_memories_per_type.get(memory_type)
                if max_count and len(type_memories) > max_count:
                    # Sort by relevance (access count + recency)
                    type_memories.sort(
                        key=lambda m: (
                            m.metadata.access_count,
                            (datetime.now(timezone.utc) - m.created_at).days
                        ),
                        reverse=True
                    )
                    
                    # Mark excess memories for forgetting
                    excess_memories = type_memories[max_count:]
                    for memory in excess_memories:
                        action = await self._determine_action(memory, policy)
                        await self._apply_action(memory, action)
                        results[action.value] += 1
                
                # Process all memories in type
                for memory in type_memories:
                    if await self.should_forget(memory):
                        action = await self._determine_action(memory, policy)
                        await self._apply_action(memory, action)
                        results[action.value] += 1
                    else:
                        results["kept"] += 1
            
            logger.info(
                f"Applied forgetting policy '{policy_name}' for user {user_id}: {results}"
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to apply forgetting policy for user {user_id}: {e}")
            return results
    
    async def _determine_action(
        self,
        memory: MemoryRecord,
        policy: ForgettingPolicy
    ) -> ForgettingAction:
        """
        Determine the appropriate forgetting action for a memory.
        
        Decision logic:
        - CRITICAL/HIGH importance: KEEP
        - MEDIUM importance with recent access: KEEP
        - MEDIUM importance, old: ARCHIVE
        - LOW importance, very large: COMPRESS
        - LOW importance, old, expired: DELETE
        - Otherwise: Use policy default
        """
        # Protect high importance memories
        if memory.metadata.importance in [MemoryImportance.CRITICAL, MemoryImportance.HIGH]:
            return ForgettingAction.KEEP
        
        # Check if memory has expired
        if memory.metadata.expires_at and datetime.now(timezone.utc) > memory.metadata.expires_at:
            if memory.metadata.importance == MemoryImportance.TEMPORARY:
                return ForgettingAction.DELETE
            return ForgettingAction.ARCHIVE
        
        # Check memory size
        if len(memory.content) > 5000:
            return ForgettingAction.COMPRESS
        
        # Check age and access
        age_days = (datetime.now(timezone.utc) - memory.created_at).days
        if age_days > policy.age_threshold_days:
            if memory.metadata.importance == MemoryImportance.TEMPORARY:
                return ForgettingAction.DELETE
            return ForgettingAction.ARCHIVE
        
        # Check access count
        if memory.metadata.access_count < policy.access_threshold:
            if age_days > 180:  # 6 months
                return ForgettingAction.ARCHIVE
            return ForgettingAction.KEEP
        
        # Use policy default
        return policy.default_action
    
    async def _apply_action(
        self,
        memory: MemoryRecord,
        action: ForgettingAction
    ) -> bool:
        """
        Apply the determined forgetting action to a memory.
        """
        try:
            if action == ForgettingAction.KEEP:
                return True  # No action needed
            
            elif action == ForgettingAction.ARCHIVE:
                return await self.archive_memory(memory.id, memory.user_id)
            
            elif action == ForgettingAction.COMPRESS:
                return await self.compress_memory(memory.id, memory.user_id)
            
            elif action == ForgettingAction.SUMMARIZE:
                if self.consolidator:
                    result = await self.consolidator.summarize_memories(
                        [memory.id],
                        memory.user_id
                    )
                    return result is not None
                return False
            
            elif action == ForgettingAction.DELETE:
                # Only delete low-importance memories
                if memory.metadata.importance == MemoryImportance.TEMPORARY:
                    return await self.storage.delete(memory.id, memory.user_id)
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply action {action} to memory {memory.id}: {e}")
            return False
    
    def add_policy(self, policy: ForgettingPolicy) -> None:
        """Add a custom forgetting policy."""
        self.policies[policy.name] = policy
        logger.info(f"Added custom forgetting policy: {policy.name}")
    
    def get_policy(self, name: str) -> Optional[ForgettingPolicy]:
        """Get a forgetting policy by name."""
        return self.policies.get(name)
    
    def list_policies(self) -> List[str]:
        """List available policy names."""
        return list(self.policies.keys())
