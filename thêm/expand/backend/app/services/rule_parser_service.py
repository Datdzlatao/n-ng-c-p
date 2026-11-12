"""
backend/app/services/rule_parser_service.py — AI Rule Parser Service
Extracts text from PDF, DOCX, TXT files (up to 50MB) and uses Gemini 3.7 Flash to generate Edge AI violation profiles.
"""
import os, io, json, re, logging
from typing import Dict, Any
from app.config import GEMINI_API_KEY, GEMINI_MODEL

log = logging.getLogger("stem.ai_rules")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

SYSTEM_PROMPT = """Bạn là Chuyên Gia AI Phân Tích Nội Quy Trường Học cho Hệ Thống Camera Điểm Danh Thông Minh.
Nhiệm vụ của bạn là đọc toàn bộ văn bản quy định/nội quy trường học (từ văn bản hoặc file PDF/Word) và trích xuất thành cấu trúc JSON CHÍNH XÁC để nạp vào Camera AI (Raspberry Pi).

Quy chuẩn JSON Schema BẮT BUỘC trả về (CHỈ TRẢ VỀ JSON, không kèm giải thích markdown bên ngoài):
{
  "time_rules": {
    "gate_open": "06:00",
    "on_time_deadline": "07:15",
    "late_cutoff": "07:30",
    "late_deduct_points": 2,
    "absent_deduct_points": 5
  },
  "uniform_rules": {
    "shirt": {
      "required_types": ["WHITE_SHIRT", "POLO_UNIFORM"],
      "require_school_badge": true,
      "violation_deduct_points": 3
    },
    "pants_or_skirt": {
      "allowed_colors": ["NAVY_BLUE", "BLACK", "DARK_GRAY"],
      "prohibit_shorts": true,
      "violation_deduct_points": 2
    },
    "footwear": {
      "allowed_types": ["SHOES", "SANDALS_WITH_STRAP"],
      "prohibit_slippers": true,
      "violation_deduct_points": 2
    },
    "accessories_and_appearance": {
      "prohibit_caps_in_yard": true,
      "prohibit_dyed_hair": true,
      "prohibit_headphones_at_gate": true,
      "violation_deduct_points": 2
    }
  },
  "custom_violations": [
    {
      "code": "CUSTOM_RULE_1",
      "name": "Tên lỗi",
      "description": "Mô tả vi phạm",
      "deduct_points": 2
    }
  ],
  "summary_vi": "Tóm tắt ngắn gọn các điểm chính của nội quy bằng tiếng Việt..."
}
"""

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract readable text from uploaded PDF, DOCX, or TXT file (limit 50MB)."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"Dung lượng file vượt quá giới hạn cho phép (50MB). File của bạn: {len(file_bytes)/(1024*1024):.1f}MB")
    
    ext = os.path.splitext(filename)[1].lower()
    extracted_text = ""
    
    # 1. PDF File
    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)
            extracted_text = "\n".join(pages_text)
        except Exception as e:
            log.error(f"[Extract PDF Error] {e}")
            raise ValueError(f"Không thể đọc nội dung file PDF: {e}")

    # 2. Word DOCX File
    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            extracted_text = "\n".join(paragraphs)
        except Exception as e:
            log.error(f"[Extract DOCX Error] {e}")
            raise ValueError(f"Không thể đọc nội dung file Word (.docx): {e}")

    # 3. Plain text / Markdown
    elif ext in (".txt", ".md", ".csv"):
        try:
            extracted_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = file_bytes.decode("latin-1", errors="ignore")

    else:
        raise ValueError(f"Định dạng file '{ext}' không được hỗ trợ. Vui lòng tải lên file .pdf, .docx, hoặc .txt (tối đa 50MB).")

    if not extracted_text.strip():
        raise ValueError("File tải lên không chứa văn bản hoặc là file scan dạng ảnh thuần túy.")

    return extracted_text.strip()


