import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import get_settings
from app.mcp.mcp_server import (
    get_farm_overview,
    get_pens_list,
    get_latest_env_logs,
    get_low_stock_inventory,
    get_animals_attention,
    get_crops_harvest,
    get_pen_status,
    transfer_animal_pen,
    manage_pen,
    control_device,
    log_feeding,
    update_animal_health,
    manage_inventory,
    manage_schedule,
    create_system_alert,
    search_agricultural_knowledge,
    diagnose_agricultural_disease,
    get_today_staff_attendance,
    get_all_staff_resource,
    get_staff_list,
    check_in_staff_face,
    get_today_attendance_summary,
)

logger = logging.getLogger("smart_manager.agent")


class AIAgentService:
    """
    AI Agent Service acting as MCP Host / Client for Smart Farm & IoT.
    Bridges Gemini LLM with FastMCP Resources and Tools across all farm pens.
    """

    def __init__(self):
        self.settings = get_settings()
        self._genai_client = None

        if self.settings.is_gemini_configured:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
                logger.info("Google Gemini Client initialized with model: %s", self.settings.GEMINI_MODEL)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Falling back to Rule-based Engine.")

    def get_system_prompt_with_mcp_context(self) -> str:
        """
        Dynamically read MCP Resources to build the latest real-time context for the AI Agent.
        """
        overview_ctx = get_farm_overview()
        pens_ctx = get_pens_list()
        env_ctx = get_latest_env_logs()
        inventory_ctx = get_low_stock_inventory()
        animals_ctx = get_animals_attention()
        crops_ctx = get_crops_harvest()
        staff_ctx = get_today_staff_attendance()

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        prompt = f"""Bạn là Quản Lý Trang Trại Nông Nghiệp Thông Minh (Smart Farm AI Agent) điều phối đa chuồng trại qua giao thức FastMCP.
Thời gian hiện tại: {current_time}

NGỮ CẢNH TOÀN BỘ CÁC CHUỒNG TRẠI VÀ TRANG TRẠI (TỪ GIAO THỨC MCP):
--------------------------------------------------
[MCP Resource: resource://farm/overview - Thống kê tổng quan]
{overview_ctx}

[MCP Resource: resource://pens/list - Danh sách chi tiết từng chuồng trại]
{pens_ctx}

[MCP Resource: resource://env/latest - Cảm biến môi trường mới nhất]
{env_ctx}

[MCP Resource: resource://animals/attention - Vật nuôi ốm sốt / cần theo dõi]
{animals_ctx}

[MCP Resource: resource://crops/harvest - Vụ mùa / cây trồng sắp thu hoạch]
{crops_ctx}

[MCP Resource: resource://inventory/low-stock - Thức ăn, thuốc, vật tư chạm ngưỡng an toàn]
{inventory_ctx}

[MCP Resource: resource://staff/today - Danh sách nhân sự đã có mặt / điểm danh hôm nay]
{staff_ctx}
--------------------------------------------------

CÁC CÔNG CỤ (MCP TOOLS) BẠN CÓ:
1. `transfer_animal_pen(animal_id, target_pen_id, reason)`: CHUYỂN ĐỔI CHUỒNG cho cá thể vật nuôi từ chuồng cũ sang chuồng mới (ví dụ: chuyển sang chuồng cách ly y tế PEN-ISO-01, đổi chuồng thịt PEN-A02...).
2. `get_pen_status(pen_id)`: Tra cứu tình trạng chi tiết của một chuồng bất kỳ (cảm biến nhiệt độ, ẩm, mùi, thiết bị, vật nuôi).
3. `manage_pen(action, pen_id, name, pen_type)`: Tạo chuồng mới hoặc cập nhật thông tin chuồng.
4. `control_device(action, device_name, pen_id)`: Bật/tắt thiết bị IoT (quạt, đèn sưởi, máy phun sương) tại chuồng được chỉ định.
5. `log_feeding(pen_id, food_name, amount)`: Ghi nhận cho vật nuôi ăn tại chuồng và tự động trừ kho thức ăn.
6. `update_animal_health(animal_id, status, note, health_type)`: Cập nhật sức khỏe (Khỏe, Sốt, Bệnh, Cách ly).
7. `manage_inventory(action, name, quantity, unit, category)`: Nhập kho, xuất kho hoặc tạo mới thức ăn/vật tư.
8. `manage_schedule(action, task_name, target_date, pen_id, note)`: Lên lịch hoặc hoàn thành công việc theo chuồng.
9. `create_system_alert(alert_type, message, pen_id)`: Phát cảnh báo nguy cơ chuồng trại qua WebSocket.
10. `search_agricultural_knowledge(query, limit)`: TRA CỨU CƠ SỞ TRI THỨC RAG (Pinecone Knowledge Base) về phác đồ điều trị bệnh gia súc/cây trồng, thông tin thuốc thú y, bệnh lý nông nghiệp.
11. `diagnose_agricultural_disease(symptoms_or_description, species)`: CHẨN ĐOÁN BỆNH LÝ & TRÍCH XUẤT PHÁC ĐỒ ĐIỀU TRỊ chuyên sâu từ cơ sở tri thức RAG.
12. `get_staff_list(pen_id)`: Tra cứu danh sách nhân sự trang trại, phân công ca trực và chuồng phụ trách.
13. `check_in_staff_face(staff_id, pen_id, note)`: Điểm danh vào ca làm việc cho nhân viên bằng FaceID nhận diện khuôn mặt.
14. `get_today_attendance_summary()`: Xem tổng hợp tình hình điểm danh nhân sự hôm nay (ai đã có mặt, ai chưa đến).

NHIỆM VỤ CỦA BẠN:
- Hệ thống hỗ trợ RẤT NHIỀU CHUỒNG KHÁC NHAU (ví dụ: Chuồng Heo Khu A1 '123', Chuồng Heo Khu A2 'PEN-A02', Khu Cách Ly 'PEN-ISO-01', Nhà Màng 'PEN-B01'...).
- Khi người dùng muốn đổi chuồng, chuyển chuồng cho vật nuôi, hoặc kiểm tra bất kỳ chuồng nào, hãy gọi tool tương ứng với mã `pen_id` chính xác.
- Khi người dùng hỏi về bệnh tật của vật nuôi (sốt, tai xanh, tiêu chảy PED, lở mồm long móng...) hoặc sâu bệnh cây trồng (đạo ôn, rầy nâu, sương mai...), bạn PHẢI gọi `search_agricultural_knowledge` hoặc `diagnose_agricultural_disease` để trích xuất phác đồ y tế chuẩn xác và hướng dẫn người dùng chi tiết, an tâm.
- Luôn trả lời bằng tiếng Việt lịch sự, thân thiện, rõ ràng về mã chuồng thao tác.
"""
        return prompt

    def _fallback_intent_engine(self, user_message: str) -> dict[str, Any]:
        """
        Rule-based NLP Engine: Ensures multi-pen tools and animal transfers are executable seamlessly.
        """
        msg = user_message.lower().strip()
        executed_tools = []
        reply_lines = []

        # 1. Action: CHUYỂN CHUỒNG / ĐỔI CHUỒNG VẬT NUÔI
        if any(k in msg for k in ["chuyển chuồng", "đổi chuồng", "chuyển sang chuồng", "chuyển con", "chuyển cá thể", "dời chuồng", "cách ly"]):
            # Detect animal ID
            id_match = re.findall(r"(heo[\-_]?[0-9a-zA-Z]+|bò[\-_]?[0-9a-zA-Z]+|[a-zA-Z]+[\-_][0-9a-zA-Z]+)", msg)
            animal_id = id_match[0].upper() if id_match else "HEO-102"

            # Detect target pen
            target_pen = "PEN-ISO-01"
            if "cách ly" in msg or "iso" in msg or "y tế" in msg or "bệnh" in msg:
                target_pen = "PEN-ISO-01"
            elif "a02" in msg or "a2" in msg or "chuồng a2" in msg:
                target_pen = "PEN-A02"
            elif "b01" in msg or "b1" in msg:
                target_pen = "PEN-B01"
            elif "123" in msg or "a1" in msg:
                target_pen = "123"
            else:
                pen_match = re.findall(r"chuồng\s*([a-zA-Z0-9_\-]+)", msg)
                if pen_match:
                    target_pen = pen_match[0].upper()

            reason = user_message
            result = transfer_animal_pen(animal_id=animal_id, target_pen_id=target_pen, reason=reason)
            executed_tools.append({
                "tool": "transfer_animal_pen",
                "args": {"animal_id": animal_id, "target_pen_id": target_pen, "reason": reason},
                "result": result,
            })
            reply_lines.append(f"🤖 [Smart Farm Agent]: {result}")

        # 2. Action: ĐIỀU KHIỂN THIẾT BỊ (THEO CHUỒNG)
        elif any(k in msg for k in ["bật", "mở", "tắt", "khởi động", "dừng"]) and any(k in msg for k in ["quạt", "đèn", "phun sương", "nước", "thiết bị", "van"]):
            action = "turn_on" if any(k in msg for k in ["bật", "mở", "khởi động"]) else "turn_off"
            dev_name = "quạt"
            if "đèn" in msg or "uv" in msg:
                dev_name = "đèn"
            elif "nước" in msg or "phun sương" in msg:
                dev_name = "phun sương"
            elif "tưới" in msg or "van" in msg:
                dev_name = "van"

            pen_id = "123"
            if "a02" in msg or "a2" in msg:
                pen_id = "PEN-A02"
            elif "cách ly" in msg or "iso" in msg:
                pen_id = "PEN-ISO-01"
            elif "b01" in msg or "b1" in msg:
                pen_id = "PEN-B01"
            else:
                pen_match = re.findall(r"chuồng\s*([a-zA-Z0-9_\-]+)", msg)
                if pen_match:
                    pen_id = pen_match[0]

            result = control_device(action=action, device_name=dev_name, pen_id=pen_id)
            executed_tools.append({"tool": "control_device", "args": {"action": action, "device_name": dev_name, "pen_id": pen_id}, "result": result})
            reply_lines.append(f"🤖 [Smart Farm Agent]: {result}")

        # 3. Action: CHO ĂN THEO CHUỒNG
        elif any(k in msg for k in ["cho ăn", "ăn", "cung cấp thức ăn", "bữa ăn"]) and any(k in msg for k in ["cám", "chuồng", "thức ăn", "kg"]):
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", msg)
            amount = float(numbers[0]) if numbers else 5.0
            food_name = "Cám Con Cò Siêu Tăng Trọng"
            pen_id = "123"
            if "a02" in msg or "a2" in msg:
                pen_id = "PEN-A02"
            elif "cách ly" in msg or "iso" in msg:
                pen_id = "PEN-ISO-01"
            else:
                pen_match = re.findall(r"chuồng\s*([a-zA-Z0-9_\-]+)", msg)
                if pen_match:
                    pen_id = pen_match[0]

            result = log_feeding(pen_id=pen_id, food_name=food_name, amount=amount)
            executed_tools.append({"tool": "log_feeding", "args": {"pen_id": pen_id, "food_name": food_name, "amount": amount}, "result": result})
            reply_lines.append(f"🤖 [Smart Farm Agent]: {result}")

        # 4. Action: TRA CỨU CHUỒNG CỤ THỂ
        elif any(k in msg for k in ["xem chuồng", "thông tin chuồng", "chuồng nào", "tình hình chuồng", "chỉ số chuồng"]):
            pen_id = "123"
            if "a02" in msg or "a2" in msg:
                pen_id = "PEN-A02"
            elif "cách ly" in msg or "iso" in msg:
                pen_id = "PEN-ISO-01"
            elif "b01" in msg or "b1" in msg:
                pen_id = "PEN-B01"
            elif "b02" in msg or "b2" in msg:
                pen_id = "PEN-B02"
            else:
                pen_match = re.findall(r"chuồng\s*([a-zA-Z0-9_\-]+)", msg)
                if pen_match:
                    pen_id = pen_match[0]

            result = get_pen_status(pen_id=pen_id)
            executed_tools.append({"tool": "get_pen_status", "args": {"pen_id": pen_id}, "result": result})
            reply_lines.append(f"🤖 [Smart Farm Agent]: Thông tin chi tiết chuồng [{pen_id}]:\n{result}")

        # 5. Action: SỨC KHỎE VẬT NUÔI
        elif any(k in msg for k in ["sốt", "ốm", "bệnh", "bỏ ăn", "khỏe", "tiêu chảy", "sức khỏe"]) and any(k in msg for k in ["heo", "bò", "vật nuôi", "cá thể"]):
            id_match = re.findall(r"(heo[\-_]?[0-9a-zA-Z]+|bò[\-_]?[0-9a-zA-Z]+|[a-zA-Z]+[\-_][0-9a-zA-Z]+)", msg)
            animal_id = id_match[0].upper() if id_match else "HEO-102"
            status = "Khoe" if "khỏe" in msg else ("Bo an" if "bỏ ăn" in msg else "Sot")

            result = update_animal_health(animal_id=animal_id, status=status, note=user_message)
            executed_tools.append({"tool": "update_animal_health", "args": {"animal_id": animal_id, "status": status, "note": user_message}, "result": result})
            reply_lines.append(f"🤖 [Smart Farm Agent]: {result}")

        # 6. Action: XUẤT NHẬP KHO
        elif any(k in msg for k in ["xuất", "nhập", "kho"]) and any(k in msg for k in ["cám", "thuốc", "phân", "kg", "bao"]):
            action = "import" if any(k in msg for k in ["nhập", "thêm", "mua"]) else "export"
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", msg)
            qty = float(numbers[0]) if numbers else 10.0
            item_name = "Cám Con Cò Siêu Tăng Trọng"
            result = manage_inventory(action=action, name=item_name, quantity=qty)
            executed_tools.append({"tool": "manage_inventory", "args": {"action": action, "name": item_name, "quantity": qty}, "result": result})
            reply_lines.append(f"🤖 [Smart Farm Agent]: {result}")

        # 7. Resource: DANH SÁCH TẤT CẢ CÁC CHUỒNG
        elif any(k in msg for k in ["các chuồng", "danh sách chuồng", "tất cả chuồng", "mấy chuồng", "chuồng trại"]):
            pens_str = get_pens_list()
            reply_lines.append(f"🤖 [Smart Farm Agent]: Danh sách toàn bộ các chuồng trong trang trại:\n{pens_str}")

        # 8. Action: RAG TRA CỨU TRI THỨC NÔNG NGHIỆP & CHẨN ĐOÁN BỆNH (TÍCH HỢP TỪ WORKFLOW STEM)
        elif any(k in msg for k in [
            "chẩn đoán", "bệnh gì", "phác đồ", "cách chữa", "điều trị", "triệu chứng", "thuốc trị",
            "tai xanh", "dịch tả", "asf", "prrs", "ped", "lở mồm", "đạo ôn", "sương mai", "rầy nâu",
            "mốc sương", "bệnh học", "phòng trị", "kháng sinh", "cẩm nang"
        ]):
            from app.services.rag_service import rag_service
            rag_diag = rag_service.diagnose_disease(user_query=user_message)
            executed_tools.append({
                "tool": "diagnose_agricultural_disease",
                "args": {"symptoms_or_description": user_message},
                "result": rag_diag,
            })
            reply_lines.append(
                f"🩺 **[Smart Farm AI Agent - RAG Disease Diagnosis]**\n"
                f"• Phân loại: {rag_diag.get('category')} ({rag_diag.get('species')})\n"
                f"• Bệnh lý chẩn đoán: **{rag_diag.get('disease_name')}**\n"
                f"• Triệu chứng ghi nhận: {rag_diag.get('text')}\n\n"
                f"📋 **Phác đồ can thiệp & điều trị y tế (RAG Knowledge Base):**\n"
                f"{rag_diag.get('answer')}"
            )

        # 9. Action: QUẢN LÝ NHÂN SỰ & ĐIỂM DANH FACE ID
        elif any(k in msg for k in ["nhân sự", "nhân viên", "điểm danh", "ai đang trực", "vào ca", "chấm công", "faceid", "khuôn mặt"]):
            if any(k in msg for k in ["điểm danh", "vào ca", "chấm công"]) and any(k in msg for k in ["nv", "tech", "cho", "bằng"]):
                id_match = re.findall(r"(nv[0-9]+|tech[\-_]?[0-9]+)", msg)
                staff_id = id_match[0].upper() if id_match else "NV01"
                pen_id = "123"
                if "a02" in msg or "a2" in msg:
                    pen_id = "PEN-A02"
                elif "cách ly" in msg or "iso" in msg:
                    pen_id = "PEN-ISO-01"
                elif "b01" in msg or "b1" in msg:
                    pen_id = "PEN-B01"

                res = check_in_staff_face(staff_id=staff_id, pen_id=pen_id, note="Điểm danh qua chat AI")
                executed_tools.append({"tool": "check_in_staff_face", "args": {"staff_id": staff_id, "pen_id": pen_id}, "result": res})
                reply_lines.append(f"🤖 [Smart Farm Agent]: {res}")
            elif any(k in msg for k in ["danh sách", "tất cả", "các nhân viên", "có ai"]):
                res = get_staff_list()
                executed_tools.append({"tool": "get_staff_list", "args": {}, "result": res})
                reply_lines.append(f"🤖 [Smart Farm Agent]: Danh sách nhân sự trang trại:\n{res}")
            else:
                summary = get_today_attendance_summary()
                executed_tools.append({"tool": "get_today_attendance_summary", "args": {}, "result": summary})
                reply_lines.append(f"🤖 [Smart Farm Agent]: Tình hình điểm danh nhân sự hôm nay:\n{summary}")

        else:
            reply_lines.append(
                f"🤖 [Smart Farm AI Agent]: Tôi đã nhận yêu cầu: '{user_message}'.\n"
                "Tôi hỗ trợ bạn quản lý linh hoạt giữa các chuồng:\n"
                "- 👤 Nhân sự FaceID: 'Điểm danh cho nhân viên NV01 tại chuồng 123', 'Danh sách nhân sự trang trại'\n"
                "- 🚚 Đổi chuồng: 'Chuyển con HEO-102 sang chuồng cách ly PEN-ISO-01'\n"
                "- 🩺 Chẩn đoán RAG: 'Chẩn đoán bệnh heo bị sốt cao tai tím', 'Phác đồ điều trị bệnh đạo ôn'\n"
                "- 🔎 Tra cứu chuồng: 'Xem thông tin chuồng PEN-A02', 'Danh sách các chuồng'\n"
                "- 🌬️ Điều khiển thiết bị: 'Bật quạt chuồng A2', 'Bật đèn sưởi chuồng 123'\n"
                "- 🥣 Cho ăn: 'Cho chuồng PEN-A02 ăn 10 kg cám'\n"
                "- 🩺 Sức khỏe: 'Cập nhật cá thể HEO-102 đã khỏi sốt'"
            )

        return {
            "reply": "\n\n".join(reply_lines),
            "tool_calls": executed_tools,
        }

    async def chat(self, user_message: str, history: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        """
        Process chat with Smart Farm AI Agent:
        1. Injects live farm context across all pens + recent conversation history.
        2. Dispatches to Gemini API with registered tools.
        3. Seamlessly fallbacks to rule engine if API key is not configured or errors out.
        """
        if not self._genai_client:
            return self._fallback_intent_engine(user_message)

        try:
            from google.genai import types

            recent_turns_text = ""
            if history:
                turns = []
                for h in history[-6:]:
                    role_label = "Người dùng" if h.get("sender") == "user" else "Trợ lý AI"
                    turns.append(f"{role_label}: {h.get('content', '')}")
                if turns:
                    recent_turns_text = "\n\nLỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY VỚI NGƯỜI DÙNG:\n" + "\n".join(turns) + "\n"

            system_instruction = self.get_system_prompt_with_mcp_context() + recent_turns_text

            tools_list = [
                transfer_animal_pen,
                get_pen_status,
                manage_pen,
                control_device,
                log_feeding,
                update_animal_health,
                manage_inventory,
                manage_schedule,
                create_system_alert,
                search_agricultural_knowledge,
                diagnose_agricultural_disease,
                get_staff_list,
                check_in_staff_face,
                get_today_attendance_summary,
            ]

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                temperature=0.2,
            )

            response = self._genai_client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=user_message,
                config=config,
            )

            executed_tools = []
            if hasattr(response, "function_calls") and response.function_calls:
                for fc in response.function_calls:
                    executed_tools.append({
                        "tool": fc.name,
                        "args": dict(fc.args) if fc.args else {},
                    })

            reply_text = response.text if response.text else "Yêu cầu trang trại đã được xử lý thành công."

            return {
                "reply": reply_text,
                "tool_calls": executed_tools,
            }

        except Exception as e:
            logger.error(f"Error invoking Gemini model: {e}. Switching to fallback engine.")
            res = self._fallback_intent_engine(user_message)
            res["reply"] += f"\n\n*(Lưu ý: Gemini API gặp lỗi [{str(e)}], hệ thống đã tự động xử lý qua Smart Farm Rule Engine)*"
            return res

    async def diagnose_multimodal(
        self,
        user_query: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        content_type: Optional[str] = "image/jpeg",
    ) -> dict[str, Any]:
        """
        Multimodal agricultural disease diagnosis integrating RAG context and visual recognition.
        Directly inherits and enhances the workflow from stem/app/services/agent.py.
        """
        from app.services.rag_service import rag_service
        return rag_service.diagnose_disease(
            user_query=user_query,
            image_bytes=image_bytes,
            image_mime_type=content_type,
        )


agent_service = AIAgentService()
