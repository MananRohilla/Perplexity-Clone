import google.generativeai as genai
from config import settings  # <- relative import

class LLMService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # "flash" is fine for streaming; swap model if you like
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def generate_response(self, query: str, search_results: list[dict]):
        context_text = "\n\n".join(
            [f"Source {i+1} ({r['url']}):\n{r['content']}" for i, r in enumerate(search_results)]
        )
        full_prompt = f"""
        Context from web search:
        {context_text}

        Query: {query}

        Provide a comprehensive, factual, well-cited answer.
        """
        response = self.model.generate_content(full_prompt, stream=True)
        for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text
