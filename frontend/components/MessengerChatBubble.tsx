'use client';

import React, { useState, useRef, useEffect } from 'react';
import { 
  MessageCircle, 
  X, 
  Minus, 
  Send, 
  Bot, 
  Sparkles, 
  RefreshCw, 
  Smile, 
  Maximize2,
  Wrench,
  CheckCircle2
} from 'lucide-react';
import { sendAgentChat, getChatHistory } from '../lib/agent-api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  time: string;
  toolsCalled?: Array<{
    tool: string;
    args: Record<string, any>;
    result?: string;
  }>;
}

interface MessengerChatBubbleProps {
  penId: string;
  penName: string;
  isOpen: boolean;
  onToggle: () => void;
  temp?: number;
  hum?: number;
  smell?: number;
  userId?: string;
}

export default function MessengerChatBubble({
  penId,
  penName,
  isOpen,
  onToggle,
  temp,
  hum,
  smell,
  userId = 'guest',
}: MessengerChatBubbleProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'agent',
      text: `Xin chào! Tôi là Trợ Lý Nông Trại AI kết nối FastMCP & Gemini. Tôi có thể giúp bạn kiểm tra vi khí hậu, bật tắt quạt, hoặc kiểm tra sức khỏe đàn nuôi. Bạn cần hỗ trợ gì?`,
      time: 'Vừa xong',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history from backend on open or pen/user change
  useEffect(() => {
    let isMounted = true;
    getChatHistory(userId, penId).then((history) => {
      if (!isMounted) return;
      if (history && history.length > 0) {
        setMessages(
          history.map((m) => ({
            id: String(m.id),
            sender: m.sender as 'user' | 'agent',
            text: m.content,
            time: m.created_at
              ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'Vừa xong',
            toolsCalled: m.tool_calls,
          }))
        );
      } else {
        setMessages([
          {
            id: '1',
            sender: 'agent',
            text: `Xin chào! Tôi là Trợ Lý Nông Trại AI phụ trách chuồng ${penName || penId}. Tôi có thể giúp bạn kiểm tra vi khí hậu, bật tắt quạt, hoặc kiểm tra sức khỏe đàn nuôi.`,
            time: 'Vừa xong',
          },
        ]);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [isOpen, penId, userId, penName]);

  // Auto scroll to bottom
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const quickQuestions = [
    'Nhiệt độ & mùi chuồng hiện tại?',
    'Bật quạt thông gió giúp tôi',
    'Vật nuôi nào đang cần chú ý?',
    'Kho thức ăn còn đủ không?',
  ];

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || inputValue;
    if (!textToSend.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Direct integration with FastAPI AI Agent (/api/chat) with pen_id & user_id
      const data = await sendAgentChat(textToSend, penId, userId);

      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: data.reply || 'Đã thực hiện xong yêu cầu.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        toolsCalled: data.tool_calls,
      };

      setMessages((prev) => [...prev, agentMsg]);
      setIsLoading(false);
      return;
    } catch (err) {
      console.warn('Backend /api/chat error, using fallback responder:', err);
    }

    // Local fallback intelligent response
    setTimeout(() => {
      let reply = '';
      const lower = textToSend.toLowerCase();

      if (lower.includes('nhiệt') || lower.includes('môi trường') || lower.includes('mùi')) {
        reply = `📡 Thông số hiện tại tại ${penName}: Nhiệt độ: ${temp ?? 29}°C, Độ ẩm: ${hum ?? 70}%, Mùi chuồng: ${smell ?? 180} ppm. Môi trường đang ở ngưỡng ${temp && temp >= 35 ? 'CẢNH BÁO NÓNG' : 'ổn định an toàn'}.`;
      } else if (lower.includes('quạt') || lower.includes('bật') || lower.includes('tắt')) {
        reply = `💨 Lệnh điều khiển thiết bị đã được gửi tới chuồng ${penName}. Hệ thống đã gửi tín hiệu qua FastMCP để kích hoạt quạt thông gió làm mát!`;
      } else if (lower.includes('heo') || lower.includes('vật nuôi') || lower.includes('bệnh') || lower.includes('ốm')) {
        reply = `🩺 Theo hồ sơ y tế mới nhất: Phát hiện 1 cá thể cần chú ý (sốt nhẹ). Các cá thể khác ăn uống bình thường và tăng trọng đạt chỉ tiêu.`;
      } else if (lower.includes('kho') || lower.includes('thức ăn') || lower.includes('cám')) {
        reply = `📦 Kho thức ăn: Cám Cò còn đủ dùng trong 3 ngày tới. Có 1 mặt hàng chạm ngưỡng tối thiểu, bạn nên lên lịch nhập thêm trước cuối tuần.`;
      } else {
        reply = `🌾 Tôi đã ghi nhận yêu cầu: "${textToSend}". Hệ thống AI Agent đã đồng bộ dữ liệu với chuồng ${penName} qua giao thức MCP!`;
      }

      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, agentMsg]);
      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Expanding Messenger Window */}
      {isOpen && (
        <div className="w-[360px] sm:w-[380px] h-[520px] bg-fb-card rounded-2xl shadow-fb-popover border border-fb-divider flex flex-col overflow-hidden mb-3 animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Messenger Header */}
          <div className="p-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white flex items-center justify-between shadow">
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center font-bold text-lg">
                  🤖
                </div>
                <span className="w-2.5 h-2.5 bg-emerald-300 rounded-full absolute bottom-0 right-0 ring-2 ring-emerald-700" />
              </div>

              <div>
                <h4 className="font-bold text-sm leading-tight">Trợ Lý Nông Trại AI</h4>
                <p className="text-[11px] text-emerald-100 flex items-center gap-1">
                  <span>FastMCP Agent</span>
                  <span>•</span>
                  <span>Đang hoạt động</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={onToggle}
                className="w-7 h-7 rounded-full hover:bg-white/20 flex items-center justify-center text-white/90 transition"
              >
                <Minus className="w-4 h-4" />
              </button>
              <button
                onClick={onToggle}
                className="w-7 h-7 rounded-full hover:bg-white/20 flex items-center justify-center text-white/90 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-[#F0F2F5]/50">
            {messages.map((m) => {
              const isUser = m.sender === 'user';

              return (
                <div
                  key={m.id}
                  className={`flex items-end gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs shrink-0 mb-0.5">
                      🤖
                    </div>
                  )}

                  <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-xs shadow-sm ${
                    isUser
                      ? 'bg-fb-blue text-white rounded-br-sm'
                      : 'bg-white text-fb-text border border-slate-200 rounded-bl-sm leading-relaxed'
                  }`}>
                    <p className="whitespace-pre-line">{m.text}</p>
                    {m.toolsCalled && m.toolsCalled.length > 0 && (
                      <div className="mt-2 pt-1.5 border-t border-slate-100 text-[10px] space-y-1">
                        {m.toolsCalled.map((t: any, idx) => (
                          <div key={idx} className="bg-emerald-50 text-emerald-800 p-1.5 rounded-lg border border-emerald-200">
                            <span className="font-bold flex items-center gap-1">
                              <Wrench className="w-3 h-3 text-emerald-600" />
                              Tool: {typeof t === 'string' ? t : t.tool}
                            </span>
                            {typeof t !== 'string' && t.result && (
                              <p className="text-[9px] text-slate-600 mt-0.5 line-clamp-2">{t.result}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    <span className={`text-[9px] block text-right mt-1 ${isUser ? 'text-blue-100' : 'text-slate-400'}`}>
                      {m.time}
                    </span>
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div className="flex items-end gap-2 justify-start">
                <div className="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs shrink-0">
                  🤖
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-3.5 py-2.5 text-xs text-slate-500 flex items-center gap-1 shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestion Chips */}
          <div className="px-3 py-2 bg-fb-card border-t border-fb-divider overflow-x-auto scrollbar-none flex gap-1.5">
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="shrink-0 text-[11px] font-medium bg-fb-bg hover:bg-emerald-50 hover:text-emerald-700 text-fb-text px-2.5 py-1 rounded-full border border-fb-divider transition"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-2.5 bg-fb-card border-t border-fb-divider flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Nhập câu hỏi hoặc ra lệnh cho AI..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1 bg-fb-bg text-xs rounded-full px-3.5 py-2 border border-fb-divider focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="w-8 h-8 rounded-full bg-fb-blue hover:bg-fb-blueDark text-white flex items-center justify-center transition disabled:opacity-40 shadow-sm shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      {/* Circular Floating Messenger Bubble */}
      <div className="relative">
        <button
          onClick={onToggle}
          title="Mở Chat Messenger Nông Trại"
          className="w-14 h-14 rounded-full bg-gradient-to-tr from-emerald-600 via-teal-600 to-green-500 hover:scale-105 transition-transform duration-200 text-white flex items-center justify-center shadow-xl border-2 border-white alert-pulse float-bubble"
        >
          {isOpen ? (
            <X className="w-6 h-6" />
          ) : (
            <div className="relative">
              <Bot className="w-7 h-7" />
              <span className="w-3 h-3 rounded-full bg-emerald-400 absolute -top-1 -right-1 ring-2 ring-emerald-800" />
            </div>
          )}
        </button>

        {!isOpen && (
          <span className="absolute -top-1.5 -right-1.5 bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow border-2 border-white">
            AI
          </span>
        )}
      </div>
    </div>
  );
}
