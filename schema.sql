-- ====================================================================
-- SUPABASE POSTGRESQL MIGRATION & REPAIR SCRIPT (CHẠY TRÊN SUPABASE SQL EDITOR)
-- Sửa toàn bộ lỗi xung đột giữa database.sql cũ và hệ thống Smart Farm mới
-- Chạy script này an toàn (Idempotent - có thể chạy nhiều lần không lỗi)
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. TẠO CÁC BẢNG NẾU CHƯA CÓ
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.pens (
    id TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    user_id UUID DEFAULT auth.uid(),
    type TEXT DEFAULT 'livestock',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.env_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    smell_level DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.devices (
    id TEXT NOT NULL PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE CASCADE,
    name TEXT,
    is_active BOOLEAN DEFAULT false,
    pin_number INTEGER,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.animals (
    id TEXT NOT NULL PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    species TEXT DEFAULT 'Heo',
    weight DOUBLE PRECISION DEFAULT 0.0,
    target_weight DOUBLE PRECISION DEFAULT 100.0,
    feeding_status TEXT DEFAULT 'Normal',
    status TEXT DEFAULT 'Khoe',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.health_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    animal_id TEXT REFERENCES public.animals(id) ON DELETE CASCADE,
    type TEXT DEFAULT 'Routine',
    title TEXT,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.weight_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    animal_id TEXT REFERENCES public.animals(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.feed_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    food_name TEXT,
    amount DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.crops (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    plant_date DATE DEFAULT CURRENT_DATE,
    harvest_date DATE,
    status TEXT DEFAULT 'Growing',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.crop_growth_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crop_id BIGINT REFERENCES public.crops(id) ON DELETE CASCADE,
    size DOUBLE PRECISION,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.crop_care_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crop_id BIGINT REFERENCES public.crops(id) ON DELETE CASCADE,
    type TEXT,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.inventory (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID DEFAULT auth.uid(),
    name TEXT NOT NULL,
    category TEXT DEFAULT 'Feed',
    quantity DOUBLE PRECISION DEFAULT 0.0,
    unit TEXT DEFAULT 'kg',
    unit_price DOUBLE PRECISION DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.inventory_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID DEFAULT auth.uid(),
    item_name TEXT,
    action_type TEXT,
    amount DOUBLE PRECISION,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.usage_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID DEFAULT auth.uid(),
    item_name TEXT,
    amount DOUBLE PRECISION,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Hai bảng quan trọng cho AI Agent (trước đây bị thiếu trong database.sql):
CREATE TABLE IF NOT EXISTS public.alerts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.schedules (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    task_name TEXT NOT NULL,
    target_date DATE NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Bảng lưu lịch sử chat của từng người dùng & chuồng
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID DEFAULT auth.uid(),
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    sender TEXT NOT NULL CHECK (sender IN ('user', 'agent')),
    content TEXT NOT NULL,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phân hệ Quản Lý Nhân Sự & Điểm Danh FaceID (Standalone AI Vision Engine)
CREATE TABLE IF NOT EXISTS public.staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'Kỹ thuật viên',
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    phone TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.staff_attendance (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_id TEXT REFERENCES public.staff(id) ON DELETE CASCADE,
    staff_name TEXT NOT NULL,
    pen_id TEXT REFERENCES public.pens(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'present',
    confidence DOUBLE PRECISION DEFAULT 1.0,
    is_real BOOLEAN DEFAULT true,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- --------------------------------------------------------------------
-- 2. NÂNG CẤP VÀ SỬA CÁC CỘT BỊ THIẾU TRONG CÁC BẢNG HIỆN CÓ
-- --------------------------------------------------------------------

-- Bổ sung cột min_threshold & location cho bảng inventory nếu đã tồn tại từ trước
ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS min_threshold DOUBLE PRECISION DEFAULT 5.0;
ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS location TEXT DEFAULT 'Kho Chính';

-- Bổ sung ràng buộc UNIQUE cho inventory.name để chống trùng lặp và hỗ trợ ON CONFLICT
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'inventory_name_key'
    ) THEN
        ALTER TABLE public.inventory ADD CONSTRAINT inventory_name_key UNIQUE (name);
    END IF;
EXCEPTION
    WHEN duplicate_table OR duplicate_object THEN
        NULL;
END $$;

-- Bổ sung cột smell_level cho bảng env_logs nếu chưa có
ALTER TABLE public.env_logs ADD COLUMN IF NOT EXISTS smell_level DOUBLE PRECISION DEFAULT 0.0;
ALTER TABLE public.env_logs ADD COLUMN IF NOT EXISTS pen_id TEXT;

-- --------------------------------------------------------------------
-- 3. MỞ RỘNG RLS POLICIES ĐỂ TRÁNH LỖI 42501 (PERMISSION DENIED)
-- --------------------------------------------------------------------

DO $$ 
DECLARE 
    tbl text;
BEGIN
    FOR tbl IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
          AND tablename IN ('pens', 'env_logs', 'devices', 'animals', 'health_logs', 
                            'weight_logs', 'feed_logs', 'crops', 'crop_growth_logs', 
                            'crop_care_logs', 'inventory', 'inventory_logs', 'usage_logs', 
                            'alerts', 'schedules', 'field', 'chat_messages', 'staff', 'staff_attendance')
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
        EXECUTE format('DROP POLICY IF EXISTS allow_all_backend_ops ON public.%I;', tbl);
        EXECUTE format('CREATE POLICY allow_all_backend_ops ON public.%I FOR ALL USING (true) WITH CHECK (true);', tbl);
    END LOOP;
END $$;

-- --------------------------------------------------------------------
-- 4. NẠP DỮ LIỆU MẪU BAN ĐẦU THEO ĐÚNG THỨ TỰ RÀNG BUỘC KHÓA NGOẠI
-- --------------------------------------------------------------------

-- Bước 4.1: Nạp pens trước (vì các bảng khác tham chiếu pen_id)
INSERT INTO public.pens (id, name, type)
VALUES 
    ('123', 'Chuồng Nuôi Heo Thịt Khu A1', 'livestock'),
    ('PEN-A02', 'Chuồng Nuôi Heo Thịt Khu A2', 'livestock'),
    ('PEN-ISO-01', 'Khu Cách Ly Y Tế / Heo Bệnh', 'livestock'),
    ('PEN-B01', 'Khu Nhà Màng Dưa Lưới B1', 'crops')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- Bước 4.2: Nạp devices theo từng chuồng
INSERT INTO public.devices (id, pen_id, name, is_active, pin_number)
VALUES 
    ('DEV_FAN_01', '123', 'Quạt Thông Gió Hút Mùi', false, 1),
    ('DEV_MIST_01', '123', 'Hệ Thống Phun Sương Làm Mát', false, 2),
    ('DEV_LAMP_01', '123', 'Đèn Sưởi Hồng Ngoại', false, 3),
    ('DEV_FAN_02', 'PEN-A02', 'Quạt Hút Gió Chuồng A2', false, 1),
    ('DEV_UV_01', 'PEN-ISO-01', 'Đèn Khử Trùng UV Y Tế', false, 1),
    ('DEV_VALVE_01', 'PEN-B01', 'Hệ Thống Tưới Nhỏ Giọt Dưa', false, 1)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, pen_id = EXCLUDED.pen_id;

-- Bước 4.3: Nạp animals phân bố theo các chuồng
INSERT INTO public.animals (id, pen_id, species, weight, target_weight, feeding_status, status)
VALUES 
    ('HEO-101', '123', 'Heo Siêu Nạc', 65.5, 100.0, 'Normal', 'Khoe'),
    ('HEO-102', '123', 'Heo Siêu Nạc', 62.0, 100.0, 'An it', 'Sot nhe'),
    ('HEO-201', 'PEN-A02', 'Heo Siêu Nạc', 72.0, 100.0, 'Normal', 'Khoe'),
    ('HEO-ISO-01', 'PEN-ISO-01', 'Heo Lai Rừng', 48.0, 80.0, 'Normal', 'Khoe')
ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, pen_id = EXCLUDED.pen_id;

-- Bước 4.4: Nạp inventory
INSERT INTO public.inventory (name, category, quantity, unit, unit_price, min_threshold)
VALUES 
    ('Cám Con Cò Siêu Tăng Trọng', 'Feed', 85.0, 'kg', 15000.0, 20.0),
    ('Kháng Sinh Amoxicillin 50%', 'Medicine', 3.0, 'hộp', 120000.0, 5.0),
    ('Phân Bón NPK Dinh Dưỡng Dưa', 'Fertilizer', 15.0, 'kg', 25000.0, 30.0)
ON CONFLICT (name) DO UPDATE SET quantity = EXCLUDED.quantity;

-- Bước 4.5: Nạp schedules & alerts
INSERT INTO public.schedules (pen_id, task_name, target_date, status, note)
VALUES 
    ('123', 'Tiêm vắc xin phòng dịch cho lứa heo 102', CURRENT_DATE, 'pending', 'Theo dõi phản ứng sau tiêm 2h'),
    ('PEN-B01', 'Kiểm tra độ ngọt Brix trước thu hoạch', CURRENT_DATE + INTERVAL '2 days', 'pending', 'Lấy mẫu ngẫu nhiên 5 quả')
ON CONFLICT DO NOTHING;

INSERT INTO public.alerts (pen_id, alert_type, message, is_read)
VALUES 
    ('123', 'SYSTEM', 'Hệ thống Smart Farm AI Agent đã khởi động và kết nối chuồng 123.', false)
ON CONFLICT DO NOTHING;

-- Bước 4.6: Nạp dữ liệu nhân sự mẫu ban đầu
INSERT INTO public.staff (id, name, role, pen_id, phone)
VALUES 
    ('NV01', 'Nguyễn Văn An', 'Quản lý trang trại', '123', '0901234567'),
    ('NV02', 'Trần Thị Bình', 'Bác sĩ thú y', 'PEN-ISO-01', '0912345678'),
    ('NV03', 'Lê Hoàng Long', 'Kỹ thuật viên IoT', 'PEN-A02', '0923456789'),
    ('NV04', 'Phạm Văn Cường', 'Kỹ sư nông học', 'PEN-B01', '0934567890')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, role = EXCLUDED.role;
