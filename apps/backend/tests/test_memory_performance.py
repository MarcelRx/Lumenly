# apps/backend/tests/test_memory_performance.py
"""
Performance tests for Memory Intelligence Core.

These tests focus on performance aspects:
- Memory storage throughput
- Retrieval latency with various dataset sizes
- Ranking algorithm performance
- Concurrent operation handling
- Resource usage optimization
"""
import asyncio
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from app.ai.memory import (
    MemoryImportance,
    MemoryManager,
    MemoryMetadata,
    MemoryRanker,
    MemoryRecord,
    MemoryType,
    MultiBackendMemoryStorage,
)


class TestMemoryStoragePerformance:
    """Test memory storage performance."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage with timing."""
        storage = Mock(spec=MultiBackendMemoryStorage)

        async def timed_store(memory):
            start = time.time()
            await asyncio.sleep(0.001)  # Simulate storage delay
            return "test_id"

        storage.store = timed_store
        storage.retrieve = AsyncMock()
        storage.list_user_memories = AsyncMock(return_value=[])
        storage.count_user_memories = AsyncMock(return_value=0)

        return storage

    @pytest.mark.asyncio
    async def test_storage_throughput(self, mock_storage):
        """Test memory storage throughput (memories per second)."""
        manager = MemoryManager(storage=mock_storage)

        num_memories = 100
        start_time = time.time()

        for i in range(num_memories):
            await manager.store_memory(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Test content {i}",
            )

        elapsed = time.time() - start_time
        throughput = num_memories / elapsed

        print(f"Storage throughput: {throughput:.2f} memories/second")
        assert throughput > 10  # Should handle at least 10 memories/second

    @pytest.mark.asyncio
    async def test_batch_storage_performance(self, mock_storage):
        """Test batch storage performance."""
        manager = MemoryManager(storage=mock_storage)

        num_memories = 50
        start_time = time.time()

        # Store memories concurrently
        tasks = [
            manager.store_memory(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Test content {i}",
            )
            for i in range(num_memories)
        ]

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        throughput = num_memories / elapsed

        print(f"Batch storage throughput: {throughput:.2f} memories/second")
        assert throughput > 20  # Concurrent should be faster


class TestMemoryRetrievalPerformance:
    """Test memory retrieval performance."""

    @pytest.fixture
    def sample_memories(self):
        """Create a large sample of memories for testing."""
        memories = []
        for i in range(100):
            metadata = MemoryMetadata(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.MEDIUM,
                access_count=i % 10,
                created_at=datetime.now(UTC) - timedelta(days=i % 30),
            )

            memory = MemoryRecord(
                id=f"memory_{i}",
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Test content {i} with some text to simulate real data",
                metadata=metadata,
                embedding_vector=[0.1 * (i % 10), 0.2 * (i % 10), 0.3 * (i % 10), 0.4 * (i % 10)],
            )
            memories.append(memory)

        return memories

    @pytest.mark.asyncio
    async def test_retrieval_latency_small_dataset(self, sample_memories):
        """Test retrieval latency with small dataset."""
        ranker = MemoryRanker()

        start_time = time.time()
        results = await ranker.rank(sample_memories[:10], "test query")
        elapsed = time.time() - start_time

        print(f"Small dataset retrieval latency: {elapsed*1000:.2f}ms")
        assert elapsed < 0.1  # Should complete within 100ms

    @pytest.mark.asyncio
    async def test_retrieval_latency_medium_dataset(self, sample_memories):
        """Test retrieval latency with medium dataset."""
        ranker = MemoryRanker()

        start_time = time.time()
        results = await ranker.rank(sample_memories[:50], "test query")
        elapsed = time.time() - start_time

        print(f"Medium dataset retrieval latency: {elapsed*1000:.2f}ms")
        assert elapsed < 0.5  # Should complete within 500ms

    @pytest.mark.asyncio
    async def test_retrieval_latency_large_dataset(self, sample_memories):
        """Test retrieval latency with large dataset."""
        ranker = MemoryRanker()

        start_time = time.time()
        results = await ranker.rank(sample_memories, "test query")
        elapsed = time.time() - start_time

        print(f"Large dataset retrieval latency: {elapsed*1000:.2f}ms")
        assert elapsed < 1.0  # Should complete within 1 second


