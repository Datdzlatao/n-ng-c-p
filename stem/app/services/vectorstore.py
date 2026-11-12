from langchain_pinecone import PineconeVectorStore
from app.services.embeddings import custom_embeddings
from app.core.config import settings

# Khởi tạo VectorStore (Pinecone)
vectorstore = PineconeVectorStore(
    index_name=settings.INDEX_NAME, 
    embedding=custom_embeddings
)