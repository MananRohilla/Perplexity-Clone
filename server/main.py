import asyncio
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .pydantic_models.chat_body import ChatBody
from .services.llm_service import LLMService
from .services.sort_source_service import SortSourceService
from .services.search_service import SearchService

app = FastAPI(title="Perplexity-Clone Backend", version="1.0.0")

# Allow your web clients 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://perplexity-clone-cyan.vercel.app/"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_service = SearchService()
sort_source_service = SortSourceService()
llm_service = LLMService()

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ---- Utilities ----
async def _search_and_rank(query: str) -> list[dict]:
    # Both use network/CPU; run them off the event loop
    search_results = await asyncio.to_thread(search_service.web_search, query)
    sorted_results = await asyncio.to_thread(
        sort_source_service.sort_sources, query, search_results or []
    )
    return sorted_results or []

async def _stream_llm_chunks(websocket: WebSocket, query: str, sources: list[dict]):
    # LLM service is yielding chunks (sync generator). Iterate in thread to avoid blocking.
    def _iter():
        for chunk in llm_service.generate_response(query, sources):
            if chunk:
                yield chunk

    # Send a start marker so client can prepare UI
    await websocket.send_json({"type": "start"})
    try:
        for chunk in await asyncio.to_thread(lambda: list(_iter())):
            await websocket.send_json({"type": "content", "data": chunk})
        await websocket.send_json({"type": "end"})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

# ---- WebSocket chat ----
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Expect messages of the form: {"query": "..."}
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
            except asyncio.TimeoutError:
                # keep the socket alive with a ping
                await websocket.send_json({"type": "ping"})
                continue

            query: Optional[str] = (data or {}).get("query")
            if not query or not query.strip():
                await websocket.send_json({"type": "error", "message": "Empty query"})
                continue

            sources = await _search_and_rank(query.strip())
            await websocket.send_json({"type": "search_result", "data": sources})

            # Stream generated content
            await _stream_llm_chunks(websocket, query.strip(), sources)

    except WebSocketDisconnect:
        # client left; nothing to do
        pass
    except Exception as e:
        # Any unexpected error
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ---- HTTP fallback (non-streaming) ----
@app.post("/chat")
async def chat_endpoint(body: ChatBody):
    try:
        sources = await _search_and_rank(body.query)
        # Consume generator to a single string
        parts = []
        for chunk in llm_service.generate_response(body.query, sources):
            if chunk:
                parts.append(chunk)
        return {"answer": "".join(parts), "sources": sources}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
