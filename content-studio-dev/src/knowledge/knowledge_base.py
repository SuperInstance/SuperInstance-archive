# src/knowledge/knowledge_base.py

import json
import os
from typing import Dict, Any, List
from datetime import datetime
import chromadb
from chromadb.config import Settings


class KnowledgeBase:
    """Stores and retrieves project knowledge, story summaries, and context"""

    def __init__(self, data_dir: str = "data/knowledge_base"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(f"{data_dir}/chroma", exist_ok=True)

        # Initialize vector store for semantic search (new Chroma API)
        self.chroma_client = chromadb.PersistentClient(path=f"{data_dir}/chroma")

        self.summaries = self.chroma_client.get_or_create_collection("summaries")
        self.patterns = self.chroma_client.get_or_create_collection("patterns")
        self.stories = self.chroma_client.get_or_create_collection("stories")

        # In-memory caches
        self.story_summaries: Dict[str, Dict] = {}
        self.project_context: Dict[str, Any] = {}
        self.changed_files: set = set()

    async def get_context(self, project_id: str = "default") -> Dict[str, Any]:
        """Get project context"""
        if project_id in self.project_context:
            return self.project_context[project_id]

        # Load from disk if not in memory
        context_file = f"{self.data_dir}/context_{project_id}.json"
        if os.path.exists(context_file):
            with open(context_file, 'r') as f:
                self.project_context[project_id] = json.load(f)
                return self.project_context[project_id]

        return {}

    async def store_summary(self, file_path: str, summary: Dict[str, Any]):
        """Store file/story summary"""
        self.story_summaries[file_path] = summary

        # Also store in vector DB for semantic search
        self.summaries.add(
            documents=[json.dumps(summary)],
            metadatas=[{"file_path": file_path, "timestamp": datetime.now().isoformat()}],
            ids=[f"summary_{file_path}"]
        )

    async def get_summary(self, file_path: str) -> Dict[str, Any]:
        """Get file/story summary"""
        return self.story_summaries.get(file_path, {})

    async def store_success(self, bot_type: str, task: Dict, result: Dict, execution_time: float):
        """Store successful task patterns for learning"""
        pattern = {
            'bot_type': bot_type,
            'task': task,
            'result': result,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }

        self.patterns.add(
            documents=[json.dumps(pattern)],
            metadatas=[{"bot_type": bot_type, "success": True}],
            ids=[f"pattern_{datetime.now().timestamp()}"]
        )

    async def index_story(self, story_path: str, content: str, metadata: Dict[str, Any]):
        """Index a story file for semantic search"""
        self.stories.add(
            documents=[content[:10000]],  # Limit to first 10K chars
            metadatas=[{
                "path": story_path,
                "title": metadata.get("title", ""),
                "version": metadata.get("version", ""),
                "timestamp": datetime.now().isoformat()
            }],
            ids=[f"story_{story_path}"]
        )

    async def search_stories(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search stories by semantic similarity"""
        results = self.stories.query(
            query_texts=[query],
            n_results=n_results
        )
        return results

    async def get_changed_files(self) -> List[str]:
        """Get list of changed files"""
        return list(self.changed_files)

    async def read_file(self, file_path: str) -> str:
        """Read file content"""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except:
            return ""

    async def get_project_context(self) -> Dict[str, Any]:
        """Get current project context"""
        return self.project_context.get("default", {
            "project_name": "Loopless Content Studio",
            "content_type": "animated_series",
            "target_platforms": ["YouTube", "Podcast"],
            "visual_style": "anime/Studio Ghibli",
            "audio_style": "impossible music + ocean ambience"
        })

    async def get_recent_errors(self) -> List[Dict[str, Any]]:
        """Get recent system errors"""
        # This would read from error logs
        return []

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            "avg_response_time": 2.5,
            "active_bots": 4,
            "tasks_completed": 0,
            "episodes_produced": 0
        }
