# apps/backend/app/ai/memory/storage.py
"""
Memory Storage - Multi-backend memory storage implementation.

This module provides a unified storage interface that works with:
- Redis for short-term conversation memory
- MongoDB for structured medium-term memory (journals, goals, habits)
- Qdrant for long-term vector-based memory retrieval
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.ai.memory.interfaces import (
    IMemoryStorage,
    MemoryImportance,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)
from app.core.config import settings
from app.db.mongo import get_mongo_client
from app.db.qdrant import get_qdrant_client
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)


class MultiBackendMemoryStorage(IMemoryStorage):
    """
    Multi-backend memory storage implementation.

    Routes memory storage to appropriate backends based on memory type:
    - ConversationMemory -> Redis
    - JournalMemory, GoalMemory, HabitMemory -> MongoDB + Qdrant
    - PreferenceMemory, BehavioralMemory, KnowledgeMemory, EpisodicMemory -> Qdrant
    """

    def __init__(self, vector_size: int = None):
        self._redis_client = None
        self._mongo_client = None
        self._qdrant_client = None
        self._vector_size = vector_size or settings.VECTOR_DIMENSION  # Use configured vector dimension

    def _get_redis(self):
        """Lazy load Redis client."""
        if self._redis_client is None:
            self._redis_client = get_redis_client()
        return self._redis_client

    def _get_mongo(self):
        """Lazy load MongoDB client."""
        if self._mongo_client is None:
            self._mongo_client = get_mongo_client()
        return self._mongo_client

    def _get_qdrant(self):
        """Lazy load Qdrant client."""
        if self._qdrant_client is None:
            self._qdrant_client = get_qdrant_client()
        return self._qdrant_client

    async def store(self, memory: MemoryRecord) -> str:
        """Store a memory record using the appropriate backend."""
        try:
            # Validate user_id is present
            if not memory.user_id:
                raise ValueError("user_id is required for memory storage")

            # Validate memory content size (prevent DoS)
            if len(memory.content) > 100000:  # 100KB limit
                raise ValueError(f"Memory content too large: {len(memory.content)} bytes")

            # Validate embedding vector if present
            if memory.embedding_vector:
                if len(memory.embedding_vector) != self._vector_size:
                    raise ValueError(
                        f"Embedding vector size mismatch: expected {self._vector_size}, "
                        f"got {len(memory.embedding_vector)}"
                    )
                # Validate vector values are within reasonable range
                if not all(-1.0 <= v <= 1.0 for v in memory.embedding_vector):
                    raise ValueError("Embedding vector values must be between -1.0 and 1.0")

            # Check for duplicate memory ID
            existing = await self.retrieve(memory.id, memory.user_id)
            if existing:
                logger.warning(f"Memory {memory.id} already exists, skipping duplicate storage")
                return memory.id

            # Check for duplicate content using hash
            import hashlib
            content_hash = hashlib.sha256(memory.content.encode()).hexdigest()
            # Store hash in metadata for deduplication
            memory.metadata.tags.append(f"content_hash:{content_hash}")

            if memory.memory_type == MemoryType.CONVERSATION:
                return await self._store_conversation_memory(memory)
            elif memory.memory_type in [MemoryType.JOURNAL, MemoryType.GOAL, MemoryType.HABIT]:
                return await self._store_structured_memory(memory)
            else:
                return await self._store_vector_memory(memory)
        except Exception as e:
            logger.error(f"Failed to store memory {memory.id}: {e}")
            raise

    async def _store_conversation_memory(self, memory: MemoryRecord) -> str:
        """Store conversation memory in Redis."""
        redis = self._get_redis()
        key = f"conversation_memory:{memory.user_id}:{memory.id}"

        conversation_data = {
            "id": memory.id,
            "user_id": memory.user_id,
            "role": memory.metadata.tags[0] if memory.metadata.tags else "user",
            "content": memory.content,
            "timestamp": memory.created_at.isoformat(),
            "metadata": {
                "source": memory.metadata.source,
                "importance": memory.metadata.importance.value,
            }
        }

        await redis.set(key, json.dumps(conversation_data), ex=86400)  # 24h TTL
        logger.debug(f"Stored conversation memory {memory.id} in Redis")
        return memory.id

    async def _store_structured_memory(self, memory: MemoryRecord) -> str:
        """Store structured memory in MongoDB and Qdrant with proper transaction compensation."""
        mongo = self._get_mongo()
        qdrant = self._get_qdrant()

        db = mongo.get_default_database()

        # Determine collection based on memory type
        collection_map = {
            MemoryType.JOURNAL: "journal_entries",
            MemoryType.GOAL: "goals",
            MemoryType.HABIT: "habits",
        }
        collection_name = collection_map.get(memory.memory_type)

        if collection_name:
            # Check for duplicate in MongoDB first
            existing = await db[collection_name].find_one({"memory_id": memory.id})
            if existing:
                logger.warning(f"Structured memory {memory.id} already exists in MongoDB")
                return memory.id

            # Store in MongoDB
            mongo_doc = {
                "memory_id": memory.id,
                "user_id": memory.user_id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "metadata": {
                    "importance": memory.metadata.importance.value,
                    "source": memory.metadata.source,
                    "tags": memory.metadata.tags,
                    "created_at": memory.created_at.isoformat(),
                }
            }

            # Track what operations succeeded for compensation
            mongo_succeeded = False
            qdrant_succeeded = False

            try:
                # Step 1: Store in MongoDB first
                result = await db[collection_name].insert_one(mongo_doc)
                mongo_succeeded = True
                logger.debug(f"Stored structured memory {memory.id} in MongoDB")

                # Step 2: Store in Qdrant for vector search if embedding is available
                if memory.embedding_vector:
                    await self._store_in_qdrant(memory, f"medium_term_{collection_name}")
                    qdrant_succeeded = True
                    logger.debug(f"Stored structured memory {memory.id} in Qdrant")

                return memory.id

            except Exception as e:
                logger.error(f"Failed to store structured memory {memory.id}: {e}")

                # Compensation pattern: rollback what succeeded
                if qdrant_succeeded:
                    try:
                        await qdrant.delete(
                            collection_name=f"medium_term_{collection_name}",
                            points_selector=[memory.id]
                        )
                        logger.info(f"Rolled back Qdrant insertion for memory {memory.id}")
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback Qdrant: {rollback_error}")

                if mongo_succeeded:
                    try:
                        await db[collection_name].delete_one({"memory_id": memory.id})
                        logger.info(f"Rolled back MongoDB insertion for memory {memory.id}")
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback MongoDB: {rollback_error}")

                raise

    async def _store_vector_memory(self, memory: MemoryRecord) -> str:
        """Store vector memory in Qdrant."""
        if memory.embedding_vector:
            collection_name = f"long_term_{memory.memory_type.value}"
            await self._store_in_qdrant(memory, collection_name)
        else:
            logger.warning(f"No embedding vector for memory {memory.id}, skipping Qdrant storage")

        return memory.id

    async def _store_in_qdrant(self, memory: MemoryRecord, collection_name: str) -> None:
        """Store memory in Qdrant with vector embedding."""
        qdrant = self._get_qdrant()

        # Ensure collection exists
        try:
            collections = await qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]

            if collection_name not in collection_names:
                await qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self._vector_size,
                        distance=getattr(Distance, settings.DISTANCE_METRIC.upper(), Distance.COSINE)
                    )
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
            raise

        # Prepare payload
        payload = {
            "user_id": memory.user_id,
            "memory_id": memory.id,
            "memory_type": memory.memory_type.value,
            "content": memory.content,
            "importance": memory.metadata.importance.value,
            "source": memory.metadata.source,
            "tags": memory.metadata.tags,
            "created_at": memory.created_at.isoformat(),
            "access_count": memory.metadata.access_count,
        }

        # Store in Qdrant
        await qdrant.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=memory.id,
                    vector=memory.embedding_vector,
                    payload=payload
                )
            ]
        )
        logger.debug(f"Stored memory {memory.id} in Qdrant collection {collection_name}")

    async def retrieve(self, memory_id: str, user_id: str) -> Optional[MemoryRecord]:
        """Retrieve a memory record by ID for a specific user."""
        try:
            # Try Redis first (conversation memory)
            redis = self._get_redis()
            key = f"conversation_memory:{user_id}:{memory_id}"
            redis_data = await redis.get(key)

            if redis_data:
                return self._parse_redis_memory(json.loads(redis_data))

            # Try MongoDB next (structured memory)
            mongo = self._get_mongo()
            db = mongo.get_default_database()

            for collection_name in ["journal_entries", "goals", "habits"]:
                doc = await db[collection_name].find_one({
                    "memory_id": memory_id,
                    "user_id": user_id
                })
                if doc:
                    return self._parse_mongo_memory(doc)

            # Try Qdrant last (vector memory)
            qdrant = self._get_qdrant()
            for collection_name in ["medium_term_journal_entries", "medium_term_goals",
                                   "medium_term_habits", "long_term_preference",
                                   "long_term_behavioral", "long_term_knowledge",
                                   "long_term_episodic"]:
                try:
                    result = await qdrant.retrieve(
                        collection_name=collection_name,
                        ids=[memory_id]
                    )
                    if result and result[0].payload.get("user_id") == user_id:
                        return self._parse_qdrant_memory(result[0])
                except Exception:
                    continue  # Collection might not exist

            logger.warning(f"Memory {memory_id} not found for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def _parse_redis_memory(self, data: Dict[str, Any]) -> MemoryRecord:
        """Parse Redis data into MemoryRecord."""
        metadata = MemoryMetadata(
            user_id=data["user_id"],
            memory_type=MemoryType.CONVERSATION,
            importance=MemoryImportance(data["metadata"]["importance"]),
            source=data["metadata"]["source"],
        )

        return MemoryRecord(
            id=data["id"],
            user_id=data["user_id"],
            memory_type=MemoryType.CONVERSATION,
            content=data["content"],
            metadata=metadata,
            created_at=datetime.fromisoformat(data["timestamp"])
        )

    def _parse_mongo_memory(self, doc: Dict[str, Any]) -> MemoryRecord:
        """Parse MongoDB document into MemoryRecord."""
        memory_type = MemoryType(doc["memory_type"])
        metadata = MemoryMetadata(
            user_id=doc["user_id"],
            memory_type=memory_type,
            importance=MemoryImportance(doc["metadata"]["importance"]),
            source=doc["metadata"]["source"],
            tags=doc["metadata"]["tags"],
        )

        return MemoryRecord(
            id=doc["memory_id"],
            user_id=doc["user_id"],
            memory_type=memory_type,
            content=doc["content"],
            metadata=metadata,
            created_at=datetime.fromisoformat(doc["metadata"]["created_at"])
        )

    def _parse_qdrant_memory(self, point) -> MemoryRecord:
        """Parse Qdrant point into MemoryRecord."""
        payload = point.payload
        memory_type = MemoryType(payload["memory_type"])

        metadata = MemoryMetadata(
            user_id=payload["user_id"],
            memory_type=memory_type,
            importance=MemoryImportance(payload["importance"]),
            source=payload["source"],
            tags=payload["tags"],
            access_count=payload.get("access_count", 0),
        )

        return MemoryRecord(
            id=payload["memory_id"],
            user_id=payload["user_id"],
            memory_type=memory_type,
            content=payload["content"],
            metadata=metadata,
            embedding_vector=point.vector,
            created_at=datetime.fromisoformat(payload["created_at"])
        )

    async def update(self, memory_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory record."""
        try:
            # Try Redis first
            redis = self._get_redis()
            key = f"conversation_memory:{user_id}:{memory_id}"
            redis_data = await redis.get(key)

            if redis_data:
                data = json.loads(redis_data)
                data.update(updates)
                await redis.setex(key, 86400, json.dumps(data))
                return True

            # Try MongoDB
            mongo = self._get_mongo()
            db = mongo.get_default_database()

            for collection_name in ["journal_entries", "goals", "habits"]:
                result = await db[collection_name].update_one(
                    {"memory_id": memory_id, "user_id": user_id},
                    {"$set": updates}
                )
                if result.modified_count > 0:
                    return True

            # Try Qdrant
            qdrant = self._get_qdrant()
            for collection_name in ["medium_term_journal_entries", "medium_term_goals",
                                   "medium_term_habits", "long_term_preference",
                                   "long_term_behavioral", "long_term_knowledge",
                                   "long_term_episodic"]:
                try:
                    # Qdrant doesn't support partial updates, need to retrieve and replace
                    result = await qdrant.retrieve(collection_name=collection_name, ids=[memory_id])
                    if result and result[0].payload.get("user_id") == user_id:
                        payload = result[0].payload
                        payload.update(updates)
                        await qdrant.upsert(
                            collection_name=collection_name,
                            points=[PointStruct(
                                id=memory_id,
                                vector=result[0].vector,
                                payload=payload
                            )]
                        )
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory record."""
        try:
            # Try Redis
            redis = self._get_redis()
            key = f"conversation_memory:{user_id}:{memory_id}"
            result = await redis.delete(key)
            if result > 0:
                return True

            # Try MongoDB
            mongo = self._get_mongo()
            db = mongo.get_default_database()

            for collection_name in ["journal_entries", "goals", "habits"]:
                result = await db[collection_name].delete_one({
                    "memory_id": memory_id,
                    "user_id": user_id
                })
                if result.deleted_count > 0:
                    return True

            # Try Qdrant
            qdrant = self._get_qdrant()
            for collection_name in ["medium_term_journal_entries", "medium_term_goals",
                                   "medium_term_habits", "long_term_preference",
                                   "long_term_behavioral", "long_term_knowledge",
                                   "long_term_episodic"]:
                try:
                    # Verify user ownership before deletion
                    result = await qdrant.retrieve(collection_name=collection_name, ids=[memory_id])
                    if result and result[0].payload.get("user_id") == user_id:
                        await qdrant.delete(collection_name=collection_name, points_selector=[memory_id])
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def list_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryRecord]:
        """List memories for a user with optional filtering."""
        memories = []

        try:
            # Redis memories
            if memory_type is None or memory_type == MemoryType.CONVERSATION:
                redis = self._get_redis()
                pattern = f"conversation_memory:{user_id}:*"
                keys = []
                async for key in redis.scan_iter(match=pattern):
                    keys.append(key)

                for key in keys[offset:offset+limit]:
                    data = await redis.get(key)
                    if data:
                        memories.append(self._parse_redis_memory(json.loads(data)))

            # MongoDB memories
            if memory_type is None or memory_type in [MemoryType.JOURNAL, MemoryType.GOAL, MemoryType.HABIT]:
                mongo = self._get_mongo()
                db = mongo.get_default_database()

                collection_map = {
                    MemoryType.JOURNAL: "journal_entries",
                    MemoryType.GOAL: "goals",
                    MemoryType.HABIT: "habits",
                }

                for mem_type, collection_name in collection_map.items():
                    if memory_type is None or mem_type == memory_type:
                        cursor = db[collection_name].find(
                            {"user_id": user_id},
                            limit=limit,
                            skip=offset
                        )
                        async for doc in cursor:
                            memories.append(self._parse_mongo_memory(doc))

            # Qdrant memories
            if memory_type is None or memory_type in [MemoryType.PREFERENCE, MemoryType.BEHAVIORAL,
                                                       MemoryType.KNOWLEDGE, MemoryType.EPISODIC]:
                qdrant = self._get_qdrant()
                collection_map = {
                    MemoryType.PREFERENCE: "long_term_preference",
                    MemoryType.BEHAVIORAL: "long_term_behavioral",
                    MemoryType.KNOWLEDGE: "long_term_knowledge",
                    MemoryType.EPISODIC: "long_term_episodic",
                }

                for mem_type, collection_name in collection_map.items():
                    if memory_type is None or mem_type == memory_type:
                        try:
                            filter_ = Filter(
                                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                            )
                            result = await qdrant.scroll(
                                collection_name=collection_name,
                                scroll_filter=filter_,
                                limit=limit,
                                offset=offset
                            )
                            for point in result[0]:
                                memories.append(self._parse_qdrant_memory(point))
                        except Exception:
                            continue

            return memories

        except Exception as e:
            logger.error(f"Failed to list memories for user {user_id}: {e}")
            return []

    async def count_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> int:
        """Count memories for a user with optional filtering."""
        count = 0

        try:
            # Redis memories
            if memory_type is None or memory_type == MemoryType.CONVERSATION:
                redis = self._get_redis()
                pattern = f"conversation_memory:{user_id}:*"
                async for key in redis.scan_iter(match=pattern):
                    count += 1

            # MongoDB memories
            if memory_type is None or memory_type in [MemoryType.JOURNAL, MemoryType.GOAL, MemoryType.HABIT]:
                mongo = self._get_mongo()
                db = mongo.get_default_database()

                collection_map = {
                    MemoryType.JOURNAL: "journal_entries",
                    MemoryType.GOAL: "goals",
                    MemoryType.HABIT: "habits",
                }

                for mem_type, collection_name in collection_map.items():
                    if memory_type is None or mem_type == memory_type:
                        count += await db[collection_name].count_documents({"user_id": user_id})

            # Qdrant memories
            if memory_type is None or memory_type in [MemoryType.PREFERENCE, MemoryType.BEHAVIORAL,
                                                       MemoryType.KNOWLEDGE, MemoryType.EPISODIC]:
                qdrant = self._get_qdrant()
                collection_map = {
                    MemoryType.PREFERENCE: "long_term_preference",
                    MemoryType.BEHAVIORAL: "long_term_behavioral",
                    MemoryType.KNOWLEDGE: "long_term_knowledge",
                    MemoryType.EPISODIC: "long_term_episodic",
                }

                for mem_type, collection_name in collection_map.items():
                    if memory_type is None or mem_type == memory_type:
                        try:
                            filter_ = Filter(
                                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                            )
                            result = await qdrant.count(collection_name=collection_name, count_filter=filter_)
                            count += result.count
                        except Exception:
                            continue

            return count

        except Exception as e:
            logger.error(f"Failed to count memories for user {user_id}: {e}")
            return 0
