from typing import List

class SortSourceService:
    def __init__(self):
        # Skip ML dependencies for now
        pass

    def sort_sources(self, query: str, sources: list[dict]) -> list[dict]:
        """Simple sorting without ML dependencies"""
        if not sources:
            return []
        
        # Simple keyword-based relevance scoring
        query_words = set(query.lower().split())
        
        for source in sources:
            title = source.get("title", "").lower()
            content = source.get("content", "").lower()
            
            # Count keyword matches
            title_matches = sum(1 for word in query_words if word in title)
            content_matches = sum(1 for word in query_words if word in content)
            
            # Simple scoring
            source["relevance_score"] = title_matches * 3 + content_matches
        
        # Sort by relevance score, descending
        return sorted(sources, key=lambda x: x.get("relevance_score", 0), reverse=True)