export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

export interface ChatResponse {
  reply: string;
  tool_calls: Array<{
    tool: string;
    args: Record<string, any>;
    result?: string;
  }>;
  timestamp?: string;
}

/**
 * Send message / instruction to AI Agent (FastMCP + Gemini)
 * Persists chat message per user & pen
 */
export async function sendAgentChat(
  message: string,
  penId?: string,
  userId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      pen_id: penId,
      user_id: userId || 'guest',
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Agent API Error (${res.status}): ${errorText}`);
  }

  return await res.json();
}

/**
 * Fetch persistent chat history for a specific user and pen
 */
export async function getChatHistory(
  userId: string,
  penId?: string
): Promise<Array<{
  id: string | number;
  sender: 'user' | 'agent';
  content: string;
  created_at: string;
  tool_calls?: any[];
}>> {
  try {
    const url = new URL(`${BACKEND_URL}/api/chat/history`);
    url.searchParams.append('user_id', userId);
    if (penId) url.searchParams.append('pen_id', penId);

    const res = await fetch(url.toString());
    if (!res.ok) return [];
    const data = await res.json();
    return data.messages || [];
  } catch (e) {
    console.error('Error fetching chat history:', e);
    return [];
  }
}

/**
 * Trigger Farm Morning Briefing (Gemini summary)
 */
export async function triggerDailyBriefing(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/scheduler/trigger-briefing`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Briefing Error: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Control IoT Device via API
 */
export async function controlDeviceViaAPI(
  penId: string,
  deviceName: string,
  action: 'turn_on' | 'turn_off'
): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/devices/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pen_id: penId,
      device_name: deviceName,
      action,
    }),
  });

  return await res.json();
}

/**
 * Transfer Animal across pens
 */
export async function transferAnimalViaAPI(
  animalId: string,
  targetPenId: string,
  reason: string
): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/animals/transfer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      animal_id: animalId,
      target_pen_id: targetPenId,
      reason,
    }),
  });

  return await res.json();
}

/**
 * Connect to FastAPI WebSocket for Realtime Agent Events
 */
export function connectAgentWebSocket(
  onEvent: (event: string, data: any) => void,
  onStatusChange: (status: 'connected' | 'disconnected') => void
): () => void {
  let ws: WebSocket | null = null;
  let shouldReconnect = true;
  let reconnectTimeout: NodeJS.Timeout;

  const connect = () => {
    try {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('✅ Connected to Smart Farm AI Agent WebSocket');
        onStatusChange('connected');
      };

      ws.onmessage = (messageEvent) => {
        try {
          const packet = JSON.parse(messageEvent.data);
          console.log('⚡ Agent WebSocket Packet:', packet);
          if (packet.event) {
            onEvent(packet.event, packet.data);
          }
        } catch (e) {
          console.error('Error parsing WebSocket packet:', e);
        }
      };

      ws.onclose = () => {
        onStatusChange('disconnected');
        if (shouldReconnect) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    } catch (err) {
      onStatusChange('disconnected');
      if (shouldReconnect) {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    }
  };

  connect();

  return () => {
    shouldReconnect = false;
    clearTimeout(reconnectTimeout);
    if (ws) {
      ws.close();
    }
  };
}

// ==========================================
// STAFF & FACE ATTENDANCE & UNIFORM APIS
// ==========================================

export interface Staff {
  id: string;
  name: string;
  role?: string;
  pen_id?: string;
  phone?: string;
  avatar_url?: string;
}

export interface AttendanceRecord {
  id?: number;
  staff_id: string;
  staff_name: string;
  pen_id?: string;
  status: string;
  check_type?: string;
  confidence?: number;
  is_real?: boolean;
  note?: string;
  created_at?: string;
}

/**
 * Get full staff list
 */
export async function getStaffList(): Promise<Staff[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/staff`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error('Error fetching staff list:', e);
    return [];
  }
}

/**
 * Face Check-in / Attendance API (Base64)
 */
export async function checkInStaff(payload: {
  staffId?: string;
  imageBase64?: string;
  penId?: string;
  checkType?: string;
  note?: string;
}): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/staff/checkin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      staff_id: payload.staffId,
      image_base64: payload.imageBase64,
      pen_id: payload.penId || '123',
      check_type: payload.checkType || 'check_in',
      note: payload.note || '',
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || 'Lỗi khi điểm danh khuôn mặt');
  }

  return await res.json();
}

/**
 * Face Check-in / Attendance API (File Upload)
 */
export async function checkInStaffUpload(
  file: File,
  penId: string = '123',
  checkType: string = 'check_in',
  staffId?: string
): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('pen_id', penId);
  formData.append('check_type', checkType);
  if (staffId) formData.append('staff_id', staffId);

  const res = await fetch(`${BACKEND_URL}/api/staff/checkin-upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || 'Lỗi khi upload ảnh chấm công');
  }

  return await res.json();
}