class TestMemoryRankingPerformance:
    """Test memory ranking algorithm performance."""

    @pytest.fixture
    def ranker(self):
        """Create a MemoryRanker instance."""
        return MemoryRanker()

    @pytest.fixture
    def large_memory_set(self):
        """Create a large set of memories for ranking tests."""
        from app.core.config import settings
        memories = []
        for i in range(500):
            metadata = MemoryMetadata(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.MEDIUM,
                access_count=i % 20,
                created_at=datetime.now(UTC) - timedelta(days=i % 365),
            )

            memory = MemoryRecord(
                id=f"memory_{i}",
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Test content {i} " * 10,  # Longer content
                metadata=metadata,
                embedding_vector=[0.01 * j for j in range(settings.VECTOR_DIMENSION)],  # Full embedding
            )
            memories.append(memory)

        return memories

    @pytest.mark.asyncio
    async def test_importance_scoring_performance(self, ranker, large_memory_set):
        """Test importance scoring performance."""
        start_time = time.time()

        for memory in large_memory_set[:100]:
            await ranker.calculate_importance_score(memory)

        elapsed = time.time() - start_time
        avg_time = elapsed / 100

        print(f"Average importance scoring time: {avg_time*1000:.2f}ms")
        assert avg_time < 0.01  # Should be very fast

    @pytest.mark.asyncio
    async def test_recency_scoring_performance(self, ranker, large_memory_set):
        """Test recency scoring performance."""
        start_time = time.time()

        for memory in large_memory_set[:100]:
            await ranker.calculate_recency_score(memory)

        elapsed = time.time() - start_time
        avg_time = elapsed / 100

        print(f"Average recency scoring time: {avg_time*1000:.2f}ms")
        assert avg_time < 0.01  # Should be very fast

    @pytest.mark.asyncio
    async def test_semantic_similarity_performance(self, ranker, large_memory_set):
        """Test semantic similarity calculation performance."""
        query_vector = [0.01 * i for i in range(384)]

        start_time = time.time()

        for memory in large_memory_set[:100]:
            await ranker.calculate_semantic_similarity(memory, query_vector)

        elapsed = time.time() - start_time
        avg_time = elapsed / 100

        print(f"Average semantic similarity time: {avg_time*1000:.2f}ms")
        assert avg_time < 0.05  # Should be reasonably fast

    @pytest.mark.asyncio
    async def test_full_ranking_performance(self, ranker, large_memory_set):
        """Test full ranking pipeline performance."""
        start_time = time.time()

        results = await ranker.rank(large_memory_set, "test query")

        elapsed = time.time() - start_time

        print(f"Full ranking for {len(large_memory_set)} memories: {elapsed*1000:.2f}ms")
        assert elapsed < 2.0  # Should complete within 2 seconds
        assert len(results) == len(large_memory_set)


class TestConcurrentOperations:
    """Test concurrent operation handling."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage."""
        storage = Mock(spec=MultiBackendMemoryStorage)
        storage.store = AsyncMock(return_value="test_id")
        storage.retrieve = AsyncMock()
        storage.list_user_memories = AsyncMock(return_value=[])
        storage.count_user_memories = AsyncMock(return_value=0)
        return storage

    @pytest.mark.asyncio
    async def test_concurrent_storage(self, mock_storage):
        """Test concurrent memory storage operations."""
        manager = MemoryManager(storage=mock_storage)

        num_concurrent = 20
        start_time = time.time()

        tasks = [
            manager.store_memory(
                user_id=f"user_{i % 5}",  # Distribute across 5 users
                memory_type=MemoryType.JOURNAL,
                content=f"Concurrent test {i}",
            )
            for i in range(num_concurrent)
        ]

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        print(f"Concurrent storage ({num_concurrent} ops): {elapsed*1000:.2f}ms")
        assert elapsed < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_retrieval(self, mock_storage):
        """Test concurrent memory retrieval operations."""
        manager = MemoryManager(storage=mock_storage)

        num_concurrent = 30
        start_time = time.time()

        tasks = [
            manager.retrieve_memories(
                user_id=f"user_{i % 5}",
                query=f"test query {i}",
            )
            for i in range(num_concurrent)
        ]

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        print(f"Concurrent retrieval ({num_concurrent} ops): {elapsed*1000:.2f}ms")
        assert elapsed < 2.0  # Should complete within 2 seconds


class TestMemoryScaling:
    """Test memory system scaling characteristics."""

    @pytest.mark.asyncio
    async def test_linear_scaling_storage(self):
        """Test that storage scales linearly with memory count."""
        storage = Mock(spec=MultiBackendMemoryStorage)

        async def simulated_store(memory):
            await asyncio.sleep(0.001)  # Constant time per operation
            return "test_id"

        storage.store = simulated_store

        # Test with different scales
        scales = [10, 50, 100]
        times = []

        for scale in scales:
            start_time = time.time()

            tasks = [
                storage.store(
                    MemoryRecord(
                        id=f"mem_{i}",
                        user_id="test_user",
                        memory_type=MemoryType.JOURNAL,
                        content="test",
                        metadata=MemoryMetadata(
                            user_id="test_user",
                            memory_type=MemoryType.JOURNAL,
                        ),
                    )
                )
                for i in range(scale)
            ]

            await asyncio.gather(*tasks)
            elapsed = time.time() - start_time
            times.append(elapsed)

        # Check that time scales roughly linearly
        # Time for 100 should be roughly 10x time for 10
        ratio = times[2] / times[0]
        print(f"Scaling ratio (100/10): {ratio:.2f}x")
        assert ratio < 15  # Allow some overhead but should be roughly linear


