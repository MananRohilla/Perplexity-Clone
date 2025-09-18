from config import settings
import requests
from bs4 import BeautifulSoup

# Try to import Tavily with better error handling
TAVILY_AVAILABLE = False
tavily_client = None

try:
    from tavily import TavilyClient
    if settings.has_tavily_key:
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        TAVILY_AVAILABLE = True
        print("✅ Tavily client initialized successfully")
    else:
        print("⚠️ Tavily API key not found or empty")
except ImportError as e:
    print(f"⚠️ Tavily not available: {e}")
except Exception as e:
    print(f"❌ Error initializing Tavily: {e}")

class SearchService:
    def web_search(self, query: str):
        print(f"🔍 Searching for: {query}")
        print(f"Tavily available: {TAVILY_AVAILABLE}")
        
        if TAVILY_AVAILABLE and tavily_client:
            try:
                print("Using Tavily search...")
                results = []
                response = tavily_client.search(query, max_results=5)
                print(f"Tavily response: {len(response.get('results', []))} results")
                
                for result in response.get("results", []):
                    # Use simple extraction instead of trafilatura
                    content = self._simple_extract(result.get("url", ""))
                    
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": content or result.get("content", "")[:500]
                    })
                
                if results:
                    print(f"✅ Successfully found {len(results)} search results")
                    return results
                else:
                    print("⚠️ Tavily returned no results, using fallback")
                    
            except Exception as e:
                print(f"❌ Tavily search error: {e}")
        
        print("Using fallback search...")
        return self._realistic_fallback_search(query)

    def _simple_extract(self, url):
        """Simple text extraction using requests + BeautifulSoup"""
        try:
            if not url or not url.startswith('http'):
                return ""
                
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
            
            return text[:1000]
        except Exception as e:
            print(f"❌ Extract error for {url}: {e}")
            return ""

    def _realistic_fallback_search(self, query):
        """More realistic fallback that provides useful information"""
        print(f"Generating fallback results for: {query}")
        
        # Check if it's asking about a person's name
        query_lower = query.lower()
        is_person_query = any(word in query_lower for word in ['who is', 'about']) or (
            len(query.split()) <= 3 and query.replace(' ', '').isalpha()
        )
        
        if is_person_query:
            results = [
                {
                    "title": f"Search Results for '{query}'",
                    "url": "https://www.example.com/search",
                    "content": f"I searched for information about '{query}' but don't have access to current web search results. To get accurate information, I would need to search across multiple sources including social media profiles, news articles, professional databases, and official websites. If this is a public figure, you might find information on Wikipedia, news sites, or their official social media profiles."
                },
                {
                    "title": f"How to Research '{query}'",
                    "url": "https://www.example.com/research-tips", 
                    "content": f"To find reliable information about '{query}', try these approaches: 1) Search major search engines like Google or Bing, 2) Check professional networking sites like LinkedIn, 3) Look for news articles or press releases, 4) Check social media platforms, 5) Look for official websites or biographies. Always verify information from multiple reputable sources."
                },
                {
                    "title": "Search Service Status",
                    "url": "https://www.example.com/status",
                    "content": f"This search was performed using a demo mode. For full functionality, this service needs: 1) Tavily API key for web search (free tier available), 2) Proper environment variable configuration on the hosting platform. The service can provide general guidance but cannot access current web information without these credentials."
                }
            ]
        else:
            results = [
                {
                    "title": f"Information Request: {query}",
                    "url": "https://www.example.com/info",
                    "content": f"Your query about '{query}' was received. In full operation mode, this system would search across multiple web sources to provide comprehensive, up-to-date information with proper citations. Currently operating in limited demo mode."
                },
                {
                    "title": "Service Configuration",
                    "url": "https://www.example.com/config",
                    "content": "This Perplexity-style search service is designed to work with web search APIs. To enable full functionality: configure Tavily API key for web search, ensure environment variables are properly set on the deployment platform, and verify all required dependencies are installed."
                }
            ]
        
        print(f"Generated {len(results)} fallback results")
        return results

    def _fallback_search(self, query):
        """Original simple fallback"""
        return [{
            "title": f"Search results for: {query}",
            "url": "https://example.com",
            "content": f"This is a fallback result for the query: {query}. Please configure your Tavily API key for real search results."
        }]