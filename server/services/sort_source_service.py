from typing import List

class SortSourceService:
    def __init__(self):
        # Skip ML dependencies for now
        pass

    def sort_sources(self, query: str, search_results: List[dict]):
        """
        Temporary implementation without ML sorting
        Returns first 5 results or basic keyword matching
        """
        try:
            if not search_results:
                return []
            
            # Simple keyword-based relevance scoring
            query_words = query.lower().split()
            scored_results = []
            
            for result in search_results:
                score = 0
                title = result.get('title', '').lower()
                content = result.get('content', '').lower()
                
                # Count keyword matches
                for word in query_words:
                    if word in title:
                        score += 2  # Title matches are more important
                    if word in content:
                        score += 1
                
                result['relevance_score'] = score
                if score > 0:  # Only include results with some relevance
                    scored_results.append(result)
            
            # Sort by score and return top 5
            sorted_results = sorted(scored_results, key=lambda x: x['relevance_score'], reverse=True)
            return sorted_results[:5] if sorted_results else search_results[:5]
            
        except Exception as e:
            print(f"Sort error: {e}")
            # Fallback: return first 5 results
            return search_results[:5] if search_results else []