class TestMemoryResourceUsage:
    """Test memory resource usage optimization."""

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test that memory operations are memory-efficient."""
        import sys

        # Create a large memory record
        large_content = "Test content " * 1000  # ~13KB
        metadata = MemoryMetadata(
            user_id="test_user",
            memory_type=MemoryType.JOURNAL,
            tags=[f"tag_{i}" for i in range(100)],
        )

        memory = MemoryRecord(
            id="test_id",
            user_id="test_user",
            memory_type=MemoryType.JOURNAL,
            content=large_content,
            metadata=metadata,
            embedding_vector=[0.01 * i for i in range(384)],
        )

        # Check memory size
        memory_size = sys.getsizeof(memory.content) + sys.getsizeof(memory.metadata.tags)

        print(f"Large memory content size: {memory_size / 1024:.2f}KB")
        assert memory_size < 50 * 1024  # Should be less than 50KB

    @pytest.mark.asyncio
    async def test_batch_operation_memory_efficiency(self):
        """Test that batch operations don't cause memory bloat."""
        memories = []

        # Create many memories
        for i in range(100):
            metadata = MemoryMetadata(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
            )

            memory = MemoryRecord(
                id=f"mem_{i}",
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Content {i}",
                metadata=metadata,
            )
            memories.append(memory)

        # Process batch
        ranker = MemoryRanker()
        start_time = time.time()

        results = await ranker.rank(memories, "test query")

        elapsed = time.time() - start_time

        print(f"Batch processing time: {elapsed*1000:.2f}ms")
        assert elapsed < 1.0  # Should be efficient


class TestMemoryCachingPerformance:
    """Test caching performance if implemented."""

    @pytest.mark.asyncio
    async def test_retrieval_caching(self):
        """Test that repeated retrievals benefit from caching."""
        # This tests the potential caching behavior
        # In a real implementation, we'd test actual cache hit rates

        mock_storage = Mock(spec=MultiBackendMemoryStorage)
        mock_storage.retrieve = AsyncMock()
        mock_storage.list_user_memories = AsyncMock(return_value=[])

        manager = MemoryManager(storage=mock_storage)

        # First retrieval
        start_time = time.time()
        await manager.retrieve_memories("test_user", "test query")
        first_time = time.time() - start_time

        # Second retrieval (should be faster if cached)
        start_time = time.time()
        await manager.retrieve_memories("test_user", "test query")
        second_time = time.time() - start_time

        print(f"First retrieval: {first_time*1000:.2f}ms")
        print(f"Second retrieval: {second_time*1000:.2f}ms")

        # Even without explicit caching, should be reasonably fast
        assert second_time < 1.0


class TestMemoryThroughputUnderLoad:
    """Test memory system throughput under various load conditions."""

    @pytest.mark.asyncio
    async def test_high_load_throughput(self):
        """Test throughput under high load."""
        mock_storage = Mock(spec=MultiBackendMemoryStorage)
        mock_storage.store = AsyncMock(return_value="test_id")
        mock_storage.retrieve = AsyncMock()
        mock_storage.list_user_memories = AsyncMock(return_value=[])

        manager = MemoryManager(storage=mock_storage)

        # Simulate high load
        num_operations = 200
        start_time = time.time()

        # Mix of operations
        tasks = []
        for i in range(num_operations):
            if i % 3 == 0:
                # Storage
                tasks.append(manager.store_memory(
                    user_id="test_user",
                    memory_type=MemoryType.JOURNAL,
                    content=f"Load test {i}",
                ))
            elif i % 3 == 1:
                # Retrieval
                tasks.append(manager.retrieve_memories(
                    user_id="test_user",
                    query=f"query {i}",
                ))
            else:
                # Statistics
                tasks.append(manager.get_memory_statistics("test_user"))

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time
        throughput = num_operations / elapsed

        print(f"High load throughput: {throughput:.2f} ops/second")
        assert throughput > 50  # Should handle at least 50 ops/second


