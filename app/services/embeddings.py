import logging
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger("smart_manager.embeddings")

try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    class Embeddings:
        """Fallback base class when langchain_core is not installed."""
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            raise NotImplementedError

        def embed_query(self, text: str) -> List[float]:
            raise NotImplementedError


class CustomGeminiEmbeddings(Embeddings):
    """
    Custom Gemini Embeddings generator matching the stem RAG pipeline.
    Uses Google GenAI / GenerativeAI embedding models (gemini-embedding-2 / text-embedding-004)
    with configured output dimensionality (default: 1024).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, dimension: Optional[int] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.GEMINI_API_KEY
        self.model = model or self.settings.EMBEDDING_MODEL
        self.dimension = dimension or self.settings.EMBEDDING_DIMENSION
        self._configured = False

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._configured = True
            except Exception as e:
                logger.warning(f"Could not configure google.generativeai embeddings: {e}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if not self._configured:
            # Fallback mock/dummy embedding when API is unconfigured
            return [[0.0] * self.dimension for _ in texts]

        try:
            import google.generativeai as genai
            res = genai.embed_content(
                model=self.model,
                content=texts,
                task_type="retrieval_document",
                output_dimensionality=self.dimension,
            )
            # Google API returns dictionary containing list of embeddings
            embeddings = res.get("embedding", [])
            if embeddings and isinstance(embeddings[0], (int, float)):
                # If only one text was embedded, it might be returned as a single list of floats
                embeddings = [embeddings]
            return embeddings
        except Exception as e:
            logger.error(f"Error generating document embeddings: {e}")
            return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        if not self._configured:
            return [0.0] * self.dimension

        try:
            import google.generativeai as genai
            res = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_query",
                output_dimensionality=self.dimension,
            )
            return res.get("embedding", [0.0] * self.dimension)
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return [0.0] * self.dimension


custom_embeddings = CustomGeminiEmbeddings()
