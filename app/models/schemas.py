from datetime import date, datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


def get_current_utc() -> datetime:
    return datetime.now(timezone.utc)


# ==========================================
# 1. PENS SCHEMAS (CHUỒNG TRẠI / KHU VỰC)
# ==========================================
class PenBase(BaseModel):
    id: str = Field(..., description="Mã chuồng trại (ví dụ: '123', 'PEN_A01')")
    name: Optional[str] = Field(default="Chuồng Mới", description="Tên định danh chuồng")
    type: Optional[str] = Field(default="livestock", description="Phân loại: livestock, crops, greenhouse")
    user_id: Optional[str] = Field(default=None, description="UUID của chủ sở hữu chuồng")


class PenCreate(PenBase):
    pass


class PenInDB(PenBase):
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. DEVICES SCHEMAS (THIẾT BỊ IOT CHUỒNG)
# ==========================================
class DeviceBase(BaseModel):
    id: str = Field(..., description="Mã thiết bị")
    pen_id: Optional[str] = Field(default=None, description="Chuồng được lắp đặt")
    name: str = Field(..., description="Tên thiết bị: quạt hút, phun sương, đèn sưởi...")
    is_active: bool = Field(default=False, description="Trạng thái Bật (True) / Tắt (False)")
    pin_number: Optional[int] = Field(default=1, description="Chân GPIO điều khiển")


class DeviceControlRequest(BaseModel):
    pen_id: Optional[str] = Field(default=None, description="Mã chuồng")
    device_name: Optional[str] = Field(default=None, description="Tên thiết bị (quạt, đèn...)")
    device_id: Optional[str] = Field(default=None, description="Hoặc ID thiết bị")
    action: Literal["turn_on", "turn_off", "toggle"] = Field(..., description="Hành động điều khiển")


class DeviceInDB(DeviceBase):
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. ENV LOGS SCHEMAS (CẢM BIẾN MÔI TRƯỜNG)
# ==========================================
class EnvLogBase(BaseModel):
    temperature: float = Field(..., description="Nhiệt độ môi trường (°C)")
    humidity: float = Field(..., description="Độ ẩm không khí (%)")
    smell_level: float = Field(default=0.0, description="Nồng độ mùi / khí chuồng (ppm hoặc chỉ số)")
    pen_id: Optional[str] = Field(default="123", description="Mã chuồng đo cảm biến")


class EnvLogCreate(EnvLogBase):
    pass