class TestMemoryLatencyPercentiles:
    """Test memory operation latency percentiles."""

    @pytest.mark.asyncio
    async def test_storage_latency_distribution(self):
        """Test storage latency distribution."""
        mock_storage = Mock(spec=MultiBackendMemoryStorage)

        async def variable_storage(memory):
            # Simulate variable latency
            delay = 0.001 + (hash(memory.id) % 10) * 0.0005
            await asyncio.sleep(delay)
            return "test_id"

        mock_storage.store = variable_storage
        mock_storage.retrieve = AsyncMock()
        mock_storage.list_user_memories = AsyncMock(return_value=[])

        manager = MemoryManager(storage=mock_storage)

        latencies = []
        for i in range(50):
            start_time = time.time()
            await manager.store_memory(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Latency test {i}",
            )
            latencies.append((time.time() - start_time) * 1000)  # Convert to ms

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"P50 latency: {p50:.2f}ms")
        print(f"P95 latency: {p95:.2f}ms")
        print(f"P99 latency: {p99:.2f}ms")

        # P99 should be reasonable
        assert p99 < 50  # P99 should be under 50ms


class TestMemoryBenchmark:
    """Comprehensive memory benchmarks."""

    @pytest.mark.asyncio
    async def test_comprehensive_benchmark(self):
        """Run comprehensive memory system benchmark."""
        import tracemalloc
        from statistics import median

        mock_storage = Mock(spec=MultiBackendMemoryStorage)

        async def realistic_storage(memory):
            await asyncio.sleep(0.001)  # Optimized storage delay
            return "test_id"

        mock_storage.store = realistic_storage
        mock_storage.retrieve = AsyncMock()
        mock_storage.list_user_memories = AsyncMock(return_value=[])
        mock_storage.count_user_memories = AsyncMock(return_value=0)

        manager = MemoryManager(storage=mock_storage)
        ranker = MemoryRanker()

        # Warm-up phase
        for i in range(10):
            await manager.store_memory(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Warm-up {i}",
            )

        # Memory profiling
        tracemalloc.start()

        # Sustained load test
        storage_latencies = []
        retrieval_latencies = []
        ranking_latencies = []

        for i in range(100):
            # Storage benchmark
            start = time.time()
            await manager.store_memory(
                user_id="test_user",
                memory_type=MemoryType.JOURNAL,
                content=f"Benchmark content {i}",
            )
            storage_latencies.append((time.time() - start) * 1000)

            # Ranking benchmark
            sample_memories = []
            for j in range(10):
                metadata = MemoryMetadata(
                    user_id="test_user",
                    memory_type=MemoryType.JOURNAL,
                    importance=MemoryImportance.MEDIUM,
                    access_count=j,
                    created_at=datetime.now(UTC) - timedelta(days=j),
                )
                sample_memories.append(
                    MemoryRecord(
                        id=f"mem_{j}",
                        user_id="test_user",
                        memory_type=MemoryType.JOURNAL,
                        content=f"Content {j}",
                        metadata=metadata,
                        embedding_vector=[0.1 * k for k in range(384)],
                    )
                )

            start = time.time()
            await ranker.rank(sample_memories, "test query")
            ranking_latencies.append((time.time() - start) * 1000)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate statistics
        storage_p50 = median(storage_latencies)
        storage_p95 = sorted(storage_latencies)[int(len(storage_latencies) * 0.95)]
        storage_p99 = sorted(storage_latencies)[int(len(storage_latencies) * 0.99)]

        ranking_p50 = median(ranking_latencies)
        ranking_p95 = sorted(ranking_latencies)[int(len(ranking_latencies) * 0.95)]
        ranking_p99 = sorted(ranking_latencies)[int(len(ranking_latencies) * 0.99)]

        storage_throughput = 100 / (sum(storage_latencies) / 1000)

        print("\n=== Comprehensive Benchmark Results ===")
        print(f"Storage Throughput: {storage_throughput:.2f} ops/second")
        print(f"Storage P50: {storage_p50:.2f}ms, P95: {storage_p95:.2f}ms, P99: {storage_p99:.2f}ms")
        print(f"Ranking P50: {ranking_p50:.2f}ms, P95: {ranking_p95:.2f}ms, P99: {ranking_p99:.2f}ms")
        print(f"Memory Usage: Current {current / 1024 / 1024:.2f}MB, Peak {peak / 1024 / 1024:.2f}MB")

        # Assertions for production readiness
        assert storage_throughput > 30, f"Storage throughput {storage_throughput} below threshold"
        assert storage_p99 < 200, f"Storage P99 {storage_p99}ms exceeds threshold"
        assert ranking_p99 < 200, f"Ranking P99 {ranking_p99}ms exceeds threshold"
        assert peak < 50 * 1024 * 1024, f"Peak memory {peak} exceeds 50MB"
