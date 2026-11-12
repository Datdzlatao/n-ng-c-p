import google.generativeai as genai
from langchain_core.embeddings import Embeddings
from app.core.config import settings

genai.configure(api_key=settings.GOOGLE_API_KEY)

class CustomGeminiEmbeddings(Embeddings):
    def embed_documents(self, texts):
        # Đã tối ưu bằng cách truyền cả list 'texts' thay vì dùng vòng lặp for
        if not texts:
            return []
            
        res = genai.embed_content(
            model="models/gemini-embedding-2",
            content=texts,
            task_type="retrieval_document",
            output_dimensionality=settings.EMBEDDING_DIMENSION,
        )
        # Google API trả về dictionary chứa list các embeddings khi truyền list texts
        return res['embedding']

    def embed_query(self, text):
        res = genai.embed_content(
            model="models/gemini-embedding-2",
            content=text,
            task_type="retrieval_query",
            output_dimensionality=settings.EMBEDDING_DIMENSION
        )
        return res['embedding']

custom_embeddings = CustomGeminiEmbeddings()