def parse_rules_with_gemini(raw_text: str) -> Dict[str, Any]:
    """Parse text rules into structured JSON using Gemini API or fallback NLP parser."""
    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    if api_key:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            prompt = f"Văn bản nội quy trường học cần phân tích:\n\"\"\"\n{raw_text}\n\"\"\"\n\nHãy trích xuất thành JSON theo đúng quy chuẩn."
            
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            cleaned = response.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            parsed = json.loads(cleaned.strip())
            log.info("[AI Rule Parser] Gemini successfully extracted rule profile.")
            return parsed
        except Exception as e:
            log.warning(f"[AI Rule Parser] Gemini API call failed ({e}), falling back to NLP rule extractor.")
    
    return _fallback_nlp_extractor(raw_text)


def _fallback_nlp_extractor(text: str) -> Dict[str, Any]:
    """Intelligent regex/heuristic fallback rule extractor when API key is not configured."""
    lower = text.lower()
    
    # Extract deadlines
    on_time = "07:15"
    m_time = re.search(r'(?:trước|đúng giờ|hạn|tới|đến)\s*(\d{1,2})[h:](\d{2})?', lower)
    if m_time:
        h = int(m_time.group(1))
        m = int(m_time.group(2) or 0)
        on_time = f"{h:02d}:{m:02d}"
    
    late_cut = "07:30"
    m_late = re.search(r'(?:sau|trễ tối đa|muộn nhất)\s*(\d{1,2})[h:](\d{2})?', lower)
    if m_late:
        h = int(m_late.group(1))
        m = int(m_late.group(2) or 0)
        late_cut = f"{h:02d}:{m:02d}"
    
    prohibit_slippers = any(w in lower for w in ["dép lê", "dép không quai", "dép xỏ ngón", "cấm dép"])
    prohibit_dyed = any(w in lower for w in ["nhuộm", "nhuộm tóc", "tóc màu", "màu sắc sặc sỡ"])
    prohibit_hat = any(w in lower for w in ["mũ", "nón", "đội mũ", "mũ bảo hiểm trong sân"])
    req_badge = any(w in lower for w in ["phù hiệu", "bảng tên", "logo trường"])
    
    late_pts = 2
    m_pts = re.search(r'trễ\s*(?:bị)?\s*trừ\s*(\d+)', lower)
    if m_pts:
        late_pts = int(m_pts.group(1))

    customs = []
    if "cà vạt" in lower or "caravat" in lower:
        customs.append({
            "code": "CUSTOM_TIE",
            "name": "Cà Vạt Đồng Phục",
            "description": "Bắt buộc đeo cà vạt đồng phục vào ngày lễ/thứ 2",
            "deduct_points": 2
        })

    return {
        "time_rules": {
            "gate_open": "06:00",
            "on_time_deadline": on_time,
            "late_cutoff": late_cut,
            "late_deduct_points": late_pts,
            "absent_deduct_points": 5
        },
        "uniform_rules": {
            "shirt": {
                "required_types": ["WHITE_SHIRT"],
                "require_school_badge": req_badge,
                "violation_deduct_points": 3
            },
            "pants_or_skirt": {
                "allowed_colors": ["NAVY_BLUE", "BLACK", "DARK_BLUE"],
                "prohibit_shorts": True,
                "violation_deduct_points": 2
            },
            "footwear": {
                "allowed_types": ["SHOES", "SANDALS_WITH_STRAP"],
                "prohibit_slippers": prohibit_slippers,
                "violation_deduct_points": 2
            },
            "accessories_and_appearance": {
                "prohibit_caps_in_yard": prohibit_hat,
                "prohibit_dyed_hair": prohibit_dyed,
                "prohibit_headphones_at_gate": True,
                "violation_deduct_points": 2
            }
        },
        "custom_violations": customs,
        "summary_vi": f"Nội quy: Vào cổng trước {on_time}. Áo sơ mi trắng ({'Có phù hiệu' if req_badge else 'Chuẩn'}). Quần tây tối màu. {'Cấm dép lê. ' if prohibit_slippers else ''}{'Cấm nhuộm tóc. ' if prohibit_dyed else ''}{'Cấm đội mũ trong sân. ' if prohibit_hat else ''}"
    }
