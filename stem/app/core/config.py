import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Smart Farm API"
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    INDEX_NAME: str = "smart-farm-knowledge-base"
    EMBEDDING_DIMENSION: int = 1024
    
    # Bạn có thể giới hạn domain gọi API ở đây khi lên Internet
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
