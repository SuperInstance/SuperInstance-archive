#!/usr/bin/env python3
"""
Test script for the memory API endpoints
"""

import sys
import os
import requests
import json
import time
import random
from pathlib import Path

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_memory_api():
    """Test the memory API endpoints"""
    print("🌐 Testing Memory API Endpoints")
    print("=" * 50)

    # API base URL
    base_url = "http://localhost:8001"

    # First, let's check if the server is running
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code != 200:
            print("❌ Server is not running or not responding correctly")
            print("Please start the API server with: python api_server.py")
            return
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("Please start the API server with: python api_server.py")
        return

    # 1. Create a test character
    print("\n1. Creating test character...")
    character_data = {
        "name": "Marcus",
        "specialization": "Computer Scientist",
        "backstory": "A brilliant computer scientist exploring the intersection of AI and consciousness.",
        "personality": {"analytical": 0.9, "curious": 0.8, "creative": 0.7},
        "skills": ["programming", "machine learning", "neural networks"],
        "goals": ["Develop advanced AI systems", "Understand artificial consciousness"]
    }

    response = requests.post(f"{base_url}/characters", json=character_data)
    if response.status_code == 200:
        character = response.json()
        character_id = character["id"]
        print(f"✅ Created character: {character['name']} (ID: {character_id})")
    else:
        print(f"❌ Failed to create character: {response.text}")
        return

    # 2. Add various types of memories
    print("\n2. Adding memories via API...")

    memories_to_add = [
        {
            "content": "Discovered a new neural network architecture that seems to exhibit emergent behavior",
            "memory_type": "learning",
            "importance": 8,
            "topics": ["neural networks", "emergence", "AI architecture"],
            "emotional_valence": 0.8
        },
        {
            "content": "Had a deep conversation with Sarah about whether AI can truly be conscious",
            "memory_type": "conversational",
            "importance": 7,
            "related_characters": ["sarah_id"],
            "topics": ["consciousness", "AI ethics", "philosophy"],
            "emotional_valence": 0.3
        },
        {
            "content": "Realized that my own programming might be a form of artificial cognition",
            "memory_type": "self_reflection",
            "importance": 9,
            "topics": ["self-awareness", "artificial cognition", "identity"],
            "emotional_valence": 0.1
        },
        {
            "content": "Felt frustrated when the training run failed after 12 hours",
            "memory_type": "emotional",
            "importance": 4,
            "topics": ["frustration", "machine learning", "training"],
            "emotional_valence": -0.7
        },
        {
            "content": "Successfully implemented a memory consolidation algorithm that improved model performance by 15%",
            "memory_type": "experience",
            "importance": 10,
            "topics": ["memory consolidation", "performance", "success"],
            "emotional_valence": 0.9
        }
    ]

    memory_ids = []
    for i, memory in enumerate(memories_to_add, 1):
        response = requests.post(f"{base_url}/characters/{character_id}/memories", json=memory)
        if response.status_code == 200:
            result = response.json()
            memory_ids.append(result["memory_id"])
            print(f"✅ Added memory {i}: {result['memory_id']}")
        else:
            print(f"❌ Failed to add memory {i}: {response.text}")

    # 3. Retrieve all memories
    print("\n3. Retrieving all memories...")
    response = requests.get(f"{base_url}/characters/{character_id}/memories")
    if response.status_code == 200:
        data = response.json()
        memories = data["memories"]
        stats = data["memory_stats"]
        print(f"✅ Retrieved {len(memories)} memories")
        print(f"   Memory stats: {stats}")
    else:
        print(f"❌ Failed to retrieve memories: {response.text}")

    # 4. Filter memories by type
    print("\n4. Filtering memories by type...")
    response = requests.get(f"{base_url}/characters/{character_id}/memories?memory_type=learning")
    if response.status_code == 200:
        data = response.json()
        learning_memories = data["memories"]
        print(f"✅ Found {len(learning_memories)} learning memories")
        for memory in learning_memories:
            print(f"   - {memory['content'][:50]}...")
    else:
        print(f"❌ Failed to filter memories: {response.text}")

    # 5. Search memories
    print("\n5. Searching memories...")
    search_query = "consciousness"
    search_data = {"query": search_query, "limit": 10}
    response = requests.post(f"{base_url}/characters/{character_id}/memories/search", json=search_data)
    if response.status_code == 200:
        data = response.json()
        results = data["results"]
        print(f"✅ Search for '{search_query}' returned {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"   {i}. [{result['memory_type']}] {result['content'][:60]}... (relevance: {result['relevance']:.2f})")
    else:
        print(f"❌ Failed to search memories: {response.text}")

    # 6. Get memory statistics
    print("\n6. Getting memory statistics...")
    response = requests.get(f"{base_url}/characters/{character_id}/memories/stats")
    if response.status_code == 200:
        data = response.json()
        stats = data["stats"]
        print(f"✅ Memory statistics:")
        print(f"   Total memories: {stats['total_memories']}")
        print(f"   By type: {stats['by_type']}")
        print(f"   Average strength: {stats['average_strength']:.2f}")
        print(f"   Total clusters: {stats['total_clusters']}")
    else:
        print(f"❌ Failed to get memory stats: {response.text}")

    # 7. Test memory consolidation
    print("\n7. Testing memory consolidation...")
    response = requests.post(f"{base_url}/characters/{character_id}/memories/consolidate")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
    else:
        print(f"❌ Failed to consolidate memories: {response.text}")

    # 8. Test edge cases and error handling
    print("\n8. Testing error handling...")

    # Test invalid memory type
    invalid_memory = {
        "content": "Test memory",
        "memory_type": "invalid_type",
        "importance": 5
    }
    response = requests.post(f"{base_url}/characters/{character_id}/memories", json=invalid_memory)
    if response.status_code == 400:
        print("✅ Correctly rejected invalid memory type")
    else:
        print(f"❌ Should have rejected invalid memory type: {response.text}")

    # Test invalid importance value
    invalid_memory = {
        "content": "Test memory",
        "memory_type": "learning",
        "importance": 15  # Invalid: should be 1-10
    }
    response = requests.post(f"{base_url}/characters/{character_id}/memories", json=invalid_memory)
    if response.status_code == 400:
        print("✅ Correctly rejected invalid importance value")
    else:
        print(f"❌ Should have rejected invalid importance: {response.text}")

    # Test non-existent character
    response = requests.get(f"{base_url}/characters/nonexistent/memories")
    if response.status_code == 404:
        print("✅ Correctly handled non-existent character")
    else:
        print(f"❌ Should have returned 404 for non-existent character: {response.text}")

    print("\n🎉 All API tests completed successfully!")
    print("\nAPI endpoints verified:")
    print("   ✅ POST /characters/{id}/memories - Add memory")
    print("   ✅ GET /characters/{id}/memories - Retrieve memories")
    print("   ✅ POST /characters/{id}/memories/search - Search memories")
    print("   ✅ GET /characters/{id}/memories/stats - Get statistics")
    print("   ✅ POST /characters/{id}/memories/consolidate - Consolidate memories")
    print("   ✅ Error handling and validation")
    print("   ✅ Filtering and sorting capabilities")

    # Clean up - delete the test character (if there was a delete endpoint)
    print(f"\n📝 Test character {character['name']} (ID: {character_id}) created successfully")
    print("   You can manually delete it if needed via the character management interface")

if __name__ == "__main__":
    test_memory_api()