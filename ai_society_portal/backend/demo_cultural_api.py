#!/usr/bin/env python3
"""
AI Society Portal - Cultural Transmission API Demo
==================================================
Demonstrates how to use the cultural transmission API endpoints.
"""

import requests
import json
import time
from typing import Dict, List


class CulturalTransmissionAPIClient:
    """Client for interacting with the cultural transmission API"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make a request to the API"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return {"error": str(e)}

    def create_character(self, name: str, specialization: str, backstory: str) -> str:
        """Create a new character"""
        data = {
            "name": name,
            "specialization": specialization,
            "backstory": backstory,
            "personality": {"curious": 0.8, "social": 0.6}
        }
        response = self._make_request("POST", "/characters", data)
        return response.get("id")

    def discover_knowledge(self, character_id: str, content: str,
                          knowledge_type: str, importance: int = 5,
                          topics: List[str] = None) -> str:
        """Character discovers new knowledge"""
        data = {
            "content": content,
            "knowledge_type": knowledge_type,
            "importance": importance,
            "topics": topics or []
        }
        response = self._make_request("POST", f"/characters/{character_id}/discover-knowledge", data)
        return response.get("knowledge_id")

    def teach_character(self, teacher_id: str, student_id: str,
                       knowledge_id: str, method: str = "direct_teaching") -> Dict:
        """Character teaches another character"""
        data = {
            "target_character_id": student_id,
            "knowledge_id": knowledge_id,
            "method": method
        }
        return self._make_request("POST", f"/characters/{teacher_id}/teach", data)

    def get_character_knowledge(self, character_id: str,
                               knowledge_type: str = None) -> List[Dict]:
        """Get character's knowledge base"""
        endpoint = f"/characters/{character_id}/knowledge"
        if knowledge_type:
            endpoint += f"?knowledge_type={knowledge_type}"
        response = self._make_request("GET", endpoint)
        return response.get("knowledge", [])

    def create_artifact(self, character_id: str, name: str, description: str,
                       embedded_knowledge_ids: List[str],
                       artifact_type: str = "document") -> str:
        """Character creates a cultural artifact"""
        data = {
            "name": name,
            "description": description,
            "embedded_knowledge_ids": embedded_knowledge_ids,
            "artifact_type": artifact_type
        }
        response = self._make_request("POST", f"/characters/{character_id}/create-artifact", data)
        return response.get("artifact_id")

    def learn_from_artifact(self, character_id: str, artifact_id: str) -> Dict:
        """Character learns from a cultural artifact"""
        data = {"artifact_id": artifact_id}
        return self._make_request("POST", f"/characters/{character_id}/learn-from-artifact", data)

    def get_cultural_stats(self) -> Dict:
        """Get cultural transmission system statistics"""
        return self._make_request("GET", "/cultural-transmission/stats")


