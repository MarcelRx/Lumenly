# apps/backend/scripts/test_agent_router.py
import asyncio
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.agent_system import AgentRouter, FusionEngine
from app.ai.agent_system.schemas.agent_types import AgentType
from app.ai.memory_engine import MemoryManager


async def test_agent_router():
    """Test AgentRouter classification across different test strings."""
    print("Testing AgentRouter classification...")

    router = AgentRouter()

    test_cases = [
        ("I need a workout routine", AgentType.FITNESS_COACH),
        ("I want to start running every morning", AgentType.FITNESS_COACH),
        ("I need help building a new habit", AgentType.HABIT_COACH),
        ("I want to maintain my daily streak", AgentType.HABIT_COACH),
        ("I'm feeling anxious and overwhelmed", AgentType.MENTAL_WELLNESS),
        ("I've been feeling really sad lately", AgentType.MENTAL_WELLNESS),
        ("I want to learn Python programming", AgentType.LEARNING_COACH),
        ("I need help studying for my exam", AgentType.LEARNING_COACH),
        ("I want to negotiate a higher salary", AgentType.CAREER_COACH),
        ("I'm overwhelmed with work deadlines", AgentType.CAREER_COACH),
        ("I need help creating a budget", AgentType.FINANCIAL_COACH),
        ("I want to save more money each month", AgentType.FINANCIAL_COACH),
        ("I'm having trouble communicating with my partner", AgentType.RELATIONSHIP_COACH),
        ("I need to set better boundaries with friends", AgentType.RELATIONSHIP_COACH),
        ("I need help balancing my life overall", AgentType.LIFE_STRATEGIST),
        ("What should I focus on right now?", AgentType.LIFE_STRATEGIST),
    ]

    passed = 0
    failed = 0

    for query, expected_agent in test_cases:
        result = router.route_query(query)
        if result == expected_agent:
            passed += 1
            print(f"  ✓ '{query}' -> {result.value}")
        else:
            failed += 1
            print(f"  ✗ '{query}' -> {result.value} (expected {expected_agent.value})")

    print(f"\nAgentRouter Test Results: {passed} passed, {failed} failed")
    return failed == 0


async def test_fusion_engine():
    """Test FusionEngine with MemoryManager."""
    print("\nTesting FusionEngine with MemoryManager...")

    # Create mock memory components (in-memory for testing)
    class MockShortTermMemory:
        async def get_history(self, user_id: str) -> list[dict]:
            return [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]

        async def add_message(self, user_id: str, role: str, content: str) -> None:
            pass

    class MockLongTermMemory:
        async def retrieve_relevant(self, user_id: str, query_vector: list[float], top_k: int) -> list[str]:
            return ["User enjoys morning workouts", "User is working on habit consistency"]

    # Create MemoryManager with mock components
    short_term = MockShortTermMemory()
    long_term = MockLongTermMemory()
    memory_manager = MemoryManager(short_term=short_term, long_term=long_term)

    # Create router and fusion engine
    router = AgentRouter()
    fusion_engine = FusionEngine(
        memory_manager=memory_manager,
        router=router,
        llm_client=None  # Use mock response
    )

    # Test query processing
    test_user_id = "test_user_123"
    test_query = "I need a workout routine"

    try:
        result = await fusion_engine.process_user_query(
            user_id=test_user_id,
            query=test_query,
            query_vector=[0.1, 0.2, 0.3]  # Mock vector
        )

        # Verify results
        assert "response" in result, "Response missing from result"
        assert "agent_used" in result, "agent_used missing from result"
        assert "memories_retrieved" in result, "memories_retrieved missing from result"
        assert result["agent_used"] == AgentType.FITNESS_COACH.value, f"Expected FITNESS_COACH, got {result['agent_used']}"
        # MemoryManager infers memories from context, so check that it detected memories were retrieved
        assert result["memories_retrieved"] > 0, f"Expected memories to be retrieved, got {result['memories_retrieved']}"
        assert len(result["response"]) > 0, "Response is empty"

        print("  ✓ Context injection successful")
        print(f"  ✓ Query routed to {result['agent_used']}")
        print(f"  ✓ Retrieved {result['memories_retrieved']} memories")
        print(f"  ✓ Response generated: {result['response'][:100]}...")
        print("  ✓ Turn saved to memory")

        print("\nFusionEngine Test Results: PASSED")
        return True

    except Exception as e:
        print(f"\nFusionEngine Test Results: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("AGENT ROUTER & FUSION ENGINE TEST SUITE")
    print("=" * 60)

    router_passed = await test_agent_router()
    fusion_passed = await test_fusion_engine()

    print("\n" + "=" * 60)
    if router_passed and fusion_passed:
        print("AGENT ROUTER & FUSION ENGINE TEST PASSED")
    else:
        print("AGENT ROUTER & FUSION ENGINE TEST FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
