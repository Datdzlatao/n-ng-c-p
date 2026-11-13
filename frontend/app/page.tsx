'use client';

import React, { useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { 
  BACKEND_URL,
  connectAgentWebSocket, 
  triggerDailyBriefing, 
  controlDeviceViaAPI 
} from '../lib/agent-api';
import Navbar from '../components/Navbar';
import LeftSidebar from '../components/LeftSidebar';
import RightSidebar from '../components/RightSidebar';
import StoriesBar from '../components/StoriesBar';
import FeedAlertPinned from '../components/FeedAlertPinned';
import FeedBriefingCard from '../components/FeedBriefingCard';
import FeedEnvMonitor from '../components/FeedEnvMonitor';
import FeedStaffAttendance from '../components/FeedStaffAttendance';
import FeedLivestockCrops from '../components/FeedLivestockCrops';
import FeedInventory from '../components/FeedInventory';
import MessengerChatBubble from '../components/MessengerChatBubble';
import {
  ModalAddPen,
  ModalAddDevice,
  ModalAddAnimal,
  ModalHealth,
  ModalWeightTracking,
  ModalImport,
  ModalExport,
  ModalAddCrop,
  ModalCropTracking,
  ModalCropCare,
} from '../components/Modals';
import { ShieldAlert, Sparkles, Sprout, ArrowRight } from 'lucide-react';

export default function Home() {
  // --- AUTH STATE ---
  const [session, setSession] = useState<any>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isDemoMode, setIsDemoMode] = useState(false);

  // --- APP STATE ---
  const [currentMode, setCurrentMode] = useState<'livestock' | 'cultivation'>('livestock');
  const [pens, setPens] = useState<any[]>([]);
  const [currentPenId, setCurrentPenId] = useState<string>('');
  const [devices, setDevices] = useState<any[]>([]);
  const [animals, setAnimals] = useState<any[]>([]);
  const [crops, setCrops] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);

  // Environment Realtime Metrics
  const [envData, setEnvData] = useState({ temp: 28.5, hum: 70, smell: 150 });
  const [historyLogs, setHistoryLogs] = useState<any[]>([]);

  // Alerts & Notifications
  const [activeAlerts, setActiveAlerts] = useState<Record<string, string[]>>({});
  const [isMuted, setIsMuted] = useState(false);
  const [dismissedAlert, setDismissedAlert] = useState(false);
  const alarmSoundRef = useRef<HTMLAudioElement | null>(null);

  // Messenger Floating State
  const [isMessengerOpen, setIsMessengerOpen] = useState(false);

  // Agent Connection & Briefing
  const [wsConnected, setWsConnected] = useState(false);
  const [briefingText, setBriefingText] = useState('');
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);

  // Modals Open State
  const [modalOpen, setModalOpen] = useState({
    addPen: false,
    addDevice: false,
    addAnimal: false,
    health: false,
    weight: false,
    importInv: false,
    exportInv: false,
    addCrop: false,
    cropTrack: false,
    cropCare: false,
  });

  // Target item for detailed modal views
  const [selectedAnimalId, setSelectedAnimalId] = useState('');
  const [animalHealthLogs, setAnimalHealthLogs] = useState<any[]>([]);
  const [animalWeightLogs, setAnimalWeightLogs] = useState<any[]>([]);
  const [selectedCropId, setSelectedCropId] = useState('');
  const [cropGrowthLogs, setCropGrowthLogs] = useState<any[]>([]);
  const [cropCareLogs, setCropCareLogs] = useState<any[]>([]);

  // Realtime Live Toast State
  const [realtimeToast, setRealtimeToast] = useState<{ message: string; table: string } | null>(null);

  // Synchronization Refs (Avoid stale closures in realtime listeners)
  const currentPenIdRef = useRef(currentPenId);
  const currentModeRef = useRef(currentMode);
  const selectedAnimalIdRef = useRef(selectedAnimalId);
  const selectedCropIdRef = useRef(selectedCropId);

  useEffect(() => { currentPenIdRef.current = currentPenId; }, [currentPenId]);
  useEffect(() => { currentModeRef.current = currentMode; }, [currentMode]);
  useEffect(() => { selectedAnimalIdRef.current = selectedAnimalId; }, [selectedAnimalId]);
  useEffect(() => { selectedCropIdRef.current = selectedCropId; }, [selectedCropId]);

  const showRealtimeNotification = (table: string, actionDesc: string) => {
    setRealtimeToast({ table, message: actionDesc });
    setTimeout(() => {
      setRealtimeToast((curr) => (curr?.message === actionDesc ? null : curr));
    }, 4500);
  };

  // 1. Initialize Audio & Auth Listener
  useEffect(() => {
    alarmSoundRef.current = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) loadInitialData(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session) loadInitialData(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  // 2. Connect to Agent WebSocket for Live Events
  useEffect(() => {
    const disconnect = connectAgentWebSocket(
      async (event, data) => {
        const activePen = currentPenIdRef.current;
        if (event === 'device_update') {
          setDevices((prev) =>
            prev.map((d) => (
              d.name.toLowerCase().includes((data.name || '').toLowerCase()) || 
              String(d.id).trim() === String(data.id || '').trim() 
                ? { ...d, is_active: data.is_active } 
                : d
            ))
          );
          if (activePen) await loadPenData(activePen);
        } else if (event === 'animal_transfer') {
          if (activePen) await loadPenData(activePen);
        } else if (event === 'briefing') {
          if (data && data.content) {
            setBriefingText(data.content);
          }
        } else if (event === 'alert') {
          setActiveAlerts((prev) => ({
            ...prev,
            [data.pen_id || 'unknown']: [data.message],
          }));
        } else if (event === 'staff_checkin') {
          const actionText = data.check_type === 'check_out' ? 'tan ca' : 'vào ca';
          showRealtimeNotification('staff', `👤 Nhân sự ${data.staff_name || data.staff_id} đã ${actionText} (${data.pen_id || 'Trang trại'})`);
        }
      },
      (status) => setWsConnected(status === 'connected')
    );

    return () => disconnect();
  }, []);

  // Handle Trigger Briefing
  const handleTriggerBriefing = async () => {
    setIsBriefingLoading(true);
    try {
      const res = await triggerDailyBriefing();
      if (res && res.briefing && res.briefing.content) {
        setBriefingText(res.briefing.content);
      }
    } catch (e) {
      console.error('Trigger briefing error:', e);
    } finally {
      setIsBriefingLoading(false);
    }
  };

  // 3. Alarm Loop: Beeps when problem pens exist and not muted
  useEffect(() => {
    const interval = setInterval(() => {
      const problemPens = Object.keys(activeAlerts);
      if (problemPens.length > 0 && !isMuted && alarmSoundRef.current) {
        alarmSoundRef.current.play().catch(() => {});
      }
    }, 6000);

    return () => clearInterval(interval);
  }, [activeAlerts, isMuted]);

  // 3. Load Initial Farm Data
  const loadInitialData = async (activeSession = session) => {
    await fetchPens(activeSession);
    await fetchInventory();
  };

  // 4. Fetch Pens based on Mode & User Isolation
  const fetchPens = async (activeSession = session) => {
    let query = supabase.from('pens').select('*').eq('type', currentModeRef.current);

    // Tách biệt mỗi user một khu vực chuồng riêng
    const userId = activeSession?.user?.id;
    if (userId) {
      query = query.eq('user_id', userId);
    }

    const { data, error } = await query;

    if (data && data.length > 0) {
      setPens((prev) => (JSON.stringify(prev) === JSON.stringify(data) ? prev : data));
      // Giữ nguyên chuồng người dùng đang chọn nếu vẫn tồn tại, tránh bị nhảy về chuồng đầu tiên khi refetch
      const currentSelected = currentPenIdRef.current;
      const exists = data.some(
        (p: any) => String(p.id).trim().toLowerCase() === String(currentSelected).trim().toLowerCase()
      );
      const activeId = exists ? currentSelected : data[0].id;
      if (currentPenIdRef.current !== activeId) {
        setCurrentPenId(activeId);
        currentPenIdRef.current = activeId;
      }
      await loadPenData(activeId);
    } else if (userId) {
      // User đã đăng nhập nhưng chưa có chuồng -> Tự động khởi tạo chuồng mặc định riêng cho user
      const defaultPenId = `PEN-${userId.substring(0, 4).toUpperCase()}-01`;
      const defaultPenName = currentModeRef.current === 'livestock' ? 'Chuồng Nuôi Cá Nhân Khu 1' : 'Vườn Trồng Cá Nhân Khu 1';
      const starterPen = {
        id: defaultPenId,
        name: defaultPenName,
        type: currentModeRef.current,
        user_id: userId,
      };
      await supabase.from('pens').insert([starterPen]);
      setPens([starterPen]);
      setCurrentPenId(starterPen.id);
      currentPenIdRef.current = starterPen.id;
      await loadPenData(starterPen.id);
    } else {
      // Fallback Seed Pens if DB is empty or in Demo Mode
      const fallbackPens = currentModeRef.current === 'livestock' 
        ? [{ id: '123', name: 'Chuồng Heo Thịt Khu A1', type: 'livestock' }, { id: 'PEN-ISO-01', name: 'Khu Cách Ly Y Tế', type: 'livestock' }]
        : [{ id: 'PEN-B01', name: 'Khu Nhà Màng Dưa Lưới B1', type: 'cultivation' }];
      setPens((prev) => (JSON.stringify(prev) === JSON.stringify(fallbackPens) ? prev : fallbackPens));
      const currentSelected = currentPenIdRef.current;
      const exists = fallbackPens.some(
        (p: any) => String(p.id).trim().toLowerCase() === String(currentSelected).trim().toLowerCase()
      );
      const activeId = exists ? currentSelected : fallbackPens[0].id;
      if (currentPenIdRef.current !== activeId) {
        setCurrentPenId(activeId);
        currentPenIdRef.current = activeId;
      }
      await loadPenData(activeId);
    }
  };

  // Change Mode (Livestock vs Cultivation)
  const handleModeChange = (newMode: 'livestock' | 'cultivation') => {
    setCurrentMode(newMode);
  };

  useEffect(() => {
    fetchPens();
  }, [currentMode]);

  // Load Specific Pen Data - Tự động so sánh và chỉ re-render khi DB có thay đổi thực sự
  const loadPenData = async (penId: string) => {
    if (!penId) return;

    // Devices: Luôn map pin_number sang pin để tương thích toàn bộ UI
    const { data: devs } = await supabase.from('devices').select('*').eq('pen_id', penId).order('id');
    if (devs) {
      const formattedDevs = devs.map((d: any) => ({ ...d, pin: d.pin_number ?? d.pin }));
      setDevices((prev) => (JSON.stringify(prev) === JSON.stringify(formattedDevs) ? prev : formattedDevs));
    }

    // Tải cả vật nuôi và cây trồng cho chuồng đang chọn
    const { data: anis } = await supabase.from('animals').select('*').eq('pen_id', penId).order('id');
    if (anis) {
      setAnimals((prev) => (JSON.stringify(prev) === JSON.stringify(anis) ? prev : anis));
    }

    const { data: crps } = await supabase.from('crops').select('*').eq('pen_id', penId).order('id');
    if (crps) {
      setCrops((prev) => (JSON.stringify(prev) === JSON.stringify(crps) ? prev : crps));
    }

    // Latest Environment Sensor Log
    const { data: envs } = await supabase
      .from('env_logs')
      .select('*')
      .eq('pen_id', penId)
      .order('created_at', { ascending: false })
      .limit(6);

    if (envs && envs.length > 0) {
      const latest = envs[0];
      setEnvData((prev) => (
        prev.temp === latest.temperature &&
        prev.hum === latest.humidity &&
        prev.smell === (latest.smell_level || 0)
          ? prev
          : { temp: latest.temperature, hum: latest.humidity, smell: latest.smell_level || 0 }
      ));

      // Parse history
      const formatted = envs.reverse().map((e: any) => ({
        time: new Date(e.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        temp: e.temperature,
        hum: e.humidity,
        smell: e.smell_level || 0,
      }));
      setHistoryLogs((prev) => (JSON.stringify(prev) === JSON.stringify(formatted) ? prev : formatted));

      checkSensorAlert(penId, latest);
    } else {
      setEnvData({ temp: 28.5, hum: 70, smell: 140 });
    }
  };

  // Check and Register Alert
  const checkSensorAlert = (penId: string, data: any) => {
    const issues: string[] = [];
    if (data.temperature >= 35) issues.push(`Nóng quá ngưỡng (${data.temperature}°C)`);
    if (data.humidity >= 90) issues.push(`Ẩm ướt cao (${data.humidity}%)`);
    if (data.smell_level >= 400) issues.push(`Mùi hôi nguy hiểm (${data.smell_level} ppm)`);

    setActiveAlerts((prev) => {
      const copy = { ...prev };
      if (issues.length > 0) copy[penId] = issues;
      else delete copy[penId];
      return copy;
    });
  };

  // 5. Fetch Inventory - Chỉ cập nhật khi kho có thay đổi thực tế
  const fetchInventory = async () => {
    const { data } = await supabase.from('inventory').select('*').order('category');
    if (data) {
      setInventory((prev) => (JSON.stringify(prev) === JSON.stringify(data) ? prev : data));
    }
  };

  // 6. Supabase Full Realtime Subscription Across All Database Tables (Khởi tạo 1 lần duy nhất)
  useEffect(() => {
    const channelName = `farm-sync-${Date.now()}`;
    const channel = supabase.channel(channelName);
    const isSameId = (a: any, b: any) => String(a ?? '').trim().toLowerCase() === String(b ?? '').trim().toLowerCase();

    channel
      // A. env_logs: Cảm biến môi trường
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'env_logs' },
        (payload: any) => {
          const newLog = payload.new;
          if (!newLog) return;
          checkSensorAlert(newLog.pen_id, newLog);

          if (isSameId(newLog.pen_id, currentPenIdRef.current)) {
            setEnvData({
              temp: newLog.temperature,
              hum: newLog.humidity,
              smell: newLog.smell_level || 0,
            });
            setHistoryLogs((prev) => [
              ...prev.slice(1),
              {
                time: new Date(newLog.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                temp: newLog.temperature,
                hum: newLog.humidity,
                smell: newLog.smell_level || 0,
              },
            ]);
            showRealtimeNotification('env_logs', `Cảm biến chuồng ${newLog.pen_id}: ${newLog.temperature}°C, ${newLog.humidity}%, Mùi ${newLog.smell_level || 0}`);
          }
        }
      )
      // B. devices: Thiết bị IoT bật/tắt hoặc thêm mới
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'devices' },
        async (payload: any) => {
          const { eventType, new: newDev, old: oldDev } = payload;
          const activePen = currentPenIdRef.current;
          if (eventType === 'INSERT') {
            if (isSameId(newDev.pen_id, activePen)) {
              const formatted = { ...newDev, pin: newDev.pin_number ?? newDev.pin };
              setDevices((prev) => [...prev.filter((d) => !isSameId(d.id, newDev.id)), formatted]);
              showRealtimeNotification('devices', `Đã thêm thiết bị mới: ${newDev.name}`);
              await loadPenData(activePen);
            }
          } else if (eventType === 'UPDATE') {
            if (isSameId(newDev.pen_id, activePen)) {
              const formatted = { ...newDev, pin: newDev.pin_number ?? newDev.pin };
              setDevices((prev) => {
                const exists = prev.some((d) => isSameId(d.id, newDev.id));
                return exists ? prev.map((d) => (isSameId(d.id, newDev.id) ? formatted : d)) : [...prev, formatted];
              });
              showRealtimeNotification('devices', `Thiết bị ${newDev.name} đổi trạng thái sang ${newDev.is_active ? 'BẬT' : 'TẮT'}`);
              await loadPenData(activePen);
            } else {
              setDevices((prev) => prev.filter((d) => !isSameId(d.id, newDev.id)));
            }
          } else if (eventType === 'DELETE') {
            setDevices((prev) => prev.filter((d) => !isSameId(d.id, oldDev.id)));
            showRealtimeNotification('devices', `Đã xóa thiết bị`);
            if (activePen) await loadPenData(activePen);
          }
        }
      )
      // C. animals: Đàn vật nuôi (cân nặng, trạng thái, chuyển chuồng)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'animals' },
        async (payload: any) => {
          const { eventType, new: newAni, old: oldAni } = payload;
          const activePen = currentPenIdRef.current;
          if (eventType === 'INSERT') {
            if (isSameId(newAni.pen_id, activePen)) {
              setAnimals((prev) => [...prev.filter((a) => !isSameId(a.id, newAni.id)), newAni]);
              showRealtimeNotification('animals', `Đã thêm cá thể mới: ${newAni.id} (${newAni.species})`);
              await loadPenData(activePen);
            }
          } else if (eventType === 'UPDATE') {
            if (isSameId(newAni.pen_id, activePen)) {
              setAnimals((prev) => {
                const exists = prev.some((a) => isSameId(a.id, newAni.id));
                return exists ? prev.map((a) => (isSameId(a.id, newAni.id) ? newAni : a)) : [...prev, newAni];
              });
              showRealtimeNotification('animals', `Cập nhật thông tin vật nuôi ${newAni.id}`);
              await loadPenData(activePen);
            } else {
              setAnimals((prev) => prev.filter((a) => !isSameId(a.id, newAni.id)));
              showRealtimeNotification('animals', `Vật nuôi ${newAni.id} đã chuyển sang chuồng ${newAni.pen_id}`);
              if (activePen) await loadPenData(activePen);
            }
          } else if (eventType === 'DELETE') {
            setAnimals((prev) => prev.filter((a) => !isSameId(a.id, oldAni.id)));
            showRealtimeNotification('animals', `Đã xóa hồ sơ vật nuôi ${oldAni.id}`);
            if (activePen) await loadPenData(activePen);
          }
        }
      )
      // D. inventory: Kho thức ăn và vật tư
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'inventory' },
        async (payload: any) => {
          const { eventType, new: newItem, old: oldItem } = payload;
          if (eventType === 'INSERT') {
            setInventory((prev) => [...prev.filter((i) => !isSameId(i.id, newItem.id)), newItem]);
            showRealtimeNotification('inventory', `Kho nhập mặt hàng mới: ${newItem.name}`);
            await fetchInventory();
          } else if (eventType === 'UPDATE') {
            setInventory((prev) => prev.map((i) => (isSameId(i.id, newItem.id) ? newItem : i)));
            showRealtimeNotification('inventory', `Tồn kho ${newItem.name}: ${newItem.quantity} ${newItem.unit}`);
            await fetchInventory();
          } else if (eventType === 'DELETE') {
            setInventory((prev) => prev.filter((i) => !isSameId(i.id, oldItem.id)));
            showRealtimeNotification('inventory', `Đã xóa mặt hàng kho`);
            await fetchInventory();
          }
        }
      )
      // E. crops: Cây trồng và mùa vụ
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'crops' },
        async (payload: any) => {
          const { eventType, new: newCrop, old: oldCrop } = payload;
          const activePen = currentPenIdRef.current;
          if (eventType === 'INSERT') {
            if (isSameId(newCrop.pen_id, activePen)) {
              setCrops((prev) => [...prev.filter((c) => !isSameId(c.id, newCrop.id)), newCrop]);
              showRealtimeNotification('crops', `Đã thêm cây trồng mới: ${newCrop.name}`);
              await loadPenData(activePen);
            }
          } else if (eventType === 'UPDATE') {
            if (isSameId(newCrop.pen_id, activePen)) {
              setCrops((prev) => prev.map((c) => (isSameId(c.id, newCrop.id) ? newCrop : c)));
              await loadPenData(activePen);
            }
          } else if (eventType === 'DELETE') {
            setCrops((prev) => prev.filter((c) => !isSameId(c.id, oldCrop.id)));
            if (activePen) await loadPenData(activePen);
          }
        }
      )
      // F. pens: Danh sách chuồng trại
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'pens' },
        async (payload: any) => {
          const { eventType, new: newPen, old: oldPen } = payload;
          if (eventType === 'INSERT') {
            if (newPen.type === currentModeRef.current) {
              setPens((prev) => [...prev.filter((p) => !isSameId(p.id, newPen.id)), newPen]);
              showRealtimeNotification('pens', `Khu vực mới vừa tạo: ${newPen.name}`);
            }
          } else if (eventType === 'UPDATE') {
            setPens((prev) => prev.map((p) => (isSameId(p.id, newPen.id) ? newPen : p)));
          } else if (eventType === 'DELETE') {
            setPens((prev) => prev.filter((p) => !isSameId(p.id, oldPen.id)));
          }
        }
      )
      // G. alerts: Cảnh báo hệ thống
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'alerts' },
        (payload: any) => {
          const newAlert = payload.new;
          if (newAlert) {
            setActiveAlerts((prev) => ({
              ...prev,
              [newAlert.pen_id || 'general']: [...(prev[newAlert.pen_id || 'general'] || []), newAlert.message],
            }));
            showRealtimeNotification('alerts', `⚠️ CẢNH BÁO MỚI: ${newAlert.message}`);
          }
        }
      )
      // H. health_logs & weight_logs
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'health_logs' },
        (payload: any) => {
          const { eventType, new: newLog, old: oldLog } = payload;
          if (eventType === 'INSERT') {
            if (selectedAnimalIdRef.current && isSameId(newLog.animal_id, selectedAnimalIdRef.current)) {
              setAnimalHealthLogs((prev) => [newLog, ...prev]);
              showRealtimeNotification('health_logs', `Đã thêm nhật ký thú y`);
            }
          } else if (eventType === 'DELETE') {
            setAnimalHealthLogs((prev) => prev.filter((l) => !isSameId(l.id, oldLog.id)));
          }
        }
      )
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'weight_logs' },
        async (payload: any) => {
          const newLog = payload.new;
          const activePen = currentPenIdRef.current;
          if (selectedAnimalIdRef.current && isSameId(newLog.animal_id, selectedAnimalIdRef.current)) {
            setAnimalWeightLogs((prev) => [...prev, newLog]);
            showRealtimeNotification('weight_logs', `Đã cập nhật cân nặng mới`);
          }
          if (activePen) await loadPenData(activePen);
        }
      )
      // I. staff_attendance: Điểm danh nhân sự realtime từ Supabase
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'staff_attendance' },
        (payload: any) => {
          const newAtt = payload.new;
          if (newAtt) {
            const actionText = newAtt.check_type === 'check_out' ? 'tan ca' : 'vào ca';
            showRealtimeNotification('staff', `👤 Nhân sự ${newAtt.staff_name || newAtt.staff_id} đã ${actionText} (${newAtt.pen_id || 'Trang trại'})`);
          }
        }
      )
      .subscribe((status) => {
        console.log('📡 Full Database Realtime Subscription Status:', status);
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  // 7. Continuous Database Live Sync Loop (Vòng Lặp Lắng Nghe Trực Tiếp Từ Database)
  // Đảm bảo mọi phần hiển thị (vật nuôi, thiết bị, kho, cảm biến, cây trồng) luôn tự động đồng bộ từ DB
  useEffect(() => {
    let isMounted = true;
    let isFetching = false;

    const continuousDatabaseSync = async () => {
      if (!isMounted || isFetching) return;
      const activePen = currentPenIdRef.current;
      if (!activePen) return;

      isFetching = true;
      try {
        await Promise.all([
          loadPenData(activePen),
          fetchInventory(),
        ]);

        // Nếu người dùng đang mở theo dõi chi tiết cá thể vật nuôi, tự động tải thêm logs mới
        const activeAnimal = selectedAnimalIdRef.current;
        if (activeAnimal && isMounted) {
          const { data: wLogs } = await supabase.from('weight_logs').select('*').eq('animal_id', activeAnimal).order('created_at', { ascending: false });
          if (wLogs) setAnimalWeightLogs((prev) => (JSON.stringify(prev) === JSON.stringify(wLogs) ? prev : wLogs));

          const { data: hLogs } = await supabase.from('health_logs').select('*').eq('animal_id', activeAnimal).order('created_at', { ascending: false });
          if (hLogs) setAnimalHealthLogs((prev) => (JSON.stringify(prev) === JSON.stringify(hLogs) ? prev : hLogs));
        }
      } catch (err) {
        console.warn('Continuous DB sync warning:', err);
      } finally {
        isFetching = false;
      }
    };

    // Chu kỳ 2000ms (2 giây): Luôn lắng nghe và tải trực tiếp dữ liệu mới nhất
    const syncInterval = setInterval(continuousDatabaseSync, 2000);

    return () => {
      isMounted = false;
      clearInterval(syncInterval);
    };
  }, []);

  // Toggle Device Switch
  const handleToggleDevice = async (id: string, currentStatus: boolean) => {
    const nextStatus = !currentStatus;
    const targetDev = devices.find((d) => String(d.id).trim() === String(id).trim());
    const activePen = currentPenIdRef.current;

    // Optimistic UI update
    setDevices((prev) => prev.map((d) => (String(d.id).trim() === String(id).trim() ? { ...d, is_active: nextStatus } : d)));
    await supabase.from('devices').update({ is_active: nextStatus }).eq('id', id);

    // Sync with Agent backend API
    if (targetDev && activePen) {
      try {
        await controlDeviceViaAPI(activePen, targetDev.name, nextStatus ? 'turn_on' : 'turn_off');
      } catch (err) {
        console.warn('Backend control API error:', err);
      }
    }
    showRealtimeNotification('devices', `Thiết bị ${targetDev?.name || id} đã chuyển sang ${nextStatus ? 'BẬT' : 'TẮT'}`);
    if (activePen) await loadPenData(activePen);
  };

  // Handle Xuất Chuồng (Animal Harvest / Sell / Export) - Không cần F5
  const handleExportAnimal = async (animal: any) => {
    const confirmed = confirm(
      `XÁC NHẬN XUẤT CHUỒNG:\nBạn có chắc muốn xuất bán cá thể ${animal.id} (${animal.species || 'Vật nuôi'}, Cân nặng: ${animal.weight} kg / Mục tiêu: ${animal.target_weight} kg)?`
    );
    if (!confirmed) return;

    const activePen = currentPenIdRef.current;

    // 1. Optimistic Update: Xóa ngay lập tức khỏi state để giao diện phản hồi tức thì
    setAnimals((prev) => prev.filter((a) => String(a.id).trim().toLowerCase() !== String(animal.id).trim().toLowerCase()));

    try {
      // 2. Xóa khỏi bảng animals trên Supabase
      await supabase.from('animals').delete().eq('id', animal.id);

      // 3. Ghi alert hệ thống
      await supabase.from('alerts').insert([
        {
          pen_id: activePen,
          alert_type: 'SYSTEM',
          message: `Đã xuất chuồng thành công cá thể ${animal.id} (${animal.species}, ${animal.weight} kg)`,
        },
      ]);
    } catch (err) {
      console.error('Lỗi khi lưu xuất chuồng:', err);
    }

    // 4. Tự động tải lại dữ liệu chuồng để đồng bộ tuyệt đối mà KHÔNG CẦN F5!
    if (activePen) await loadPenData(activePen);
    showRealtimeNotification('animals', `🎉 ĐÃ XUẤT CHUỒNG THÀNH CÔNG: Cá thể ${animal.id} (${animal.weight} kg)`);
  };

  // Current pen helper
  const currentPen = pens.find((p) => p.id === currentPenId) || { id: currentPenId, name: 'Chuồng Trang Trại' };
  const currentPenIssues = activeAlerts[currentPenId] || [];

  // Flatten Alerts for dropdown
  const alertList = Object.entries(activeAlerts).map(([pId, issues], idx) => {
    const p = pens.find((x) => x.id === pId);
    return {
      id: idx.toString(),
      penName: p ? p.name : `Chuồng ${pId}`,
      issues,
      time: 'Vừa xong',
    };
  });

  // Handle Login/Register
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');

    if (authMode === 'login') {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) setAuthError(error.message);
      else setSession(data.session);
    } else {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) setAuthError(error.message);
      else alert('Đăng ký thành công! Vui lòng kiểm tra email hoặc đăng nhập.');
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setIsDemoMode(false);
  };

  // --- RENDER LOGIN IF NOT AUTHENTICATED & NOT DEMO ---
  if (!session && !isDemoMode) {
    return (
      <div className="min-h-screen bg-fb-bg flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-md bg-fb-card rounded-2xl shadow-fb-popover border border-fb-divider p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-emerald-600 to-green-500 mx-auto flex items-center justify-center text-white shadow-lg mb-3">
              <Sprout className="w-9 h-9" />
            </div>
            <h2 className="text-2xl font-extrabold text-fb-text tracking-tight">Nông Trại Thông Minh</h2>
            <p className="text-xs text-fb-muted mt-1">
              Hệ Thống Quản Lý Nông Trại & Trợ Lý Trực Tuyến 24/7
            </p>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-fb-muted mb-1">Email Người Quản Lý</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="quanly@nongtrai.vn"
                className="w-full bg-fb-bg text-sm rounded-xl px-3.5 py-2.5 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-fb-muted mb-1">Mật Khẩu</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-fb-bg text-sm rounded-xl px-3.5 py-2.5 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {authError && (
              <p className="text-xs text-red-600 bg-red-50 p-2.5 rounded-xl border border-red-200">
                {authError}
              </p>
            )}

            <button
              type="submit"
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-xl transition shadow cursor-pointer"
            >
              {authMode === 'login' ? 'Đăng Nhập Quản Lý' : 'Tạo Tài Khoản Mới'}
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-fb-divider flex items-center justify-between text-xs">
            <button
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              className="text-emerald-700 font-semibold hover:underline cursor-pointer"
            >
              {authMode === 'login' ? 'Chưa có tài khoản? Đăng ký ngay' : 'Đã có tài khoản? Đăng nhập'}
            </button>

            <button
              onClick={() => {
                setIsDemoMode(true);
                loadInitialData();
              }}
              className="text-emerald-700 font-bold hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>Trải Nghiệm Thử Nhanh</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- MAIN FACEBOOK NEWSFEED DASHBOARD ---
  return (
    <div className="min-h-screen bg-fb-bg flex flex-col">
      {/* 1. Facebook-Style Sticky Top Bar */}
      <Navbar
        currentMode={currentMode}
        onModeChange={handleModeChange}
        pens={pens}
        currentPenId={currentPenId}
        onPenChange={(pId) => {
          setCurrentPenId(pId);
          currentPenIdRef.current = pId;
          loadPenData(pId);
        }}
        userEmail={session?.user?.email || 'Người Quản Lý Trang Trại'}
        onLogout={handleLogout}
        alerts={alertList}
        onOpenMessenger={() => setIsMessengerOpen(true)}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted(!isMuted)}
        unreadAlertsCount={alertList.length}
        wsConnected={wsConnected}
        onTriggerBriefing={handleTriggerBriefing}
      />

      {/* 2. Main 3-Column Layout */}
      <div className="max-w-7xl mx-auto w-full px-2 sm:px-4 py-4 flex gap-4 flex-1">
        {/* Left Column (Navigation & Pens) */}
        <LeftSidebar
          userEmail={session?.user?.email || 'nongdan@smartfarm.vn'}
          currentMode={currentMode}
          onModeChange={handleModeChange}
          pens={pens.map((p) => ({ ...p, hasAlert: !!activeAlerts[p.id] }))}
          currentPenId={currentPenId}
          onSelectPen={(pId) => {
            setCurrentPenId(pId);
            currentPenIdRef.current = pId;
            loadPenData(pId);
          }}
          onOpenAddPenModal={() => setModalOpen({ ...modalOpen, addPen: true })}
        />

        {/* Center Column: The Facebook Newsfeed */}
        <main className="flex-1 max-w-2xl mx-auto w-full space-y-4">
          {/* A. Facebook Stories Row */}
          <StoriesBar
            pens={pens.map((p) => ({
              ...p,
              hasAlert: !!activeAlerts[p.id],
              temp: p.id === currentPenId ? envData.temp : undefined,
              hum: p.id === currentPenId ? envData.hum : undefined,
            }))}
            currentPenId={currentPenId}
            onSelectPen={(pId) => {
              setCurrentPenId(pId);
              currentPenIdRef.current = pId;
              loadPenData(pId);
            }}
            onOpenAddPenModal={() => setModalOpen({ ...modalOpen, addPen: true })}
          />

          {/* B. Pinned Breaking Alert Card (Auto jumps to top if sensor issue detected) */}
          {!dismissedAlert && currentPenIssues.length > 0 && (
            <FeedAlertPinned
              penName={currentPen.name}
              penId={currentPenId}
              issues={currentPenIssues}
              temp={envData.temp}
              smell={envData.smell}
              onActivateFan={async () => {
                alert('Đã kích hoạt quạt thông gió làm mát chuồng!');
                const fanDev = devices.find((d) => d.name.toLowerCase().includes('quạt'));
                if (fanDev) handleToggleDevice(fanDev.id, false);
              }}
              onDismiss={() => setDismissedAlert(true)}
              onAskAI={() => setIsMessengerOpen(true)}
            />
          )}

          {/* C. AI Morning Briefing Post */}
          <FeedBriefingCard
            onOpenChat={() => setIsMessengerOpen(true)}
            pendingTasksCount={2}
            lowStockCount={inventory.filter((i) => i.quantity <= 5).length}
            sickAnimalsCount={animals.filter((a) => a.feeding_status === 'Anorexic' || a.status === 'Sick').length}
            briefingText={briefingText}
            onTriggerBriefing={handleTriggerBriefing}
            isLoading={isBriefingLoading}
          />

          {/* D. Realtime Environment Monitor Post (Chart.js + Gauges) */}
          <FeedEnvMonitor
            penName={currentPen.name}
            penId={currentPenId}
            currentMode={currentMode}
            temp={envData.temp}
            hum={envData.hum}
            smell={envData.smell}
            historyLogs={historyLogs}
            onRefresh={() => loadPenData(currentPenIdRef.current)}
            onOpenChat={() => setIsMessengerOpen(true)}
          />

          {/* E. Staff Attendance & 24/7 Face Scan Feed Post */}
          <FeedStaffAttendance
            currentPenId={currentPenId}
            penName={currentPen.name}
            onNotification={(title, desc) => showRealtimeNotification('staff', desc)}
          />

          {/* F. Livestock & Crops Feed Post */}
          <FeedLivestockCrops
            currentMode={currentMode}
            animals={animals}
            crops={crops}
            penName={currentPen.name}
            onOpenAddModal={() =>
              currentMode === 'livestock'
                ? setModalOpen({ ...modalOpen, addAnimal: true })
                : setModalOpen({ ...modalOpen, addCrop: true })
            }
            onExportAnimal={handleExportAnimal}
            onOpenTracking={async (animalId) => {
              setSelectedAnimalId(animalId);
              selectedAnimalIdRef.current = animalId;
              const { data } = await supabase.from('weight_logs').select('*').eq('animal_id', animalId);
              setAnimalWeightLogs(data || [{ weight: 20 }, { weight: 25 }]);
              setModalOpen({ ...modalOpen, weight: true });
            }}
            onOpenHealth={async (animalId) => {
              setSelectedAnimalId(animalId);
              selectedAnimalIdRef.current = animalId;
              const { data } = await supabase.from('health_logs').select('*').eq('animal_id', animalId);
              setAnimalHealthLogs(data || []);
              setModalOpen({ ...modalOpen, health: true });
            }}
            onDeleteAnimal={async (animalId) => {
              if (confirm('Bạn có chắc muốn xóa hồ sơ vật nuôi này?')) {
                const activePen = currentPenIdRef.current;
                setAnimals((prev) => prev.filter((a) => String(a.id).trim().toLowerCase() !== String(animalId).trim().toLowerCase()));
                await supabase.from('animals').delete().eq('id', animalId);
                if (activePen) await loadPenData(activePen);
                showRealtimeNotification('animals', `Đã xóa hồ sơ cá thể ${animalId}`);
              }
            }}
            onOpenCropTracking={async (cropId) => {
              setSelectedCropId(cropId);
              selectedCropIdRef.current = cropId;
              const { data } = await supabase.from('crop_growth_logs').select('*').eq('crop_id', cropId);
              setCropGrowthLogs(data || []);
              setModalOpen({ ...modalOpen, cropTrack: true });
            }}
            onOpenCropCare={async (cropId) => {
              setSelectedCropId(cropId);
              selectedCropIdRef.current = cropId;
              const { data } = await supabase.from('crop_care_logs').select('*').eq('crop_id', cropId);
              setCropCareLogs(data || []);
              setModalOpen({ ...modalOpen, cropCare: true });
            }}
            onDeleteCrop={async (cropId) => {
              if (confirm('Bạn có chắc muốn xóa vụ mùa cây trồng này?')) {
                const activePen = currentPenIdRef.current;
                setCrops((prev) => prev.filter((c) => String(c.id).trim().toLowerCase() !== String(cropId).trim().toLowerCase()));
                await supabase.from('crops').delete().eq('id', cropId);
                if (activePen) await loadPenData(activePen);
                showRealtimeNotification('crops', `Đã xóa vụ mùa cây trồng`);
              }
            }}
          />

          {/* F. Inventory Feed Post */}
          <FeedInventory
            items={inventory}
            onOpenImport={() => setModalOpen({ ...modalOpen, importInv: true })}
            onOpenExport={() => setModalOpen({ ...modalOpen, exportInv: true })}
          />
        </main>

        {/* Right Column: IoT Switches & Activity Stream */}
        <RightSidebar
          devices={devices}
          penName={currentPen.name}
          onToggleDevice={handleToggleDevice}
          onOpenAddDeviceModal={() => setModalOpen({ ...modalOpen, addDevice: true })}
        />
      </div>

      {/* 3. Floating Messenger Chat Bubble */}
      <MessengerChatBubble
        penId={currentPenId}
        penName={currentPen.name}
        isOpen={isMessengerOpen}
        onToggle={() => setIsMessengerOpen(!isMessengerOpen)}
        temp={envData.temp}
        hum={envData.hum}
        smell={envData.smell}
        userId={session?.user?.id || (isDemoMode ? 'demo_user' : 'guest')}
      />

      {/* 4. Modals */}
      <ModalAddPen
        isOpen={modalOpen.addPen}
        onClose={() => setModalOpen({ ...modalOpen, addPen: false })}
        onAdd={async (type, id, name) => {
          const userId = session?.user?.id;
          const newPen = { id, name, type, ...(userId ? { user_id: userId } : {}) };
          setPens((prev) => [...prev, newPen]);
          await supabase.from('pens').insert([newPen]);
          try {
            await fetch(`${BACKEND_URL}/api/pens`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(newPen),
            });
          } catch (e) {
            console.error('Pen API sync error:', e);
          }
          setCurrentPenId(id);
          currentPenIdRef.current = id;
          await fetchPens();
          await loadPenData(id);
          showRealtimeNotification('pens', `Đã tạo khu vực mới: ${name}`);
        }}
      />

      <ModalAddDevice
        isOpen={modalOpen.addDevice}
        onClose={() => setModalOpen({ ...modalOpen, addDevice: false })}
        onAdd={async (id, name, pin) => {
          const activePen = currentPenIdRef.current;
          const newDev = { id, name, pin_number: pin, is_active: false, pen_id: activePen };
          setDevices((prev) => [...prev, { ...newDev, pin }]);
          await supabase.from('devices').insert([newDev]);
          if (activePen) await loadPenData(activePen);
          showRealtimeNotification('devices', `Đã thêm thiết bị mới: ${name}`);
        }}
      />

      <ModalAddAnimal
        isOpen={modalOpen.addAnimal}
        onClose={() => setModalOpen({ ...modalOpen, addAnimal: false })}
        onAdd={async (id, species, weight, targetWeight) => {
          const activePen = currentPenIdRef.current;
          const newAni = { id, species, weight, target_weight: targetWeight, pen_id: activePen, status: 'Khoe' };
          setAnimals((prev) => [...prev, newAni]);
          await supabase.from('animals').insert([newAni]);
          if (activePen) await loadPenData(activePen);
          showRealtimeNotification('animals', `Đã thêm cá thể mới: ${id} (${species})`);
        }}
      />

      <ModalHealth
        isOpen={modalOpen.health}
        onClose={() => setModalOpen({ ...modalOpen, health: false })}
        animalId={selectedAnimalId}
        logs={animalHealthLogs}
        onAddLog={async (type, action, note) => {
          const targetAnimalId = selectedAnimalIdRef.current;
          const newLog = { animal_id: targetAnimalId, type, title: action, note, created_at: new Date().toISOString() };
          setAnimalHealthLogs((prev) => [newLog, ...prev]);
          await supabase.from('health_logs').insert([newLog]);
          const { data } = await supabase.from('health_logs').select('*').eq('animal_id', targetAnimalId);
          if (data) setAnimalHealthLogs(data);
          showRealtimeNotification('health_logs', `Đã thêm nhật ký thú y`);
        }}
        onDeleteLog={async (logId) => {
          const targetAnimalId = selectedAnimalIdRef.current;
          setAnimalHealthLogs((prev) => prev.filter((l) => String(l.id) !== String(logId)));
          await supabase.from('health_logs').delete().eq('id', logId);
          const { data } = await supabase.from('health_logs').select('*').eq('animal_id', targetAnimalId);
          if (data) setAnimalHealthLogs(data);
        }}
      />

      <ModalWeightTracking
        isOpen={modalOpen.weight}
        onClose={() => setModalOpen({ ...modalOpen, weight: false })}
        animalId={selectedAnimalId}
        logs={animalWeightLogs}
        onSaveWeight={async (weight) => {
          const targetAnimalId = selectedAnimalIdRef.current;
          const activePen = currentPenIdRef.current;
          const newLog = { animal_id: targetAnimalId, weight: Number(weight), created_at: new Date().toISOString() };
          setAnimalWeightLogs((prev) => [...prev, newLog]);
          setAnimals((prev) => prev.map((a) => (String(a.id) === String(targetAnimalId) ? { ...a, weight: Number(weight) } : a)));
          await supabase.from('weight_logs').insert([newLog]);
          await supabase.from('animals').update({ weight: Number(weight) }).eq('id', targetAnimalId);
          if (activePen) await loadPenData(activePen);
          showRealtimeNotification('weight_logs', `Đã cập nhật cân nặng mới: ${weight} kg`);
        }}
      />

      <ModalImport
        isOpen={modalOpen.importInv}
        onClose={() => setModalOpen({ ...modalOpen, importInv: false })}
        onImport={async (category, name, quantity, unit, price) => {
          const existing = inventory.find((i) => i.name.toLowerCase().trim() === name.toLowerCase().trim());
          if (existing) {
            const updatedQty = Number(existing.quantity) + Number(quantity);
            setInventory((prev) => prev.map((i) => (String(i.id) === String(existing.id) ? { ...i, quantity: updatedQty } : i)));
            await supabase.from('inventory').update({ quantity: updatedQty }).eq('id', existing.id);
          } else {
            // Không truyền cột 'id' vì 'id' là GENERATED ALWAYS AS IDENTITY trong PostgreSQL
            const newItem = {
              name,
              category: category || 'Feed',
              quantity: Number(quantity),
              unit: unit || 'kg',
              unit_price: Number(price) || 0,
              user_id: session?.user?.id || null,
            };
            await supabase.from('inventory').insert([newItem]);
          }
          await fetchInventory();
          showRealtimeNotification('inventory', `Đã nhập kho ${quantity} ${unit} ${name}`);
        }}
      />

      <ModalExport
        isOpen={modalOpen.exportInv}
        onClose={() => setModalOpen({ ...modalOpen, exportInv: false })}
        inventoryItems={inventory}
        pens={pens}
        onExport={async (itemId, qty, penId, note) => {
          const item = inventory.find((i) => String(i.id) === String(itemId));
          if (item) {
            const updatedQty = Math.max(0, Number(item.quantity) - Number(qty));
            setInventory((prev) => prev.map((i) => (String(i.id) === String(itemId) ? { ...i, quantity: updatedQty } : i)));
            await supabase.from('inventory').update({ quantity: updatedQty }).eq('id', item.id);
            // Bảng feed_logs có các cột: pen_id, food_name, amount
            await supabase.from('feed_logs').insert([{ pen_id: penId, food_name: item.name, amount: Number(qty) }]);
            await fetchInventory();
            showRealtimeNotification('inventory', `Đã xuất kho ${qty} ${item.unit} ${item.name} cho chuồng ${penId}`);
          }
        }}
      />

      <ModalAddCrop
        isOpen={modalOpen.addCrop}
        onClose={() => setModalOpen({ ...modalOpen, addCrop: false })}
        onAdd={async (name, quantity, date) => {
          const activePen = currentPenIdRef.current;
          // Bảng crops dùng cột 'plant_date' và 'id' tự tăng
          const newCrop = {
            name,
            quantity: Number(quantity),
            plant_date: date || new Date().toISOString().split('T')[0],
            pen_id: activePen,
          };
          await supabase.from('crops').insert([newCrop]);
          if (activePen) await loadPenData(activePen);
          showRealtimeNotification('crops', `Đã thêm cây trồng mới: ${name}`);
        }}
      />

      <ModalCropTracking
        isOpen={modalOpen.cropTrack}
        onClose={() => setModalOpen({ ...modalOpen, cropTrack: false })}
        cropId={selectedCropId}
        logs={cropGrowthLogs}
        onSaveGrowth={async (size) => {
          const targetCropId = selectedCropIdRef.current;
          const newLog = { crop_id: targetCropId, size: Number(size), created_at: new Date().toISOString() };
          setCropGrowthLogs((prev) => [...prev, newLog]);
          await supabase.from('crop_growth_logs').insert([newLog]);
          showRealtimeNotification('crop_growth_logs', `Đã cập nhật tăng trưởng cây trồng`);
        }}
      />

      <ModalCropCare
        isOpen={modalOpen.cropCare}
        onClose={() => setModalOpen({ ...modalOpen, cropCare: false })}
        cropId={selectedCropId}
        logs={cropCareLogs}
        onAddCare={async (type, note) => {
          const targetCropId = selectedCropIdRef.current;
          const newLog = { crop_id: targetCropId, type, note, created_at: new Date().toISOString() };
          setCropCareLogs((prev) => [...prev, newLog]);
          await supabase.from('crop_care_logs').insert([newLog]);
          showRealtimeNotification('crop_care_logs', `Đã ghi nhật ký chăm sóc`);
        }}
      />
      {/* 5. Live Realtime Notification Toast (F5-Free Instant Sync) */}
      {realtimeToast && (
        <div className="fixed bottom-6 left-6 z-50 bg-slate-900/95 backdrop-blur text-white text-xs px-4 py-3 rounded-2xl shadow-2xl border border-emerald-500/60 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-4 duration-200 max-w-sm">
          <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-sm shrink-0 shadow-inner">
            ⚡
          </div>
          <div className="min-w-0">
            <span className="font-bold text-emerald-400 block text-[11px] uppercase tracking-wider">
              Cập Nhật Tự Động • Thời Gian Thực
            </span>
            <span className="text-slate-200 text-xs block truncate mt-0.5">
              {realtimeToast.message}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
