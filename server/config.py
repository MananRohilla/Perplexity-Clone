import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file if it exists (for local development)
load_dotenv()

class Settings(BaseSettings):
    TAVILY_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    class Config:
        # This ensures environment variables take precedence over .env file
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Debug: Print whether keys are loaded (remove in production)
        print(f"TAVILY_API_KEY loaded: {'Yes' if self.TAVILY_API_KEY.strip() else 'No'}")
        print(f"GEMINI_API_KEY loaded: {'Yes' if self.GEMINI_API_KEY.strip() else 'No'}")
        
        # Alternative way to get env vars if pydantic-settings fails
        if not self.TAVILY_API_KEY.strip():
            self.TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
        if not self.GEMINI_API_KEY.strip():
            self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    @property
    def has_tavily_key(self) -> bool:
        return bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip())
    
    @property  
    def has_gemini_key(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

settings = Settings()