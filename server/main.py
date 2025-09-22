import asyncio
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from config import settings
from pydantic_models.chat_body import ChatBody
from services.llm_service import LLMService
from services.sort_source_service import SortSourceService
from services.search_service import SearchService

app = FastAPI(title="Perplexity-Clone Backend", version="1.0.0")

# Configure CORS for production
origins = [
    "https://perplexity-clone-rrjo.onrender.com",
    "https://*.vercel.app"
    "https://perplexity-clone-cyan.vercel.app/",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:5173",
]

# In development, allow all origins
if os.getenv("ENVIRONMENT") == "development":
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services with error handling
try:
    search_service = SearchService()
    sort_source_service = SortSourceService()
    llm_service = LLMService()
except Exception as e:
    print(f"Warning: Failed to initialize services: {e}")
    search_service = None
    sort_source_service = None
    llm_service = None

@app.get("/")
def root():
    return {
        "message": "Perplexity Clone Backend",
        "status": "online",
        "endpoints": ["/healthz", "/chat", "/ws/chat"],
        "websocket_url": "/ws/chat"
    }

@app.get("/healthz")
def healthz():
    health_status = {
        "ok": True,
        "services": {
            "search": search_service is not None,
            "llm": llm_service is not None,
            "sort": sort_source_service is not None
        }
    }
    return health_status

async def _search_and_rank(query: str) -> list[dict]:
    if not search_service or not sort_source_service:
        return [{
            "title": "Service Unavailable",
            "url": "#",
            "content": "Search services are currently unavailable. Please check API keys."
        }]
    
    try:
        # Run search and ranking in thread pool
        search_results = await asyncio.to_thread(search_service.web_search, query)
        sorted_results = await asyncio.to_thread(
            sort_source_service.sort_sources, query, search_results or []
        )
        return sorted_results or []
    except Exception as e:
        print(f"Search error: {e}")
        return [{
            "title": "Search Error",
            "url": "#",
            "content": f"An error occurred during search: {str(e)}"
        }]

async def _stream_llm_chunks(websocket: WebSocket, query: str, sources: list[dict]):
    if not llm_service:
        await websocket.send_json({
            "type": "error",
            "message": "LLM service unavailable. Please check GEMINI_API_KEY."
        })
        return
    
    # Send start marker
    await websocket.send_json({"type": "start"})
    
    try:
        # Stream chunks from LLM
        for chunk in llm_service.generate_response(query, sources):
            if chunk:
                await websocket.send_json({"type": "content", "data": chunk})
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
        
        await websocket.send_json({"type": "end"})
    except Exception as e:
        print(f"LLM streaming error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Error generating response: {str(e)}"
        })

# ---- WebSocket chat endpoint ----
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket connection accepted from {websocket.client}")
    
    try:
        while True:
            try:
                # Wait for client message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                continue
            
            # Extract and validate query
            query: Optional[str] = (data or {}).get("query")
            if not query or not query.strip():
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty query received"
                })
                continue
            
            print(f"Processing query: {query[:50]}...")
            
            # Search and rank sources
            sources = await _search_and_rank(query.strip())
            await websocket.send_json({
                "type": "search_result",
                "data": sources
            })
            
            # Stream LLM response
            await _stream_llm_chunks(websocket, query.strip(), sources)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected from {websocket.client}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

# ---- HTTP fallback endpoint ----
@app.post("/chat")
async def chat_endpoint(body: ChatBody):
    try:
        sources = await _search_and_rank(body.query)
        
        if not llm_service:
            return JSONResponse(
                status_code=503,
                content={"detail": "LLM service unavailable"}
            )
        
        # Generate complete response
        response_parts = []
        for chunk in llm_service.generate_response(body.query, sources):
            if chunk:
                response_parts.append(chunk)
        
        return {
            "answer": "".join(response_parts),
            "sources": sources
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

@app.get("/debug/env")
def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "tavily_key_present": bool(settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip()),
        "gemini_key_present": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        "tavily_key_length": len(settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else 0,
        "gemini_key_length": len(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else 0,
        "render": os.getenv("RENDER", "not_set"),
        "environment": os.getenv("ENVIRONMENT", "not_set")
    }

@app.get("/debug/search/{query}")
async def debug_search(query: str):
    """Debug endpoint to test search functionality"""
    try:
        sources = await _search_and_rank(query)
        return {
            "query": query,
            "sources_count": len(sources),
            "sources": sources[:2]  # Return first 2 sources for debugging
        }
    except Exception as e:
        return {
            "error": str(e),
            "query": query
        }