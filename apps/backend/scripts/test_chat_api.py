#!/usr/bin/env python3
"""
Verification script for the FusionEngine Chat API.

This script tests the /api/chat endpoint using FastAPI's TestClient.
It sends a sample request and verifies the response structure.
"""
import asyncio
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from app.db.qdrant import init_qdrant
from app.db.redis import init_redis
from app.main import app


async def initialize_dependencies():
    """Initialize Redis and Qdrant for testing."""
    print("Initializing dependencies...")
    await init_redis()
    await init_qdrant()
    print("Dependencies initialized")


client = TestClient(app)


def test_chat_api():
    """
    Test the chat API endpoint with a sample prompt.

    This test:
    - Sends a POST request to /api/chat
    - Verifies 200 OK status code
    - Checks that response contains agent_used field
    - Verifies response contains a valid response string
    """
    print("Testing Chat API Pipeline...")

    # Initialize dependencies
    asyncio.run(initialize_dependencies())

    # Prepare test request
    test_request = {
        "user_id": "test_user_123",
        "message": "I need help building a new morning habit"
    }

    print(f"Sending request: {test_request}")

    # Send POST request to /api/chat
    response = client.post("/api/chat", json=test_request)

    # Check status code
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    print(f"✓ Status code: {response.status_code}")

    # Parse response
    response_data = response.json()
    print(f"Response data: {response_data}")

    # Verify response structure
    assert "response" in response_data, "Response missing 'response' field"
    assert "agent_used" in response_data, "Response missing 'agent_used' field"
    assert "memories_retrieved" in response_data, "Response missing 'memories_retrieved' field"
    assert "knowledge_snippets_used" in response_data, "Response missing 'knowledge_snippets_used' field"
    print("✓ Response contains all required fields")

    # Verify agent_used is a valid string
    agent_used = response_data["agent_used"]
    assert isinstance(agent_used, str), "agent_used should be a string"
    assert len(agent_used) > 0, "agent_used should not be empty"
    print(f"✓ Agent used: {agent_used}")

    # Verify response is a valid string
    response_text = response_data["response"]
    assert isinstance(response_text, str), "response should be a string"
    assert len(response_text) > 0, "response should not be empty"
    print(f"✓ Response text length: {len(response_text)} characters")

    # Verify memories_retrieved is an integer
    memories_retrieved = response_data["memories_retrieved"]
    assert isinstance(memories_retrieved, int), "memories_retrieved should be an integer"
    print(f"✓ Memories retrieved: {memories_retrieved}")

    # Verify knowledge_snippets_used is an integer
    knowledge_snippets_used = response_data["knowledge_snippets_used"]
    assert isinstance(knowledge_snippets_used, int), "knowledge_snippets_used should be an integer"
    print(f"✓ Knowledge snippets used: {knowledge_snippets_used}")

    print("\n" + "="*50)
    print("CHAT API PIPELINE TEST PASSED")
    print("="*50)


if __name__ == "__main__":
    try:
        test_chat_api()
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