class EnvLogInDB(EnvLogBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. ANIMALS SCHEMAS (VẬT NUÔI)
# ==========================================
class AnimalBase(BaseModel):
    id: str = Field(..., description="Mã vật nuôi / thẻ tai (ví dụ: 'HEO-101')")
    pen_id: Optional[str] = Field(default="123", description="Chuồng đang nuôi")
    species: Optional[str] = Field(default="Heo", description="Loài (Heo, Bò, Gà...)")
    weight: Optional[float] = Field(default=0.0, description="Cân nặng hiện tại (kg)")
    target_weight: Optional[float] = Field(default=100.0, description="Cân nặng xuất chuồng mục tiêu")
    feeding_status: Optional[str] = Field(default="Normal", description="Trạng thái ăn uống (Normal, An it, Bo an)")
    status: Optional[str] = Field(default="Khoe", description="Trạng thái sức khỏe (Khoe, Sot, Benh, Cach ly)")


class AnimalHealthUpdate(BaseModel):
    animal_id: str
    status: str = Field(..., description="Trạng thái mới: Khoe, Sot, Cach ly, ...")
    note: Optional[str] = Field(default="", description="Chi tiết triệu chứng / chẩn đoán")
    type: Optional[str] = Field(default="Disease", description="Phân loại: Routine, Disease, Vaccine")


class AnimalTransferRequest(BaseModel):
    animal_id: str = Field(..., description="Mã vật nuôi cần chuyển chuồng (ví dụ: 'HEO-102')")
    target_pen_id: str = Field(..., description="Mã chuồng chuyển đến (ví dụ: 'PEN-ISO-01', 'PEN-A02')")
    reason: Optional[str] = Field(default="", description="Lý do chuyển chuồng (cách ly, tách đàn, xuất chuồng...)")


class AnimalInDB(AnimalBase):
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. CROPS SCHEMAS (CÂY TRỒNG / VỤ MÙA)
# ==========================================
class CropBase(BaseModel):
    name: str = Field(..., description="Tên loại cây / giống")
    pen_id: Optional[str] = Field(default=None, description="Khu vực trồng")
    quantity: Optional[int] = Field(default=1, description="Số lượng cây / luống")
    plant_date: Optional[date] = Field(default_factory=date.today)
    harvest_date: Optional[date] = None
    status: Optional[str] = Field(default="Growing", description="Giai đoạn: Growing, Flowering, Ripening, Harvested")


class CropInDB(CropBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. FEED LOGS SCHEMAS (CHO ĂN)
# ==========================================
class FeedLogCreate(BaseModel):
    pen_id: str = Field(..., description="Chuồng được cho ăn")
    food_name: str = Field(..., description="Tên loại thức ăn (khớp với kho inventory)")
    amount: float = Field(..., gt=0, description="Lượng thức ăn tiêu thụ (kg)")


class FeedLogInDB(FeedLogCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. INVENTORY SCHEMAS (KHO VẬT TƯ / THỨC ĂN)
# ==========================================
class InventoryBase(BaseModel):
    name: str = Field(..., min_length=1, description="Tên vật tư / thức ăn / thuốc")
    category: Optional[str] = Field(default="Feed", description="Phân loại: Feed, Medicine, Fertilizer, Equipment")
    quantity: float = Field(..., ge=0, description="Số lượng tồn kho (>= 0)")
    unit: str = Field(default="kg", description="Đơn vị tính (kg, lít, bao, cái, hộp, ...)")
    unit_price: Optional[float] = Field(default=0.0, ge=0, description="Đơn giá tham khảo")
    min_threshold: float = Field(default=5.0, ge=0, description="Ngưỡng cảnh báo tối thiểu")
    location: Optional[str] = Field(default="Kho Chính", description="Vị trí kho")


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    min_threshold: Optional[float] = Field(default=None, ge=0)
    location: Optional[str] = None


class InventoryInDB(InventoryBase):
    id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 8. SCHEDULES SCHEMAS (LỊCH TRÌNH CÔNG VIỆC)
# ==========================================
class ScheduleBase(BaseModel):
    task_name: str = Field(..., min_length=1, description="Tên công việc / lịch trình")
    target_date: date = Field(..., description="Ngày thực hiện (YYYY-MM-DD)")
    pen_id: Optional[str] = Field(default=None, description="Mã chuồng liên quan nếu có")
    status: Literal["pending", "done"] = Field(default="pending", description="Trạng thái: pending hoặc done")
    note: Optional[str] = Field(default="", description="Ghi chú chi tiết")


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    task_name: Optional[str] = None
    target_date: Optional[date] = None
    pen_id: Optional[str] = None
    status: Optional[Literal["pending", "done"]] = None
    note: Optional[str] = None


class ScheduleInDB(ScheduleBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 9. ALERTS SCHEMAS (CẢNH BÁO BẤT THƯỜNG)
# ==========================================
class AlertBase(BaseModel):
    alert_type: str = Field(..., description="Loại cảnh báo: ENV_ANOMALY, INVENTORY_LOW, HEALTH_WARNING, SYSTEM")
    message: str = Field(..., min_length=1, description="Nội dung cảnh báo chi tiết")
    pen_id: Optional[str] = Field(default=None, description="Mã chuồng liên quan")


class AlertCreate(AlertBase):
    pass


class AlertInDB(AlertBase):
    id: int
    is_read: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 10. WEBSOCKET & CHAT SCHEMAS
# ==========================================
class WebSocketMessage(BaseModel):
    event: str = Field(..., description="Tên sự kiện: alert, chat_response, env_update, device_update, ...")
    data: dict = Field(default_factory=dict, description="Dữ liệu payload")
    timestamp: datetime = Field(default_factory=get_current_utc)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Câu lệnh hoặc câu hỏi của người dùng gửi cho AI Agent")
    user_id: Optional[str] = Field(default="guest", description="ID người dùng để lưu và phân loại lịch sử")
    pen_id: Optional[str] = Field(default=None, description="Mã chuồng hiện tại người dùng đang thao tác")


class AgentChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=get_current_utc)


class ChatMessageResponse(BaseModel):
    id: Optional[int | str] = None
    user_id: str
    pen_id: Optional[str] = None
    sender: str
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    created_at: Optional[str] = None
