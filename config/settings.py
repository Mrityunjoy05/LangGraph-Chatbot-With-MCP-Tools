from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    
    GROQ_API_KEY:str =os.getenv('GROQ_API_KEY')
    TAVILY_API_KEY:str =os.getenv('TAVILY_API_KEY')
    OPENWEATHER_API_KEY:str =os.getenv('OPENWEATHER_API_KEY')
    GITHUB_TOKEN:str = os.getenv('GITHUB_TOKEN')
    LLM_MODEL:str =os.getenv('LLM_MODEL')
    LLM_TEMPERATURE:float = float(os.getenv('LLM_TEMPERATURE'))
    K_SEARCH:int= int(os.getenv('K_SEARCH'))
    DB_FOLDER_NAME:str = os.getenv('DB_FOLDER_NAME')
    SERVER_FOLDER_NAME:str = os.getenv('SERVER_FOLDER_NAME')
    DATABASE_NAME:str = os.getenv('DATABASE_NAME')
    WEB_SERVER_NAME:str = os.getenv('WEB_SERVER_NAME')
    GITHUB_SERVER_NAME:str = os.getenv('GITHUB_SERVER_NAME')

    def validate(self) -> bool:

        if not self.GROQ_API_KEY :
            raise ValueError("GROQ API key is not set. Please add it to your .env file")
        
        if not self.TAVILY_API_KEY :
            raise ValueError("TAVILY API key is not set. Please add it to your .env file")
        
        if not self.OPENWEATHER_API_KEY :
            raise ValueError("OPENWEATHER API key is not set. Please add it to your .env file")

        return True


settings = Settings()