def demo_cultural_transmission():
    """Demonstrate the cultural transmission API"""
    print("🎭 AI Society Portal - Cultural Transmission API Demo")
    print("=" * 60)

    # Initialize API client
    client = CulturalTransmissionAPIClient()

    # Check if server is running
    try:
        response = requests.get("http://localhost:8001/")
        if response.status_code != 200:
            print("❌ Server is not running. Please start the API server first:")
            print("   cd backend && python api_server.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the API server first:")
        print("   cd backend && python api_server.py")
        return

    print("✅ Connected to API server")

    # Create characters
    print("\n📝 Creating characters...")
    einstein_id = client.create_character(
        "Albert Einstein", "Physicist",
        "Revolutionized physics with theories of relativity and quantum mechanics"
    )
    print(f"  ✓ Created Einstein: {einstein_id}")

    marie_id = client.create_character(
        "Marie Curie", "Chemist",
        "Pioneered research on radioactivity and discovered two elements"
    )
    print(f"  ✓ Created Marie Curie: {marie_id}")

    confucius_id = client.create_character(
        "Confucius", "Philosopher",
        "Ancient Chinese philosopher who emphasized personal and governmental morality"
    )
    print(f"  ✓ Created Confucius: {confucius_id}")

    # Discover knowledge
    print("\n🔬 Discovering knowledge...")
    relativity_id = client.discover_knowledge(
        einstein_id,
        "The theory of relativity unifies space and time into a single continuum",
        "fact", importance=9,
        topics=["physics", "relativity", "spacetime"]
    )
    print(f"  ✓ Einstein discovered relativity: {relativity_id}")

    radioactivity_id = client.discover_knowledge(
        marie_id,
        "Radioactivity is the spontaneous emission of particles from atomic nuclei",
        "fact", importance=8,
        topics=["chemistry", "physics", "radioactivity"]
    )
    print(f"  ✓ Marie discovered radioactivity principles: {radioactivity_id}")

    golden_rule_id = client.discover_knowledge(
        confucius_id,
        "Do not impose on others what you do not wish for yourself",
        "insight", importance=10,
        topics=["ethics", "philosophy", "morality"]
    )
    print(f"  ✓ Confucius discovered the golden rule: {golden_rule_id}")

    # Teaching
    print("\n🎓 Teaching knowledge...")
    print("Einstein teaching Marie about relativity...")
    result = client.teach_character(einstein_id, marie_id, relativity_id, "direct_teaching")
    if result.get("result", {}).get("success"):
        print("  ✓ Teaching successful!")
    else:
        print("  ✗ Teaching failed")

    print("Marie teaching Einstein about radioactivity...")
    result = client.teach_character(marie_id, einstein_id, radioactivity_id, "direct_teaching")
    if result.get("result", {}).get("success"):
        print("  ✓ Teaching successful!")
    else:
        print("  ✗ Teaching failed")

    print("Confucius teaching Einstein the golden rule...")
    result = client.teach_character(confucius_id, einstein_id, golden_rule_id, "direct_teaching")
    if result.get("result", {}).get("success"):
        print("  ✓ Teaching successful!")
    else:
        print("  ✗ Teaching failed")

    # Create artifacts
    print("\n📚 Creating cultural artifacts...")
    einstein_knowledge = client.get_character_knowledge(einstein_id)
    einstein_knowledge_ids = [k["id"] for k in einstein_knowledge]

    if einstein_knowledge_ids:
        relativity_paper_id = client.create_artifact(
            einstein_id,
            "On the Electrodynamics of Moving Bodies",
            "Einstein's 1905 paper introducing special relativity",
            einstein_knowledge_ids[:1],  # Just the first piece of knowledge
            "document"
        )
        print(f"  ✓ Created relativity paper: {relativity_paper_id}")

        # Have Marie learn from the artifact
        print("Marie learning from Einstein's paper...")
        result = client.learn_from_artifact(marie_id, relativity_paper_id)
        if result.get("result", {}).get("success"):
            print(f"  ✓ Marie learned {len(result['result']['learned_knowledge_ids'])} items from paper")
        else:
            print("  ✗ Marie failed to learn from paper")

    # Show final knowledge distribution
    print("\n📊 Final knowledge distribution:")
    for name, char_id in [("Einstein", einstein_id), ("Marie", marie_id), ("Confucius", confucius_id)]:
        knowledge = client.get_character_knowledge(char_id)
        print(f"  {name}: {len(knowledge)} knowledge items")
        for k in knowledge:
            print(f"    - {k['knowledge_type']}: {k['content'][:50]}{'...' if len(k['content']) > 50 else ''}")

    # Show cultural statistics
    print("\n📈 Cultural transmission statistics:")
    stats = client.get_cultural_stats()
    stats_data = stats.get("stats", {})

    print(f"  Total knowledge items: {stats_data.get('total_knowledge', 0)}")
    print(f"  Total artifacts: {stats_data.get('total_artifacts', 0)}")
    print(f"  Total transmissions: {stats_data.get('total_transmissions', 0)}")
    print(f"  Successful transmissions: {stats_data.get('successful_transmissions', 0)}")

    knowledge_by_type = stats_data.get('knowledge_by_type', {})
    if knowledge_by_type:
        print("\n  Knowledge by type:")
        for ktype, count in knowledge_by_type.items():
            print(f"    {ktype.replace('_', ' ').title()}: {count}")

    print("\n🎉 Cultural transmission demo completed!")
    print("The AI society is building its culture through knowledge sharing!")


if __name__ == "__main__":
    demo_cultural_transmission()