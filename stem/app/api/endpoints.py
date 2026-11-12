import base64
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from app.services.agent import agent, process_agent_response

router = APIRouter()

@router.post("/diagnose")
async def diagnose(
    user_query: str = Form(None), 
    image: UploadFile = File(None)
):
    try:
        message_content = []
        
        # Xử lý Text
        if user_query:
            message_content.append({"type": "text", "text": user_query})
        else:
            message_content.append({"type": "text", "text": "Hãy phân tích hình ảnh này và đưa ra chẩn đoán."})
            
        # Xử lý Ảnh gửi lên từ Client
        if image:
            image_data = await image.read()
            b64_image = base64.b64encode(image_data).decode("utf-8")
            # Bảo vệ trường hợp content_type bị rỗng
            content_type = image.content_type if image.content_type else "image/jpeg"
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{content_type};base64,{b64_image}"}
            })

        multimodal_message = HumanMessage(content=message_content)
        
        # Gọi Agent
        response = agent.invoke({"messages": [multimodal_message]})
        
        # Parse kết quả
        parsed_dict = process_agent_response(response)
        return JSONResponse(content=parsed_dict)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))