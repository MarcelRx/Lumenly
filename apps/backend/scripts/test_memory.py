#!/usr/bin/env python3
"""
Memory Engine Verification Script

Tests the short-term and long-term memory functionality.
"""
import asyncio
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ai.memory_engine import LongTermMemory, ShortTermMemory
from app.db.qdrant import close_qdrant, get_qdrant_client, init_qdrant
from app.db.redis import close_redis, get_redis_client, init_redis
from app.core.config import settings


async def test_short_term_memory():
    """Test short-term memory with Redis."""
    print("Testing Short-Term Memory (Redis)...")

    redis_client = get_redis_client()
    short_term = ShortTermMemory(redis_client)

    test_user_id = "test_user_123"

    # Save 2 conversation turns
    await short_term.add_message(test_user_id, "user", "Hello, how are you?")
    await short_term.add_message(test_user_id, "assistant", "I'm doing great, thanks for asking!")
    await short_term.add_message(test_user_id, "user", "What's the weather like?")
    await short_term.add_message(test_user_id, "assistant", "I don't have access to real-time weather data.")

    # Retrieve history
    history = await short_term.get_history(test_user_id)

    # Verify
    assert len(history) == 4, f"Expected 4 messages, got {len(history)}"
    assert history[0]["role"] == "user", "First message should be from user"
    assert history[0]["content"] == "Hello, how are you?", "First message content mismatch"
    assert history[1]["role"] == "assistant", "Second message should be from assistant"

    print(f"✓ Short-term memory test passed: {len(history)} messages retrieved")

    # Cleanup
    await redis_client.delete(f"chat_history:{test_user_id}")
    print("✓ Cleaned up test data from Redis")


async def test_long_term_memory():
    """Test long-term memory with Qdrant."""
    print("\nTesting Long-Term Memory (Qdrant)...")

    qdrant_client = get_qdrant_client()
    long_term = LongTermMemory(qdrant_client, vector_size=settings.VECTOR_DIMENSION)

    test_user_id = "test_user_123"

    # Create a sample vector
    sample_vector = [0.1] * settings.VECTOR_DIMENSION

    # Save a memory
    await long_term.save_memory(
        user_id=test_user_id,
        text="The user prefers Python over JavaScript for backend development.",
        vector=sample_vector,
        category="preferences"
    )

    # Retrieve relevant memories
    retrieved = await long_term.retrieve_relevant(
        user_id=test_user_id,
        query_vector=sample_vector,
        top_k=3
    )

    # Verify
    assert len(retrieved) >= 1, f"Expected at least 1 memory, got {len(retrieved)}"
    assert "Python" in retrieved[0], "Retrieved memory should contain 'Python'"

    print(f"✓ Long-term memory test passed: {len(retrieved)} memories retrieved")
    print(f"  Retrieved: {retrieved[0][:50]}...")

    # Cleanup - delete the test point
    from qdrant_client.models import FieldCondition, Filter, MatchValue
    filter_ = Filter(
        must=[FieldCondition(key="user_id", match=MatchValue(value=test_user_id))]
    )
    # FIX: Use points_selector instead of query_filter
    await qdrant_client.delete(
        collection_name="user_long_term_memory",
        points_selector=filter_
    )
    print("✓ Cleaned up test data from Qdrant")


async def main():
    """Run all memory engine tests."""
    print("=" * 60)
    print("Memory Engine Verification Test")
    print("=" * 60)

    try:
        # Initialize connections
        print("\nInitializing connections...")
        redis_ok = await init_redis()
        if not redis_ok:
            print("✗ Failed to connect to Redis")
            return False

        qdrant_ok = await init_qdrant()
        if not qdrant_ok:
            print("✗ Failed to connect to Qdrant")
            return False

        print("✓ Connections initialized successfully")

        # Run tests
        await test_short_term_memory()
        await test_long_term_memory()

        # Close connections
        await close_redis()
        await close_qdrant()

        print("\n" + "=" * 60)
        print("MEMORY ENGINE TEST PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
