#!/usr/bin/env python3
"""
Knowledge Brain Verification Script

Tests the document chunking, ingestion, and retrieval functionality.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.qdrant import init_qdrant, close_qdrant, get_qdrant_client
from app.ai.knowledge_brain import KnowledgeIngestor, KnowledgeRetriever


async def mock_embed_func(text: str) -> list[float]:
    """
    Mock embedding function for testing.
    Returns a fixed vector based on text length to simulate different embeddings.
    """
    # Create a deterministic vector based on text length
    # This is just for testing - in production, use a real embedding model
    base = [0.1] * 768
    # Modify slightly based on text to create different vectors
    modifier = (len(text) % 100) / 100.0
    return [x + modifier for x in base]


async def test_knowledge_brain():
    """Test the knowledge brain pipeline."""
    print("=" * 60)
    print("Knowledge Brain Verification Test")
    print("=" * 60)

    try:
        # Initialize Qdrant connection
        print("\nInitializing Qdrant connection...")
        qdrant_ok = await init_qdrant()
        if not qdrant_ok:
            print("✗ Failed to connect to Qdrant")
            return False

        print("✓ Qdrant connection initialized")

        qdrant_client = get_qdrant_client()

        # Create mock document text (simulating Atomic Habits Chapter 1)
        mock_text = """
        Atomic Habits Chapter 1: The aggregation of marginal gains
        
        The fate of British Cycling changed one day in 2003. The organization, which was the governing body for professional cycling in Great Britain, had recently hired Dave Brailsford as its new performance director. At the time, professional cyclists in Great Britain had endured nearly one hundred years of mediocrity. In fact, they had won just a single gold medal at the Olympic Games since 1908, and they had never won the Tour de France.
        
        Brailsford had been hired to put British Cycling on a new trajectory. What made him different from previous coaches was his relentless commitment to a strategy that he referred to as the aggregation of marginal gains. The whole principle came from the idea that if you broke down everything you could think of that goes into riding a bike, and then improved it by 1 percent, you will get a significant increase when you put them all together.
        
        Brailsford believed in the power of small improvements. He didn't focus on one big transformation. Instead, he searched for tiny margins of improvement in everything they did. He redesigned the bike seats to make them more comfortable. He rubbed the tires with alcohol to improve grip. He tested different fabrics in wind tunnels to see which one had the least drag. He even had the athletes wash their hands with hot water to prevent infections that could lead to illness.
        
        The results were stunning. In the five years after Brailsford took over, the British cycling team won 66 Olympic and Paralympic gold medals and 5 Tour de France victories. They dominated the sport in a way that had never been seen before.
        
        This is the central thesis of this book: small habits can lead to remarkable results. The aggregation of marginal gains is not just about cycling—it's about life. By making tiny improvements in our daily habits, we can achieve extraordinary outcomes over time.
        """

        test_user_id = "test_user_123"
        document_title = "Atomic Habits - Chapter 1"

        print(f"\nProcessing document: {document_title}")
        print(f"Document length: {len(mock_text)} characters")

        # Initialize KnowledgeIngestor and process the document
        ingestor = KnowledgeIngestor(qdrant_client, mock_embed_func)
        await ingestor.process_and_store_document(
            user_id=test_user_id,
            document_title=document_title,
            text=mock_text
        )
        print("✓ Document processed and stored successfully")

        # Initialize KnowledgeRetriever and search for a concept
        retriever = KnowledgeRetriever(qdrant_client, mock_embed_func)

        # Search for "marginal gains" concept
        search_query = "marginal gains"
        print(f"\nSearching for concept: '{search_query}'")

        results = await retriever.search_knowledge(
            user_id=test_user_id,
            query=search_query,
            top_k=3
        )

        print(f"✓ Retrieved {len(results)} chunks")

        # Verify that at least one result contains the expected concept
        found_concept = False
        for i, result in enumerate(results):
            chunk_text = result["chunk_text"]
            if "marginal gains" in chunk_text.lower():
                found_concept = True
                print(f"✓ Found concept in chunk {i + 1}")
                print(f"  Document: {result['document_title']}")
                print(f"  Score: {result['score']:.4f}")
                print(f"  Preview: {chunk_text[:100]}...")
                break

        assert found_concept, f"Expected concept 'marginal gains' not found in any retrieved chunk"

        # Cleanup - delete test points
        print(f"\nCleaning up test data for user: {test_user_id}")
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        filter_ = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=test_user_id))]
        )

        await qdrant_client.delete(
            collection_name="knowledge_base",
            points_selector=filter_
        )
        print("✓ Cleaned up test data from Qdrant")

        # Close connection
        await close_qdrant()

        print("\n" + "=" * 60)
        print("KNOWLEDGE BRAIN TEST PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_knowledge_brain())
    sys.exit(0 if success else 1)
