# apps/backend/app/workers/tasks.py
import logging
import time
import uuid

from bson import ObjectId
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.ai.embeddings.sync_providers import (
    SyncEmbeddingConfig,
    SyncEmbeddingProviderFactory,
)
from app.core.celery_app import celery_app
from app.core.config import settings
from app.workers.memory_worker import SyncMemoryWorkerService

# Import synchronous metrics for Celery workers
try:
    from prometheus_client import CollectorRegistry, Counter, Histogram

    # Use a separate registry for Celery worker metrics to avoid conflicts
    celery_worker_registry = CollectorRegistry()

    # Define synchronous Celery metrics with separate registry
    celery_tasks_total_sync = Counter(
        'celery_tasks_total',
        'Total Celery task executions',
        ['task', 'status'],
        registry=celery_worker_registry
    )

    celery_task_failures_total_sync = Counter(
        'celery_task_failures_total',
        'Total Celery task failures',
        ['task', 'failure_type'],
        registry=celery_worker_registry
    )

    celery_task_retries_total_sync = Counter(
        'celery_task_retries_total',
        'Total Celery task retries',
        ['task'],
        registry=celery_worker_registry
    )

    celery_task_duration_seconds_sync = Histogram(
        'celery_task_duration_seconds',
        'Celery task execution duration in seconds',
        ['task'],
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float('inf')),
        registry=celery_worker_registry
    )

    document_processing_total_sync = Counter(
        'document_processing_total',
        'Total document processing attempts',
        ['status'],
        registry=celery_worker_registry
    )

    document_processing_duration_seconds_sync = Histogram(
        'document_processing_duration_seconds',
        'Document processing duration in seconds',
        ['status'],
        buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, float('inf')),
        registry=celery_worker_registry
    )

    vector_ingestion_failures_total_sync = Counter(
        'vector_ingestion_failures_total',
        'Total vector ingestion failures',
        ['failure_type'],
        registry=celery_worker_registry
    )

    METRICS_AVAILABLE = True
except ImportError:
    # Fallback if prometheus_client is not available
    METRICS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("prometheus_client not available in Celery worker context")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
COLLECTION_NAME = "lumenly_vectors"

logger = logging.getLogger(__name__)


# Exception Classification
class RetryableError(Exception):
    """Base class for retryable errors (transient failures)."""


class PermanentError(Exception):
    """Base class for permanent errors (should not retry)."""


class DocumentNotFoundError(PermanentError):
    """Document not found in database."""


class InvalidDocumentDataError(PermanentError):
    """Document data is corrupted or invalid."""


class UnsupportedFormatError(PermanentError):
    """Document format is not supported."""


class TransientDatabaseError(RetryableError):
    """Temporary database connection or operation failure."""


class TransientQdrantError(RetryableError):
    """Temporary Qdrant connection or operation failure."""