/**
 * Get recent staff attendance logs
 */
export async function getStaffAttendanceHistory(limit: number = 20): Promise<AttendanceRecord[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/staff/attendance?limit=${limit}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error('Error fetching attendance history:', e);
    return [];
  }
}

/**
 * Register new staff FaceID
 */
export async function enrollStaffFace(
  staffId: string,
  staffName: string,
  file: File,
  role: string = 'Kỹ thuật viên',
  penId: string = '123'
): Promise<any> {
  const formData = new FormData();
  formData.append('staff_id', staffId);
  formData.append('staff_name', staffName);
  formData.append('role', role);
  formData.append('pen_id', penId);
  formData.append('file', file);

  const res = await fetch(`${BACKEND_URL}/api/staff/enroll`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || 'Lỗi khi đăng ký FaceID');
  }

  return await res.json();
}

/**
 * Reload FaceID from known_faces folder
 */
export async function reloadStaffFacesAPI(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/staff/reload-faces`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Không thể làm mới danh sách khuôn mặt');
  return await res.json();
}

/**
 * Check Standalone AI Engine Health
 */
export async function getVisionHealth(): Promise<any> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/staff/vision-status`);
    if (!res.ok) return { online: false };
    return await res.json();
  } catch {
    return { online: false };
  }
}

/**
 * Scan Full-Body & Inspect Uniform via Base64
 */
export async function scanUniformAPI(
  imageBase64: string,
  weekday: number = -1,
  returnAnnotated: boolean = true
): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/uniform/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_base64: imageBase64,
      weekday,
      return_annotated: returnAnnotated,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Lỗi khi quét toàn thân và kiểm tra đồng phục');
  }

  return await res.json();
}

/**
 * Scan Full-Body & Inspect Uniform via File Upload
 */
export async function scanUniformUploadAPI(
  file: File,
  weekday: number = -1
): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('weekday', weekday.toString());

  const res = await fetch(`${BACKEND_URL}/api/uniform/scan-upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Lỗi khi upload ảnh kiểm tra đồng phục');
  }

  return await res.json();
}

/**
 * Live Camera Frame Real-Time AI Scan
 */
export async function liveScanStaffAPI(params: {
  imageBase64: string;
  penId?: string;
  checkType?: string;
  weekday?: number;
  autoCheckin?: boolean;
  returnAnnotated?: boolean;
}): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/staff/live-scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_base64: params.imageBase64,
      pen_id: params.penId || '123',
      check_type: params.checkType || 'check_in',
      weekday: params.weekday !== undefined ? params.weekday : -1,
      auto_checkin: params.autoCheckin !== undefined ? params.autoCheckin : true,
      return_annotated: params.returnAnnotated || false,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Lỗi khi quét live camera');
  }

  return await res.json();
}

/**
 * Camera Hardware Live Stream Controls
 */
export async function getCameraStreamStatusAPI(): Promise<any> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/camera/status`);
    if (!res.ok) return { is_running: false };
    return await res.json();
  } catch {
    return { is_running: false };
  }
}

export async function getCameraLatestTelemetryAPI(): Promise<any> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/camera/latest`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function startCameraDeviceAPI(source: string = '0', weekday?: number): Promise<any> {
  const url = `${BACKEND_URL}/api/camera/start?source=${encodeURIComponent(source)}${weekday !== undefined ? `&weekday=${weekday}` : ''}`;
  const res = await fetch(url, { method: 'POST' });
  return await res.json();
}

export async function stopCameraDeviceAPI(): Promise<any> {
  const res = await fetch(`${BACKEND_URL}/api/camera/stop`, { method: 'POST' });
  return await res.json();
}
