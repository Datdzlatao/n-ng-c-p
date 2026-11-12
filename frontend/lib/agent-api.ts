const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

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
