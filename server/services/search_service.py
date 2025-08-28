from ..config import settings
import requests
from bs4 import BeautifulSoup

try:
    from tavily import TavilyClient
    tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    tavily_client = None

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

class SearchService:
    def web_search(self, query: str):
        if not TAVILY_AVAILABLE:
            return self._fallback_search(query)
            
        try:
            results = []
            response = tavily_client.search(query, max_results=10)
            
            for result in response.get("results", []):
                # Try to extract content
                content = ""
                url = result.get("url", "")
                
                if TRAFILATURA_AVAILABLE:
                    try:
                        downloaded = trafilatura.fetch_url(url)
                        content = trafilatura.extract(downloaded, include_comments=False)
                    except:
                        content = self._simple_extract(url)
                else:
                    content = self._simple_extract(url)
                
                results.append({
                    "title": result.get("title", ""),
                    "url": url,
                    "content": content or result.get("content", "")[:500]  # Fallback to tavily content
                })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return self._fallback_search(query)

    def _simple_extract(self, url):
        """Simple text extraction using requests + BeautifulSoup"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:1000]  # First 1000 characters
        except Exception as e:
            print(f"Extract error for {url}: {e}")
            return ""

    def _fallback_search(self, query):
        """Fallback when Tavily is not available"""
        return [{
            "title": f"Search results for: {query}",
            "url": "https://example.com",
            "content": f"This is a fallback result for the query: {query}. Please configure your Tavily API key for real search results."
        }]