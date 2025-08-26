from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    TAVILY_API_KEY: str = "" # set the API key blank so that there is a default null value
    GEMINI_API_KEY: str = "" # set the API key blank so that there is a default null value

settings = Settings()