def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)

        # Move start position, accounting for overlap
        if end >= text_length:
            break
        start = end - overlap

    return chunks


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=25 * 60,  # 25 minutes soft timeout
    time_limit=30 * 60,  # 30 minutes hard timeout
)
def process_document_task(self, document_id: str, user_id: str) -> None:
    """
    Celery task to process a document synchronously with production-grade retry strategy.

    This task:
    1. Retrieves the UserDocument by ID from MongoDB (sync) with user_id validation
    2. Updates status to "PROCESSING" (idempotent)
    3. Splits content into overlapping text chunks
    4. For each chunk, generates vector embeddings
    5. Upserts each chunk's vector into Qdrant with metadata (sync)
    6. Updates document with vector IDs and sets status to "PROCESSED"
    7. Handles exceptions by setting status to "FAILED"
    8. Implements retry logic for transient failures
    9. Preserves idempotency across retries
    10. Enforces multi-tenant isolation with explicit user_id parameter

    Retry Strategy:
    - Maximum retries: 3
    - Backoff: Exponential with jitter (max 300 seconds)
    - Retryable errors: Database connection issues, Qdrant unavailability, Redis issues
    - Permanent errors: Invalid document ID, corrupted data, unsupported format, user mismatch

    Args:
        document_id: The ID of the document to process
        user_id: The user ID for ownership validation and multi-tenant isolation
    """
    start_time = time.time()
    retry_count = self.request.retries

    # Track task start metrics
    if METRICS_AVAILABLE:
        celery_tasks_total_sync.labels(task="process_document_task", status="started").inc()

    # Track retry metrics
    if METRICS_AVAILABLE and retry_count > 0:
        celery_task_retries_total_sync.labels(task="process_document_task").inc()

    logger.info(
        f"Processing document {document_id} "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "document_id": document_id,
            "attempt": retry_count + 1,
            "max_attempts": self.max_retries + 1,
            "task_id": self.request.id,
        }
    )

    # Initialize sync clients
    mongo_client = None
    qdrant_client = None
    embedding_provider = None

    try:
        # Initialize MongoDB sync client
        try:
            mongo_client = MongoClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                socketTimeoutMS=30000,
                connectTimeoutMS=5000,
            )
            # Test connection
            mongo_client.admin.command('ping')
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise TransientDatabaseError(f"MongoDB connection failed: {e}")

        # For production, we use 'lumenly' database
        db_name = 'lumenly'
        logger.info(f"Using MongoDB database: {db_name}")

        # Apply UUID codec options for proper UUID handling
        from bson.binary import UuidRepresentation
        from bson.codec_options import CodecOptions
        codec_options = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)
        db = mongo_client.get_database(db_name, codec_options=codec_options)
        collection = db["UserDocument"]  # Beanie uses capitalized collection names

        # Log collection info for debugging
        logger.info(f"Collection: {collection.name}, Document count: {collection.count_documents({})}")

        # Initialize Qdrant sync client
        try:
            protocol = "https" if settings.QDRANT_USE_HTTPS else "http"
            qdrant_client = QdrantClient(
                url=f"{protocol}://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
                api_key=settings.QDRANT_API_KEY or None,
                timeout=30,
            )
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}")
            raise TransientQdrantError(f"Qdrant connection failed: {e}")

        # Ensure collection exists
        try:
            collections = qdrant_client.get_collections()
            existing_collections = [c.name for c in collections.collections]
            if COLLECTION_NAME not in existing_collections:
                logger.info(f"Creating collection '{COLLECTION_NAME}' with {settings.VECTOR_DIMENSION} dimensions")
                distance_metric = getattr(Distance, settings.DISTANCE_METRIC.upper(), Distance.COSINE)
                qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=settings.VECTOR_DIMENSION,
                        distance=distance_metric,
                    ),
                )
        except Exception as e:
            logger.error(f"Qdrant collection check failed: {e}")
            raise TransientQdrantError(f"Qdrant collection check failed: {e}")

        # Initialize synchronous embedding provider
        try:
            # Determine provider name based on environment and API key availability
            provider_name = settings.EMBEDDING_PROVIDER

            # In development/test, use mock if API keys are not properly configured
            if settings.APP_ENV != "production":
                if provider_name == "openai" and not settings.OPENAI_API_KEY or provider_name == "cohere" and not settings.COHERE_API_KEY:
                    provider_name = "mock"

            # Map provider name to API key based on configuration
            api_key = None
            if provider_name == "openai":
                api_key = settings.OPENAI_API_KEY
            elif provider_name == "cohere":
                api_key = settings.COHERE_API_KEY
            elif provider_name == "mock":
                api_key = "mock-key"

            embedding_config = SyncEmbeddingConfig(
                provider=provider_name,
                model=settings.EMBEDDING_MODEL if provider_name != "mock" else "mock-model",
                api_key=api_key,
                dimension=settings.VECTOR_DIMENSION,
            )
            embedding_provider = SyncEmbeddingProviderFactory.create(embedding_config)
            embedding_provider.initialize()
            logger.info(f"Initialized sync embedding provider: {provider_name}")
        except Exception as e:
            logger.error(f"Embedding provider initialization failed: {e}")
            raise TransientDatabaseError(f"Embedding provider initialization failed: {e}")

        # Retrieve the document
        try:
            logger.info(f"Attempting to find document with ObjectId: {document_id}")
            document = collection.find_one({"_id": ObjectId(document_id)})
            logger.info(f"Document query result: {document is not None}")
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
            logger.error(f"MongoDB query failed: {e}")
            raise TransientDatabaseError(f"MongoDB query failed: {e}")
        except Exception as e:
            logger.error(f"Invalid document ID format: {e}")
            raise InvalidDocumentDataError(f"Invalid document ID format: {e}")

        if not document:
            logger.error(f"Document {document_id} not found")
            raise DocumentNotFoundError(f"Document {document_id} not found")

        # Validate user ownership for multi-tenant isolation
        # MongoDB stores UUIDs as Binary, need to convert properly
        from bson.binary import Binary
        document_user_id_raw = document.get("user_id")

        logger.info(f"Raw user_id type: {type(document_user_id_raw)}, value: {document_user_id_raw}")

        # Handle different UUID representations in MongoDB
        if isinstance(document_user_id_raw, Binary):
            # BSON Binary UUID - convert to UUID then to string
            # MongoDB stores UUIDs as Binary with subtype 4 (UUID standard)
            logger.info(f"Detected Binary UUID, bytes: {document_user_id_raw}")
            try:
                document_user_id = str(uuid.UUID(bytes=document_user_id_raw))
            except Exception as e:
                logger.warning(f"Failed to convert Binary to UUID: {e}")
                # Try with standard UUID representation
                document_user_id = str(uuid.UUID(bytes=document_user_id_raw.bytes))
        elif isinstance(document_user_id_raw, bytes):
            # Raw bytes - try to convert as UUID
            logger.info("Detected raw bytes, converting to UUID")
            try:
                document_user_id = str(uuid.UUID(bytes=document_user_id_raw))
            except Exception as e:
                # If conversion fails, use string representation
                logger.warning(f"Failed to convert bytes to UUID: {e}")
                document_user_id = str(document_user_id_raw)
        elif isinstance(document_user_id_raw, uuid.UUID):
            # UUID object
            document_user_id = str(document_user_id_raw)
        else:
            # Already a string
            document_user_id = str(document_user_id_raw)

        logger.info(f"User ID validation - requested: {user_id}, document owner: {document_user_id}")

        if document_user_id != user_id:
            logger.error(
                f"User {user_id} attempted to access document {document_id} owned by {document_user_id}",
                extra={
                    "doc_id": document_id,
                    "req_user_id": user_id,
                    "doc_user_id": document_user_id,
                    "attempt": retry_count + 1,
                }
            )
            raise InvalidDocumentDataError(f"User {user_id} is not authorized to access document {document_id}")

        # Validate document data
        if not document.get("content"):
            logger.error(
                f"Document {document_id} has no content",
                extra={
                    "document_id": document_id,
                    "error": "no_content",
                    "attempt": retry_count + 1,
                }
            )
            raise InvalidDocumentDataError(f"Document {document_id} has no content")

        logger.info(
            f"Processing document {document_id} for user {document.get('user_id')}",
            extra={
                "document_id": document_id,
                "user_id": str(document.get('user_id')),
                "doc_filename": document.get('filename'),
                "content_length": len(document.get('content', '')),
                "attempt": retry_count + 1,
            }
        )

        # Update status to PROCESSING (idempotent - only if not already PROCESSING)
        try:
            result = collection.update_one(
                {"_id": ObjectId(document_id), "status": {"$ne": "PROCESSING"}},
                {"$set": {"status": "PROCESSING"}}
            )
            logger.debug(f"Status update result: {result.modified_count} document(s) updated")
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
            logger.error(f"Failed to update document status: {e}")
            raise TransientDatabaseError(f"Failed to update document status: {e}")

        # Split content into chunks
        chunks = chunk_text(document.get("content", ""))
        logger.info(
            f"Split document into {len(chunks)} chunks",
            extra={
                "document_id": document_id,
                "chunk_count": len(chunks),
                "attempt": retry_count + 1,
            }
        )

        # Process each chunk
        vector_ids = []

        for idx, chunk in enumerate(chunks):
            try:
                logger.debug(f"Generating embedding for chunk {idx + 1}/{len(chunks)}")
                # Generate embedding using synchronous provider
                embedding = embedding_provider.embed(chunk)

                # Generate vector ID
                vector_id = str(uuid.uuid4())

                # Upsert to Qdrant with metadata
                payload = {
                    "user_id": str(document.get("user_id")),
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text_content": chunk,
                }

                logger.debug(f"Upserting vector to Qdrant for chunk {idx + 1}/{len(chunks)}")
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=vector_id,
                            vector=embedding,
                            payload=payload,
                        ),
                    ],
                )

                vector_ids.append(vector_id)
                logger.info(
                    f"Processed chunk {idx + 1}/{len(chunks)} for document {document_id}",
                    extra={
                        "document_id": document_id,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "vector_id": vector_id,
                        "attempt": retry_count + 1,
                    }
                )

            except Exception as e:
                logger.error(f"Failed to process chunk {idx} for document {document_id}: {e}")
                # Track vector ingestion failure metrics
                if METRICS_AVAILABLE:
                    vector_ingestion_failures_total_sync.labels(failure_type=type(e).__name__).inc()
                # Classify error based on type
                if "Qdrant" in str(type(e).__module__) or "connection" in str(e).lower():
                    raise TransientQdrantError(f"Qdrant upsert failed for chunk {idx}: {e}")
                else:
                    raise

        # Update document with results
        try:
            collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "vector_ids": vector_ids,
                        "chunk_count": len(chunks),
                        "status": "PROCESSED",
                        "error_message": None
                    }
                }
            )
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
            logger.error(f"Failed to update document status to PROCESSED: {e}")
            raise TransientDatabaseError(f"Failed to update document status to PROCESSED: {e}")

        logger.info(
            f"Successfully processed document {document_id} with {len(chunks)} chunks",
            extra={
                "document_id": document_id,
                "chunk_count": len(chunks),
                "vector_count": len(vector_ids),
                "attempt": retry_count + 1,
                "status": "PROCESSED",
            }
        )

        # Track success metrics
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            celery_tasks_total_sync.labels(task="process_document_task", status="completed").inc()
            document_processing_total_sync.labels(status="success").inc()
            document_processing_duration_seconds_sync.labels(status="success").observe(duration)

    except PermanentError as e:
        # Permanent errors - do not retry, mark as FAILED immediately
        logger.error(
            f"Document {document_id} processing failed permanently: {e} "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})",
            extra={
                "document_id": document_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "attempt": retry_count + 1,
                "max_attempts": self.max_retries + 1,
                "status": "FAILED",
                "retryable": False,
            }
        )

        # Try to update document status to FAILED
        try:
            if mongo_client:
                db = mongo_client.get_default_database()
                collection = db["user_documents"]
                collection.update_one(
                    {"_id": ObjectId(document_id)},
                    {
                        "$set": {
                            "status": "FAILED",
                            "error_message": f"{type(e).__name__}: {e!s}"
                        }
                    }
                )
        except Exception as save_error:
            logger.error(f"Failed to update document status to FAILED: {save_error}")

        # Track permanent failure metrics
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            celery_task_failures_total_sync.labels(task="process_document_task", failure_type=type(e).__name__).inc()
            celery_tasks_total_sync.labels(task="process_document_task", status="failed").inc()
            document_processing_total_sync.labels(status="failed").inc()
            document_processing_duration_seconds_sync.labels(status="failed").observe(duration)

        # Do not raise for permanent errors - task completes with FAILED status
        return

    except RetryableError as e:
        # Retryable errors - will be automatically retried by Celery
        logger.warning(
            f"Document {document_id} processing failed transiently: {e} "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})",
            extra={
                "document_id": document_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "attempt": retry_count + 1,
                "max_attempts": self.max_retries + 1,
                "retryable": True,
                "will_retry": retry_count < self.max_retries,
            }
        )

        # Try to update document status to FAILED if this is the last retry
        if retry_count >= self.max_retries:
            logger.error(
                f"Document {document_id} failed after {self.max_retries + 1} attempts: {e}",
                extra={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "total_attempts": self.max_retries + 1,
                    "status": "FAILED",
                    "retryable": True,
                    "exhausted_retries": True,
                }
            )
            try:
                if mongo_client:
                    db = mongo_client.get_default_database()
                    collection = db["user_documents"]
                    collection.update_one(
                        {"_id": ObjectId(document_id)},
                        {
                            "$set": {
                                "status": "FAILED",
                                "error_message": f"Failed after {self.max_retries + 1} attempts: {e!s}"
                            }
                        }
                    )
            except Exception as save_error:
                logger.error(f"Failed to update document status to FAILED: {save_error}")

            # Track exhausted retry metrics
            if METRICS_AVAILABLE:
                duration = time.time() - start_time
                celery_task_failures_total_sync.labels(task="process_document_task", failure_type="exhausted_retries").inc()
                celery_tasks_total_sync.labels(task="process_document_task", status="failed").inc()
                document_processing_total_sync.labels(status="failed").inc()
                document_processing_duration_seconds_sync.labels(status="failed").observe(duration)

            return

        # Re-raise to trigger Celery's retry mechanism
        raise

    except (SoftTimeLimitExceeded, TimeLimitExceeded) as e:
        # Timeout errors - mark as FAILED and do not retry
        logger.error(
            f"Document {document_id} processing timed out: {e} "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})",
            extra={
                "document_id": document_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "attempt": retry_count + 1,
                "max_attempts": self.max_retries + 1,
                "status": "FAILED",
                "retryable": False,
                "timeout": True,
            }
        )

        # Try to update document status to FAILED
        try:
            if mongo_client:
                db = mongo_client.get_default_database()
                collection = db["user_documents"]
                collection.update_one(
                    {"_id": ObjectId(document_id)},
                    {
                        "$set": {
                            "status": "FAILED",
                            "error_message": f"Processing timed out: {e!s}"
                        }
                    }
                )
        except Exception as save_error:
            logger.error(f"Failed to update document status to FAILED: {save_error}")

        # Track timeout metrics
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            celery_task_failures_total_sync.labels(task="process_document_task", failure_type="timeout").inc()
            celery_tasks_total_sync.labels(task="process_document_task", status="failed").inc()
            document_processing_total_sync.labels(status="failed").inc()
            document_processing_duration_seconds_sync.labels(status="failed").observe(duration)

        # Do not raise - mark as FAILED and complete
        return

    except Exception as e:
        # Unhandled errors - treat as permanent to avoid infinite retries
        logger.error(
            f"Document {document_id} processing failed with unexpected error: {e} "
            f"(attempt {retry_count + 1}/{self.max_retries + 1})",
            extra={
                "document_id": document_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "attempt": retry_count + 1,
                "max_attempts": self.max_retries + 1,
                "status": "FAILED",
                "retryable": False,
                "unexpected": True,
            }
        )

        # Try to update document status to FAILED
        try:
            if mongo_client:
                db = mongo_client.get_default_database()
                collection = db["user_documents"]
                collection.update_one(
                    {"_id": ObjectId(document_id)},
                    {
                        "$set": {
                            "status": "FAILED",
                            "error_message": f"Unexpected error: {e!s}"
                        }
                    }
                )
        except Exception as save_error:
            logger.error(f"Failed to update document status to FAILED: {save_error}")

        # Track unexpected error metrics
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            celery_task_failures_total_sync.labels(task="process_document_task", failure_type="unexpected").inc()
            celery_tasks_total_sync.labels(task="process_document_task", status="failed").inc()
            document_processing_total_sync.labels(status="failed").inc()
            document_processing_duration_seconds_sync.labels(status="failed").observe(duration)

        # Do not raise - mark as FAILED and complete
        return

    finally:
        # Close sync clients
        if mongo_client is not None:
            mongo_client.close()
        if qdrant_client is not None:
            qdrant_client.close()
        if embedding_provider is not None:
            embedding_provider.close()


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=15 * 60,  # 15 minutes soft timeout
    time_limit=20 * 60,  # 20 minutes hard timeout
)
def memory_consolidation_task(
    self,
    user_id: str,
    memory_type: str | None = None
) -> dict:
    """
    Celery task to consolidate similar memories for a user.

    This task:
    1. Initializes the Memory Manager
    2. Finds similar memories of the specified type
    3. Consolidates them into summarized memories
    4. Archives original memories
    5. Returns consolidation results

    Args:
        user_id: The user ID to consolidate memories for
        memory_type: Optional memory type to consolidate (consolidates all if None)

    Returns:
        Dictionary with consolidation results
    """
    retry_count = self.request.retries
    logger.info(
        f"Memory consolidation task for user {user_id} "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "user_id": user_id,
            "memory_type": memory_type,
            "attempt": retry_count + 1,
            "task_id": self.request.id,
        }
    )

    try:
        # Use synchronous memory worker service
        memory_worker = SyncMemoryWorkerService()
        try:
            results = memory_worker.consolidate_user_memories_sync(
                user_id=user_id,
                memory_type=memory_type
            )

            # Format results
            consolidated_count = len(results)
            source_memory_ids = []
            for result in results:
                source_memory_ids.extend(result.get("source_memory_ids", []))

            logger.info(
                f"Memory consolidation completed for user {user_id}: "
                f"{consolidated_count} groups consolidated, "
                f"{len(source_memory_ids)} source memories archived"
            )

            return {
                "status": "completed",
                "user_id": user_id,
                "memory_type": memory_type,
                "consolidated_count": consolidated_count,
                "source_memory_count": len(source_memory_ids),
                "source_memory_ids": source_memory_ids,
            }
        finally:
            memory_worker.close()

    except SoftTimeLimitExceeded:
        logger.error(
            f"Memory consolidation task timed out for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        raise RetryableError("Task timed out")

    except TimeLimitExceeded:
        logger.error(
            f"Memory consolidation task hard timeout for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        return {
            "status": "timeout",
            "user_id": user_id,
            "error": "Task exceeded hard time limit"
        }

    except Exception as e:
        logger.error(
            f"Memory consolidation task failed for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "error": str(e),
                "attempt": retry_count + 1,
                "task_id": self.request.id,
            }
        )
        raise RetryableError(f"Memory consolidation failed: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=10 * 60,  # 10 minutes soft timeout
    time_limit=15 * 60,  # 15 minutes hard timeout
)
def memory_cleanup_task(
    self,
    user_id: str,
    policy_name: str = "default"
) -> dict:
    """
    Celery task to clean up memories using forgetting policy.

    This task:
    1. Initializes the Memory Manager
    2. Applies the specified forgetting policy
    3. Archives, compresses, or deletes old memories
    4. Returns cleanup results

    Args:
        user_id: The user ID to clean up memories for
        policy_name: Name of the forgetting policy to use

    Returns:
        Dictionary with cleanup results
    """
    retry_count = self.request.retries
    logger.info(
        f"Memory cleanup task for user {user_id} with policy '{policy_name}' "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "user_id": user_id,
            "policy_name": policy_name,
            "attempt": retry_count + 1,
            "task_id": self.request.id,
        }
    )

    try:
        # Use synchronous memory worker service
        memory_worker = SyncMemoryWorkerService()
        try:
            results = memory_worker.cleanup_user_memories_sync(
                user_id=user_id,
                policy_name=policy_name
            )

            logger.info(
                f"Memory cleanup completed for user {user_id}: {results}"
            )

            return {
                "status": "completed",
                "user_id": user_id,
                "policy_name": policy_name,
                **results,
            }
        finally:
            memory_worker.close()

    except SoftTimeLimitExceeded:
        logger.error(
            f"Memory cleanup task timed out for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        raise RetryableError("Task timed out")

    except TimeLimitExceeded:
        logger.error(
            f"Memory cleanup task hard timeout for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        return {
            "status": "timeout",
            "user_id": user_id,
            "policy_name": policy_name,
            "error": "Task exceeded hard time limit"
        }

    except Exception as e:
        logger.error(
            f"Memory cleanup task failed for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "policy_name": policy_name,
                "error": str(e),
                "attempt": retry_count + 1,
                "task_id": self.request.id,
            }
        )
        raise RetryableError(f"Memory cleanup failed: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=5 * 60,  # 5 minutes soft timeout
    time_limit=10 * 60,  # 10 minutes hard timeout
)
def behavior_aggregation_task(
    self,
    user_id: str,
    time_range_days: int = 30
) -> dict:
    """
    Celery task to aggregate behavioral data for a user.

    This task:
    1. Initializes the Memory Manager
    2. Retrieves behavioral memories for the time range
    3. Analyzes patterns and generates summary
    4. Stores aggregated behavioral summary

    Args:
        user_id: The user ID to aggregate behavior for
        time_range_days: Number of days to look back (default: 30)

    Returns:
        Dictionary with behavioral summary
    """
    retry_count = self.request.retries
    logger.info(
        f"Behavior aggregation task for user {user_id} "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "user_id": user_id,
            "time_range_days": time_range_days,
            "attempt": retry_count + 1,
            "task_id": self.request.id,
        }
    )

    try:
        # Use synchronous memory worker service
        memory_worker = SyncMemoryWorkerService()
        try:
            summary = memory_worker.get_behavior_summary_sync(
                user_id=user_id,
                time_range_days=time_range_days
            )

            logger.info(
                f"Behavior aggregation completed for user {user_id}: "
                f"{summary.get('total_behavioral_events', 0)} events analyzed"
            )

            return {
                "status": "completed",
                "user_id": user_id,
                "time_range_days": time_range_days,
                "summary": summary,
            }
        finally:
            memory_worker.close()

    except SoftTimeLimitExceeded:
        logger.error(
            f"Behavior aggregation task timed out for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        raise RetryableError("Task timed out")

    except TimeLimitExceeded:
        logger.error(
            f"Behavior aggregation task hard timeout for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        return {
            "status": "timeout",
            "user_id": user_id,
            "time_range_days": time_range_days,
            "error": "Task exceeded hard time limit"
        }

    except Exception as e:
        logger.error(
            f"Behavior aggregation task failed for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "time_range_days": time_range_days,
                "error": str(e),
                "attempt": retry_count + 1,
                "task_id": self.request.id,
            }
        )
        raise RetryableError(f"Behavior aggregation failed: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=3 * 60,  # 3 minutes soft timeout
    time_limit=5 * 60,  # 5 minutes hard timeout
)
def memory_summarization_task(
    self,
    user_id: str,
    memory_id: str
) -> dict:
    """
    Celery task to summarize a specific memory.

    This task:
    1. Initializes the Memory Manager
    2. Retrieves the memory by ID
    3. Generates a summary
    4. Returns the summary

    Args:
        user_id: The user ID who owns the memory
        memory_id: The memory ID to summarize

    Returns:
        Dictionary with the memory summary
    """
    retry_count = self.request.retries
    logger.info(
        f"Memory summarization task for memory {memory_id} "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "user_id": user_id,
            "memory_id": memory_id,
            "attempt": retry_count + 1,
            "task_id": self.request.id,
        }
    )

    try:
        # Use synchronous memory worker service
        memory_worker = SyncMemoryWorkerService()
        try:
            summary = memory_worker.summarize_memory_sync(
                memory_id=memory_id,
                user_id=user_id
            )

            if not summary:
                logger.warning(f"Memory {memory_id} not found or summarization failed")
                return {
                    "status": "failed",
                    "user_id": user_id,
                    "memory_id": memory_id,
                    "error": "Memory not found or summarization failed"
                }

            logger.info(f"Memory summarization completed for memory {memory_id}")

            return {
                "status": "completed",
                "user_id": user_id,
                "memory_id": memory_id,
                "summary": summary,
            }
        finally:
            memory_worker.close()

    except SoftTimeLimitExceeded:
        logger.error(
            f"Memory summarization task timed out for memory {memory_id}",
            extra={"user_id": user_id, "memory_id": memory_id, "task_id": self.request.id}
        )
        raise RetryableError("Task timed out")

    except TimeLimitExceeded:
        logger.error(
            f"Memory summarization task hard timeout for memory {memory_id}",
            extra={"user_id": user_id, "memory_id": memory_id, "task_id": self.request.id}
        )
        return {
            "status": "timeout",
            "user_id": user_id,
            "memory_id": memory_id,
            "error": "Task exceeded hard time limit"
        }

    except Exception as e:
        logger.error(
            f"Memory summarization task failed for memory {memory_id}: {e}",
            extra={
                "user_id": user_id,
                "memory_id": memory_id,
                "error": str(e),
                "attempt": retry_count + 1,
                "task_id": self.request.id,
            }
        )
        raise RetryableError(f"Memory summarization failed: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=10 * 60,  # 10 minutes soft timeout
    time_limit=15 * 60,  # 15 minutes hard timeout
)
def memory_forgetting_task(
    self,
    user_id: str,
    policy_name: str = "default"
) -> dict:
    """
    Celery task to apply forgetting policy to user memories.

    This task:
    1. Initializes the Memory Manager
    2. Applies the specified forgetting policy
    3. Archives, compresses, or deletes old memories
    4. Returns forgetting results

    Args:
        user_id: The user ID to apply forgetting policy for
        policy_name: Name of the forgetting policy to use

    Returns:
        Dictionary with forgetting results
    """
    retry_count = self.request.retries
    logger.info(
        f"Memory forgetting task for user {user_id} with policy '{policy_name}' "
        f"(attempt {retry_count + 1}/{self.max_retries + 1})",
        extra={
            "user_id": user_id,
            "policy_name": policy_name,
            "attempt": retry_count + 1,
            "task_id": self.request.id,
        }
    )

    try:
        # Use synchronous memory worker service
        memory_worker = SyncMemoryWorkerService()
        try:
            results = memory_worker.cleanup_user_memories_sync(
                user_id=user_id,
                policy_name=policy_name
            )

            logger.info(
                f"Memory forgetting completed for user {user_id}: {results}"
            )

            return {
                "status": "completed",
                "user_id": user_id,
                "policy_name": policy_name,
                **results,
            }
        finally:
            memory_worker.close()

    except SoftTimeLimitExceeded:
        logger.error(
            f"Memory forgetting task timed out for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        raise RetryableError("Task timed out")

    except TimeLimitExceeded:
        logger.error(
            f"Memory forgetting task hard timeout for user {user_id}",
            extra={"user_id": user_id, "task_id": self.request.id}
        )
        return {
            "status": "timeout",
            "user_id": user_id,
            "policy_name": policy_name,
            "error": "Task exceeded hard time limit"
        }

    except Exception as e:
        logger.error(
            f"Memory forgetting task failed for user {user_id}: {e}",
            extra={
                "user_id": user_id,
                "policy_name": policy_name,
                "error": str(e),
                "attempt": retry_count + 1,
                "task_id": self.request.id,
            }
        )
        raise RetryableError(f"Memory forgetting failed: {e}")
