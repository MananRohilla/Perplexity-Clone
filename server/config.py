from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    TAVILY_API_KEY: str = "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" # set the API key here on my own 
    GEMINI_API_KEY: str = "AIzaSyAKUhdPtSfPfCVjttqFfuitE83PKa6Nbqo"
