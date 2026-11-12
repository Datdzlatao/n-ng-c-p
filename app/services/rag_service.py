import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.services.embeddings import custom_embeddings

logger = logging.getLogger("smart_manager.rag")

# ====================================================================
# BUILT-IN AGRICULTURAL KNOWLEDGE BASE (FALLBACK & SEED DATA)
# ====================================================================
# Cung cấp phác đồ điều trị thú y & bệnh cây trồng chuẩn xác khi Pinecone
# chưa được seed đầy đủ hoặc gặp sự cố kết nối mạng.
BUILTIN_KNOWLEDGE_DOCS = [
    {
        "id": "KB-LIVESTOCK-001",
        "category": "livestock",
        "species": "Heo",
        "disease_name": "Hội chứng rối loạn hô hấp và sinh sản (Tai xanh - PRRS)",
        "keywords": ["tai xanh", "prrs", "sốt cao", "tai tím", "sẩy thai", "khó thở", "ho"],
        "content": (
            "BỆNH TAI XANH Ở HEO (PRRS):\n"
            "- Triệu chứng: Sốt cao liên tục 40-42°C, ủ rũ, tai chót mũi tím tái, khó thở thể bụng, ho khan, heo nái sẩy thai hoặc đẻ non, heo con còi cọc tỉ lệ chết cao.\n"
            "- Phác đồ điều trị & can thiệp:\n"
            "  1. Cách ly nghiêm ngặt: Chuyển ngay cá thể bệnh sang chuồng cách ly (PEN-ISO-01).\n"
            "  2. Hạ sốt & trợ sức: Tiêm Paracetamol hoặc Anagin C (1ml/10kg P), bổ sung Vitamin C + Điện giải Gluco-K-C qua nước uống liên tục 5-7 ngày.\n"
            "  3. Chống bội nhiễm: Dùng kháng sinh phổ rộng Ceftiofur (1ml/15kg P) hoặc Amoxicillin 15% (1ml/10kg P) tiêm bắp 1 lần/ngày trong 4-5 ngày.\n"
            "  4. Vệ sinh môi trường: Phun sát trùng chuồng bằng Iodine hoặc vôi bột 2 ngày/lần, tăng thông gió quạt hút giảm khí độc chuồng."
        ),
        "source": "Cẩm Nang Thú Y - Viện Chăn Nuôi Quốc Gia",
    },
    {
        "id": "KB-LIVESTOCK-002",
        "category": "livestock",
        "species": "Heo",
        "disease_name": "Dịch tả lợn châu Phi (ASF)",
        "keywords": ["dịch tả lợn châu phi", "asf", "xuất huyết", "chết đột ngột", "sốt rất cao", "bỏ ăn"],
        "content": (
            "DỊCH TẢ LỢN CHÂU PHI (ASF):\n"
            "- Triệu chứng: Sốt rất cao 41-42°C trong 3-4 ngày đầu, bỏ ăn hoàn toàn, da xuất huyết dạng đốm tím ở tai, bụng, bẹn, đuôi; nôn mửa, tiêu chảy ra máu; tỉ lệ chết gần 100%.\n"
            "- Quy trình xử lý khẩn cấp:\n"
            "  1. Hiện tại CHƯA CÓ THUỐC ĐẶC TRỊ. Tuyệt đối không tự ý bán tháo hay mổ thịt.\n"
            "  2. Báo cáo ngay cho cơ quan Thú y địa phương để lấy mẫu xét nghiệm khẳng định.\n"
            "  3. Khoanh vùng, phong tỏa toàn bộ khu vực chuồng trại, lập chốt khử trùng vôi bột dày ở lối ra vào.\n"
            "  4. Tiêu hủy cá thể chết theo quy trình chôn lấp vôi bột sâu 1.5 - 2m hoặc đốt tiêu hủy.\n"
            "  5. Tiêu độc khử trùng liên tục toàn trang trại bằng dung dịch xút (NaOH) 2% hoặc Formol 2%."
        ),
        "source": "Quy Chuẩn Quốc Gia Phòng Chống Dịch Bệnh Gia Súc - Cục Thú Y",
    },
    {
        "id": "KB-LIVESTOCK-003",
        "category": "livestock",
        "species": "Heo",
        "disease_name": "Bệnh tiêu chảy cấp do Coronavirus (PED)",
        "keywords": ["tiêu chảy", "ped", "phân vàng", "nôn mửa", "mất nước", "heo con"],
        "content": (
            "BỆNH TIÊU CHẢY CẤP (PED) Ở HEO:\n"
            "- Triệu chứng: Heo con theo mẹ nôn mửa, tiêu chảy tóe nước màu vàng/trắng xám tanh khắm, sụt cân cấp tính, mất nước kiệt quệ, chết sau 2-4 ngày.\n"
            "- Phác đồ điều trị:\n"
            "  1. Bù nước & điện giải cấp bách: Cho uống dung dịch Oresol pha ấm nhiều lần trong ngày, có thể truyền tĩnh mạch tai hoặc xoang bụng nếu mất nước nặng.\n"
            "  2. Giữ ấm chuồng trại: Nâng nhiệt độ úm lên 32-34°C bằng đèn sưởi hồng ngoại, giữ sàn chuồng khô ráo tuyệt đối.\n"
            "  3. Bổ sung kháng thể & men tiêu hóa: Cho uống kháng thể PED và men vi sinh probiotic liều gấp đôi để cân bằng lại hệ vi sinh đường ruột.\n"
            "  4. Ngừa phụ nhiễm: Tiêm Enrofloxacin hoặc Colistin liều điều trị trong 3 ngày."
        ),
        "source": "Sổ Tay Chẩn Đoán & Điều Trị Bệnh Heo Nái & Heo Con",
    },
    {
        "id": "KB-LIVESTOCK-004",
        "category": "livestock",
        "species": "Heo",
        "disease_name": "Bệnh lở mồm long móng (FMD)",
        "keywords": ["lở mồm long móng", "fmd", "mụn nước", "kẽ móng", "chảy dãi", "khập khiễng"],
        "content": (
            "BỆNH LỞ MỒM LONG MÓNG (FMD):\n"
            "- Triệu chứng: Sốt cao, ủ rũ, chảy nhiều nước dãi có bọt trắng quanh mép; xuất hiện mụn nước ở niêm mạc miệng, nướu, lưỡi, vành móng, kẽ móng chân; mụn vỡ gây viêm loét khiến gia súc đau đớn đi khập khiễng hoặc nằm liệt.\n"
            "- Phác đồ điều trị triệu chứng & vệ sinh:\n"
            "  1. Cách ly nghiêm ngặt cá thể bệnh để ngăn lây lan toàn đàn.\n"
            "  2. Rửa vết loét: Dùng dung dịch chua nhẹ (nước chanh, giấm thanh, khế chua) hoặc thuốc tím 1% rửa sạch vùng miệng và kẽ móng ngày 2-3 lần.\n"
            "  3. Bôi thuốc sát trùng làm lành niêm mạc: Xanh methylen 1% hoặc bột than lá xoan nghiền đắp lên vết loét móng.\n"
            "  4. Giảm đau & kháng viêm: Tiêm Flunixin Meglumine hoặc Ketoprofen, cho ăn thức ăn mềm lỏng giàu dinh dưỡng."
        ),
        "source": "Hướng Dẫn Kỹ Thuật Điều Trị Bệnh Truyền Nhiễm Gia Súc - Chi Cục Chăn Nuôi",
    },
    {
        "id": "KB-CROP-001",
        "category": "crop",
        "species": "Lúa",
        "disease_name": "Bệnh đạo ôn (Pyricularia oryzae)",
        "keywords": ["đạo ôn", "cháy lá", "thoi", "thối cổ bông", "lúa", "lá vàng", "nấm"],
        "content": (
            "BỆNH ĐẠO ÔN HẠI LÚA:\n"
            "- Triệu chứng: Trên phiến lá xuất hiện chấm nhỏ hình thoi, màu nâu xám, tâm trắng bạc (đạo ôn lá). Ở giai đoạn trổ đòng, cổ bông bị thối thắt lại chuyển sang màu nâu đen làm hạt lép lửng hoàn toàn (đạo ôn cổ bông).\n"
            "- Quy trình phòng trị:\n"
            "  1. Ngưng ngay việc bón phân đạm (Urê), không phun phân bón lá có hàm lượng đạm cao.\n"
            "  2. Giữ mực nước ruộng ổn định từ 3-5 cm, không để ruộng bị khô hạn nứt nẻ.\n"
            "  3. Phun thuốc đặc trị nấm: Dùng hoạt chất Tricyclazole (Beam 75WP), Isoprothiolane (Fuji-one 40EC), hoặc Kasugamycin (Kasumin 2SL).\n"
            "  4. Phun sáng sớm hoặc chiều mát, nếu bệnh nặng phun nhắc lại lần 2 sau 5-7 ngày."
        ),
        "source": "Viện Bảo Vệ Thực Vật - Quy Trình Quản Lý Bệnh Cây Lương Thực",
    },
    {
        "id": "KB-CROP-002",
        "category": "crop",
        "species": "Cà chua & Dưa lưới",
        "disease_name": "Bệnh mốc sương / Sương mai (Phytophthora infestans)",
        "keywords": ["sương mai", "mốc sương", "cà chua", "dưa lưới", "đốm nâu", "cháy lá", "nhà màng"],
        "content": (
            "BỆNH SƯƠNG MAI TRÊN CÀ CHUA VÀ DƯA LƯỚI:\n"
            "- Triệu chứng: Vết bệnh ban đầu xuất hiện ở mép hoặc chóp lá màu xanh tái, sau chuyển sang nâu đen, mặt dưới lá có lớp phấn nấm màu trắng mỏng. Thân cây xuất hiện vệt úng nước màu nâu, quả non bị chai sượng sẫm màu.\n"
            "- Biện pháp xử lý & bảo vệ:\n"
            "  1. Điều chỉnh môi trường nhà màng (PEN-B01): Bật quạt thông gió để giảm độ ẩm không khí dưới 80%, tỉa bỏ lá gốc già, lá bị bệnh thu gom tiêu hủy xa khu canh tác.\n"
            "  2. Phun thuốc trừ nấm nội hấp: Dùng Metalaxyl-M + Mancozeb (Ridomil Gold 68WG), Dimethomorph (Acrobat MZ) hoặc Fosetyl Aluminium (Aliette 800WG).\n"
            "  3. Tưới nhỏ giọt kiểm soát lượng nước tưới, tránh phun nước ướt đẫm tán lá vào chiều tối."
        ),
        "source": "Giáo Trình Bệnh Học Cây Trồng - ĐH Nông Nghiệp",
    },
    {
        "id": "KB-CROP-003",
        "category": "crop",
        "species": "Lúa",
        "disease_name": "Rầy nâu (Nilaparvata lugens) & Bệnh vàng lùn",
        "keywords": ["rầy nâu", "cháy rầy", "vàng lùn", "lùn xoắn lá", "lúa"],
        "content": (
            "RẦY NÂU HẠI LÚA VÀ TRUYỀN BỆNH VÀNG LÙN:\n"
            "- Triệu chứng: Rầy chích hút nhựa ở gốc làm cây vàng úa, khi mật độ cao gây hiện tượng 'cháy rầy' từng chòm tròn; rầy là môi giới truyền virus gây bệnh Vàng lùn và Lùn xoắn lá không có thuốc trị.\n"
            "- Quy trình phòng trừ:\n"
            "  1. Thăm đồng thường xuyên, kiểm tra kỹ gốc lúa khi lúa giai đoạn đẻ nhánh đến trổ.\n"
            "  2. Khi mật độ rầy tuổi 2-3 đạt trên 3 con/tép: Phun thuốc đặc trị rầy chống lột xác Buprofezin (Applaud 10WP) hoặc thuốc nội hấp Pymetrozine (Chess 50WG).\n"
            "  3. Hạ mực nước trước khi phun và phun hạ thấp vòi xịt hướng vào gốc lúa nơi rầy trú ngụ."
        ),
        "source": "Cục Trồng Trọt & BVTV",
    },
]


class FarmRAGService:
    """
    RAG Service integrating Pinecone Vector Store and Gemini Embeddings
    with robust local veterinary/crop knowledge fallback.
    Implements the diagnosis workflow from the stem project.
    """

    def __init__(self):
        self.settings = get_settings()
        self.embeddings = custom_embeddings
        self._vectorstore = None
        self._pinecone_ready = False
        self._init_vectorstore()

    def _init_vectorstore(self):
        """Initialize Pinecone VectorStore if configured and library available."""
        if not self.settings.is_pinecone_configured:
            logger.info("Pinecone API key not configured. Using Built-in Agricultural Knowledge Base.")
            return

        try:
            from langchain_pinecone import PineconeVectorStore
            # Set environment variable for Pinecone client
            os.environ["PINECONE_API_KEY"] = self.settings.PINECONE_API_KEY

            self._vectorstore = PineconeVectorStore(
                index_name=self.settings.PINECONE_INDEX_NAME,
                embedding=self.embeddings,
            )
            self._pinecone_ready = True
            logger.info(f"Pinecone VectorStore initialized with index: {self.settings.PINECONE_INDEX_NAME}")
        except Exception as e:
            logger.warning(f"Could not connect to Pinecone VectorStore: {e}. Falling back to Built-in Knowledge Base.")
            self._pinecone_ready = False

    def search_knowledge(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search agricultural knowledge base (Pinecone VectorStore first, then Built-in Fallback).
        Returns a list of document dicts with content, metadata, and score.
        """
        results: List[Dict[str, Any]] = []

        # 1. Try Pinecone VectorStore
        if self._pinecone_ready and self._vectorstore:
            try:
                docs = self._vectorstore.similarity_search(query, k=k)
                if docs:
                    for d in docs:
                        results.append({
                            "content": d.page_content,
                            "metadata": getattr(d, "metadata", {}),
                            "source": getattr(d, "metadata", {}).get("source", "Pinecone Knowledge Base"),
                        })
                    return results
            except Exception as e:
                logger.warning(f"Pinecone similarity search failed: {e}. Falling back to internal KB.")

        # 2. Fallback to Built-in Knowledge Base
        query_lower = query.lower()
        scored_docs = []

        for doc in BUILTIN_KNOWLEDGE_DOCS:
            score = 0
            # Keyword matching
            for kw in doc.get("keywords", []):
                if kw in query_lower:
                    score += 5
            # Species matching
            if doc.get("species", "").lower() in query_lower:
                score += 3
            # Disease name matching
            if doc.get("disease_name", "").lower() in query_lower:
                score += 7
            # General term in content
            words = [w for w in query_lower.split() if len(w) > 3]
            for w in words:
                if w in doc.get("content", "").lower():
                    score += 1

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by relevance score
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        if not scored_docs:
            # If no specific match, return top k generic relevant docs
            scored_docs = [(1, d) for d in BUILTIN_KNOWLEDGE_DOCS[:k]]

        for _, doc in scored_docs[:k]:
            results.append({
                "content": doc["content"],
                "metadata": {
                    "id": doc.get("id"),
                    "species": doc.get("species"),
                    "disease_name": doc.get("disease_name"),
                    "category": doc.get("category"),
                },
                "source": doc.get("source", "Built-in Agricultural Knowledge Base"),
            })

        return results

    def retrieve_context(self, query: str, k: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve formatted text context from the knowledge base for LLM injection.
        Matches stem's `retrieve_context` tool interface.
        """
        docs = self.search_knowledge(query, k=k)
        if not docs:
            return "Dữ liệu hiện tại chưa có thông tin chi tiết về vấn đề này.", []

        formatted_content = "\n\n---\n\n".join([d["content"] for d in docs])
        return formatted_content, docs

    def diagnose_disease(
        self,
        user_query: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime_type: Optional[str] = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Executes the complete RAG Agricultural Disease Diagnosis Workflow:
        1. Analyzes text or multimodal image to detect category (livestock/crop), species, and disease.
        2. Retrieves treatment protocol from VectorStore / Knowledge Base using retrieve_context.
        3. Returns structured JSON:
           {
               "category": "livestock" | "crop",
               "species": "...",
               "disease_name": "...",
               "text": "...",
               "answer": "...",
               "sources": [...]
           }
        """
        clean_query = user_query.strip() if user_query else "Chẩn đoán triệu chứng bệnh cây trồng hoặc vật nuôi."

        # If Gemini client is configured and available, try multimodal diagnosis
        if self.settings.is_gemini_configured:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.settings.GEMINI_API_KEY)

                # Step 1: Detect disease and query context
                context_str, docs = self.retrieve_context(clean_query, k=2)

                system_instruction = (
                    "Bạn là chuyên gia chẩn đoán nông nghiệp và thú y thông minh. "
                    "Nhiệm vụ của bạn là phân tích VĂN BẢN hoặc HÌNH BỆNH để chẩn đoán bệnh lý "
                    "và trích xuất phác đồ điều trị chuẩn xác.\n\n"
                    "NGỮ CẢNH TÀI LIỆU Y TẾ TRÍCH XUẤT TỪ CƠ SỞ TRI THỨC RAG:\n"
                    f"{context_str}\n\n"
                    "ĐỊNH DẠNG ĐẦU RA BẮT BUỘC: Bạn PHẢI trả về duy nhất một chuỗi JSON hợp lệ không markdown với các trường:\n"
                    "{\n"
                    '  "category": "livestock" hoặc "crop",\n'
                    '  "species": "tên loài (VD: heo, bò, lúa, cà chua...)",\n'
                    '  "disease_name": "tên bệnh chẩn đoán được",\n'
                    '  "text": "tóm tắt ngắn gọn triệu chứng quan sát được",\n'
                    '  "answer": "phác đồ điều trị và hướng dẫn can thiệp chi tiết dựa trên tài liệu"\n'
                    "}"
                )

                contents = []
                if image_bytes:
                    contents.append(
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=image_mime_type or "image/jpeg",
                        )
                    )
                contents.append(clean_query)

                response = client.models.generate_content(
                    model=self.settings.GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )

                if response.text:
                    parsed = json.loads(response.text)
                    parsed["sources"] = [d.get("source", "RAG Knowledge Base") for d in docs]
                    return parsed

            except Exception as e:
                logger.warning(f"Gemini RAG diagnosis failed: {e}. Falling back to Rule-based RAG Diagnosis.")

        # Fallback Diagnosis Engine (Rule-based RAG)
        context_str, docs = self.retrieve_context(clean_query, k=3)

        category = "livestock"
        species = "Heo"
        disease_name = "Chưa rõ"

        q_low = clean_query.lower()
        if any(w in q_low for w in ["lúa", "cà chua", "dưa", "cây", "lá", "bông", "đạo ôn", "sương mai", "rầy"]):
            category = "crop"
            if "lúa" in q_low or "đạo ôn" in q_low or "rầy" in q_low:
                species = "Lúa"
                disease_name = "Bệnh đạo ôn hoặc rầy nâu hại lúa"
            elif "cà chua" in q_low or "sương mai" in q_low or "dưa" in q_low:
                species = "Cà chua / Dưa lưới"
                disease_name = "Bệnh mốc sương / Sương mai"
        else:
            category = "livestock"
            if "tai xanh" in q_low or "prrs" in q_low:
                species = "Heo"
                disease_name = "Hội chứng rối loạn hô hấp & sinh sản (Tai xanh - PRRS)"
            elif "dịch tả" in q_low or "asf" in q_low:
                species = "Heo"
                disease_name = "Dịch tả lợn châu Phi (ASF)"
            elif "tiêu chảy" in q_low or "ped" in q_low:
                species = "Heo"
                disease_name = "Bệnh tiêu chảy cấp do Coronavirus (PED)"
            elif "lở mồm" in q_low or "mụn nước" in q_low:
                species = "Gia súc (Heo/Bò)"
                disease_name = "Bệnh lở mồm long móng (FMD)"
            elif "sốt" in q_low or "bỏ ăn" in q_low:
                species = "Heo"
                disease_name = "Nhiễm khuẩn đường hô hấp / Sốt truyền nhiễm"

        return {
            "category": category,
            "species": species,
            "disease_name": disease_name,
            "text": clean_query,
            "answer": (
                f"Chẩn đoán sơ bộ: {disease_name} trên {species}.\n\n"
                f"Phác đồ xử lý & điều trị khuyến nghị từ Cơ Sở Tri Thức:\n"
                f"{context_str}"
            ),
            "sources": [d.get("source", "Built-in Knowledge Base") for d in docs],
        }


# Global Singleton Instance
rag_service = FarmRAGService()
