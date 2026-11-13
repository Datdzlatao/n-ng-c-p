'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Users, 
  Camera, 
  CameraOff, 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  Sparkles, 
  RefreshCw, 
  Upload, 
  LogIn, 
  LogOut, 
  Zap,
  AlertCircle,
  Eye,
  Shirt,
  ScanLine,
  UserCheck,
  UserPlus,
  X,
  Pause,
  Play,
  Radio,
  Video,
  ArrowRight,
  ChevronRight,
  RotateCcw,
  Check,
  Shield,
  Info
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { 
  BACKEND_URL,
  FACE_API_URL,
  getStaffList, 
  getStaffAttendanceHistory, 
  checkInStaff, 
  checkInStaffUpload,
  getVisionHealth,
  scanUniformUploadAPI,
  startCameraDeviceAPI,
  stopCameraDeviceAPI,
  getCameraLatestTelemetryAPI,
  enrollStaffFace,
  reloadStaffFacesAPI
} from '../lib/agent-api';

interface FeedStaffAttendanceProps {
  currentPenId: string;
  penName: string;
  onNotification?: (title: string, desc: string) => void;
}

// Cố định quy chuẩn trang phục bảo hộ chuẩn nông trại (giống image.jpg/png)
// -1 = Chuẩn an toàn sinh học: Khẩu trang y tế + Áo xanh bảo hộ + Quần tối màu
const FIXED_UNIFORM_RULE = -1;

export default function FeedStaffAttendance({
  currentPenId,
  penName,
  onNotification,
}: FeedStaffAttendanceProps) {
  // Quy trình 2 bước bắt buộc:
  // 'step1_face': Nhận diện khuôn mặt (FaceID - bỏ khẩu trang)
  // 'step2_uniform': Quét trang phục & khẩu trang y tế chuẩn nông trại
  // 'completed': Chúc mừng hoàn tất và đếm ngược chuyển nhân sự kế tiếp
  const [checkinStep, setCheckinStep] = useState<'step1_face' | 'step2_uniform' | 'completed'>('step1_face');
  const [identifiedStaff, setIdentifiedStaff] = useState<{
    staffId: string;
    staffName: string;
    confidence: number;
    isReal: boolean;
    detectedAt?: number;
  } | null>(null);

  const [autoResetTimer, setAutoResetTimer] = useState<number | null>(null);
  const [isFinalizingCheckin, setIsFinalizingCheckin] = useState<boolean>(false);
  const autoResetIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const step2HoldCountRef = useRef<number>(0);

  // Staff & Attendance State
  const [staffList, setStaffList] = useState<any[]>([]);
  const [attendanceLogs, setAttendanceLogs] = useState<any[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<string>('');
  const [checkType, setCheckType] = useState<'check_in' | 'check_out'>('check_in');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Vision Health
  const [visionOnline, setVisionOnline] = useState<boolean>(false);

  // Live Camera State (Server Camera Stream)
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isLivePaused, setIsLivePaused] = useState(false);
  const [liveScanFps, setLiveScanFps] = useState<number>(0);
  const [liveLatencyMs, setLiveLatencyMs] = useState<number>(0);

  // Hardware Stream URL State
  const [hardwareStreamKey, setHardwareStreamKey] = useState<number>(Date.now());
  const [hardwareStreamUrl, setHardwareStreamUrl] = useState<string>(
    `${FACE_API_URL}/api/v1/camera/video_feed?overlay=true`
  );

  // Live Detection Results
  const [liveFaces, setLiveFaces] = useState<any[]>([]);
  const [uniformResult, setUniformResult] = useState<any | null>(null);
  const [liveSuccessBanner, setLiveSuccessBanner] = useState<{
    staffName: string;
    staffId: string;
    type: string;
    timestamp: number;
  } | null>(null);

  // Enroll FaceID eKYC Modal State (3 Angles: Thẳng, Nghiêng Trái, Nghiêng Phải)
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollStaffId, setEnrollStaffId] = useState('');
  const [enrollStaffName, setEnrollStaffName] = useState('');
  const [enrollRole, setEnrollRole] = useState('Kỹ thuật viên');
  const [enrollPenId, setEnrollPenId] = useState(currentPenId || '123');

  const [enrollFileThang, setEnrollFileThang] = useState<File | null>(null);
  const [enrollFileTrai, setEnrollFileTrai] = useState<File | null>(null);
  const [enrollFilePhai, setEnrollFilePhai] = useState<File | null>(null);

  const [previewThang, setPreviewThang] = useState<string | null>(null);
  const [previewTrai, setPreviewTrai] = useState<string | null>(null);
  const [previewPhai, setPreviewPhai] = useState<string | null>(null);

  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollModalMsg, setEnrollModalMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fileInputThangRef = useRef<HTMLInputElement>(null);
  const fileInputTraiRef = useRef<HTMLInputElement>(null);
  const fileInputPhaiRef = useRef<HTMLInputElement>(null);

  // References
  const hardwarePollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uniformFileInputRef = useRef<HTMLInputElement | null>(null);

  // Initial Data
  useEffect(() => {
    fetchInitialData();
    checkEngine();
  }, [currentPenId]);

  // Lắng nghe thay đổi trực tiếp từ Supabase bảng staff_attendance theo thời gian thực
  useEffect(() => {
    const channel = supabase
      .channel('staff_attendance_realtime_feed')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'staff_attendance' },
        async () => {
          try {
            const logs = await getStaffAttendanceHistory(20);
            setAttendanceLogs(logs);
          } catch (e) {}
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const checkEngine = async () => {
    const health = await getVisionHealth();
    setVisionOnline(Boolean(health?.online));
  };

  const fetchInitialData = async () => {
    setIsLoading(true);
    try {
      const [staffs, logs] = await Promise.all([
        getStaffList(),
        getStaffAttendanceHistory(20)
      ]);
      setStaffList(staffs);
      if (staffs.length > 0 && !selectedStaffId) {
        setSelectedStaffId(staffs[0].id);
      }
      setAttendanceLogs(logs);
    } catch (err) {
      console.error('Error fetching staff data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Synthetic Audio Chime on Successful Verification
  const playSuccessChime = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch (e) {
      // Audio autoplay blocked
    }
  }, []);

  // ─────────────────────────────────────────────────────────────
  // SERVER CAMERA CONTROLS
  // ─────────────────────────────────────────────────────────────
  const startCamera = async () => {
    try {
      setStatusMessage(null);
      setIsLoading(true);

      const newKey = Date.now();
      setHardwareStreamKey(newKey);
      setHardwareStreamUrl(`${FACE_API_URL}/api/v1/camera/video_feed?overlay=true&t=${newKey}`);

      try {
        await startCameraDeviceAPI('0', FIXED_UNIFORM_RULE);
      } catch (e) {
        console.warn('Server camera device start notice:', e);
      }

      setIsCameraActive(true);
      setIsLivePaused(false);
    } catch (err: any) {
      console.warn('Server camera start error:', err);
      setStatusMessage({
        type: 'error',
        text: `Không thể kết nối máy ảnh chuồng trại: ${err.message || err}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  const stopCamera = () => {
    if (hardwarePollIntervalRef.current) {
      clearInterval(hardwarePollIntervalRef.current);
      hardwarePollIntervalRef.current = null;
    }
    stopCameraDeviceAPI().catch(() => {});
    setIsCameraActive(false);
    setIsLivePaused(false);
    setLiveScanFps(0);
    setLiveLatencyMs(0);
    setLiveFaces([]);
  };

  const togglePauseLive = () => {
    setIsLivePaused(prev => !prev);
  };

  // ─────────────────────────────────────────────────────────────
  // 2-STEP PROTOCOL CONTROLS & COMPLETION
  // ─────────────────────────────────────────────────────────────
  const goToStep2 = () => {
    if (!identifiedStaff) return;
    setCheckinStep('step2_uniform');
    step2HoldCountRef.current = 0;
    setStatusMessage({
      type: 'success',
      text: `Bước 2: Quét trang phục bảo hộ & khẩu trang y tế cho ${identifiedStaff.staffName}.`
    });
  };

  const goBackToStep1 = () => {
    setCheckinStep('step1_face');
    step2HoldCountRef.current = 0;
  };

  const resetToStep1 = () => {
    if (autoResetIntervalRef.current) {
      clearInterval(autoResetIntervalRef.current);
      autoResetIntervalRef.current = null;
    }
    setAutoResetTimer(null);
    setCheckinStep('step1_face');
    setIdentifiedStaff(null);
    setUniformResult(null);
    setLiveSuccessBanner(null);
    step2HoldCountRef.current = 0;
  };

  const handleFinalizeTwoStepCheckIn = useCallback(async (staff: any, uniformData: any) => {
    if (isFinalizingCheckin || !staff) return;
    setIsFinalizingCheckin(true);
    try {
      const maskColor = uniformData?.mask?.mask_color === 'blue' ? 'xanh y tế' : (uniformData?.mask?.mask_color || 'y tế');
      const noteMsg = `Vào ca chuẩn nông trại: Khẩu trang ${maskColor} + Áo xanh bảo hộ + Quần tối màu`;

      await checkInStaff({
        staffId: staff.staffId,
        staffName: staff.staffName,
        penId: currentPenId || '123',
        checkType,
        confidence: staff.confidence,
        isReal: staff.isReal,
        note: noteMsg
      });

      playSuccessChime();
      setCheckinStep('completed');
      setLiveSuccessBanner({
        staffName: staff.staffName,
        staffId: staff.staffId,
        type: checkType,
        timestamp: Date.now()
      });

      if (onNotification) {
        onNotification('Vào Ca Thành Công', `🎉 ${staff.staffName} (${staff.staffId}) đã hoàn tất quy trình an toàn sinh học!`);
      }

      getStaffAttendanceHistory(20).then(setAttendanceLogs).catch(() => {});

      // Tự động đếm ngược 6 giây sẵn sàng cho nhân sự tiếp theo
      let count = 6;
      setAutoResetTimer(count);
      if (autoResetIntervalRef.current) clearInterval(autoResetIntervalRef.current);
      autoResetIntervalRef.current = setInterval(() => {
        count -= 1;
        if (count <= 0) {
          if (autoResetIntervalRef.current) {
            clearInterval(autoResetIntervalRef.current);
            autoResetIntervalRef.current = null;
          }
          setAutoResetTimer(null);
          resetToStep1();
        } else {
          setAutoResetTimer(count);
        }
      }, 1000);

    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `Lỗi khi xác nhận vào ca: ${err.message || err}`
      });
    } finally {
      setIsFinalizingCheckin(false);
    }
  }, [currentPenId, checkType, playSuccessChime, onNotification, isFinalizingCheckin]);

  // ─────────────────────────────────────────────────────────────
  // SERVER CAMERA AI REAL-TIME TELEMETRY POLLING LOOP
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isCameraActive || isLivePaused) {
      if (hardwarePollIntervalRef.current) {
        clearInterval(hardwarePollIntervalRef.current);
        hardwarePollIntervalRef.current = null;
      }
      return;
    }

    const pollServerCamera = async () => {
      if (isPollingRef.current) return;
      isPollingRef.current = true;
      const tStart = performance.now();

      try {
        const telemetry = await getCameraLatestTelemetryAPI();
        const latency = Math.round(performance.now() - tStart);
        setLiveLatencyMs(latency);

        if (telemetry) {
          const fps = telemetry.ai_fps || telemetry.capture_fps || 0;
          setLiveScanFps(Math.round(fps * 10) / 10);

          if (telemetry.uniform) {
            setUniformResult(telemetry.uniform);
          }

          const faces = telemetry.faces || [];
          if (faces.length > 0) {
            setLiveFaces(faces);

            // BƯỚC 1: XÁC THỰC DANH TÍNH KHUÔN MẶT
            if (checkinStep === 'step1_face' && !identifiedStaff) {
              const vf = faces.find((f: any) => {
                const sid = f.student_id || f.staff_id || f.id;
                const isReal = f.liveness ? f.liveness.is_real : true;
                return sid && sid !== 'UNKNOWN' && (f.confidence || 0) >= 0.55 && isReal;
              });

              if (vf) {
                playSuccessChime();
                const sid = vf.student_id || vf.staff_id || vf.id;
                const staffObj = {
                  staffId: sid,
                  staffName: vf.name || 'Nhân sự',
                  confidence: vf.confidence || 0.95,
                  isReal: vf.liveness ? vf.liveness.is_real : true,
                  detectedAt: Date.now()
                };
                setIdentifiedStaff(staffObj);
                setSelectedStaffId(sid);
                if (onNotification) {
                  onNotification(
                    'Xác thực khuôn mặt',
                    `✅ Đã nhận diện ${staffObj.staffName}. Vui lòng bấm [Quét Trang Phục & Khẩu Trang]!`
                  );
                }
              }
            }
          }

          // BƯỚC 2: QUÉT TRANG PHỤC & KHẨU TRANG
          if (checkinStep === 'step2_uniform' && identifiedStaff && !isFinalizingCheckin) {
            if (telemetry.uniform && telemetry.uniform.is_correct) {
              step2HoldCountRef.current += 1;
              if (step2HoldCountRef.current >= 2) {
                handleFinalizeTwoStepCheckIn(identifiedStaff, telemetry.uniform);
              }
            } else {
              step2HoldCountRef.current = 0;
            }
          }
        }
      } catch (e) {
        // Drop network error frame silently
      } finally {
        isPollingRef.current = false;
      }
    };

    // Polling tốc độ cao 180ms phản hồi tức thời
    hardwarePollIntervalRef.current = setInterval(pollServerCamera, 180);

    return () => {
      if (hardwarePollIntervalRef.current) {
        clearInterval(hardwarePollIntervalRef.current);
        hardwarePollIntervalRef.current = null;
      }
    };
  }, [
    isCameraActive,
    isLivePaused,
    checkinStep,
    identifiedStaff,
    isFinalizingCheckin,
    handleFinalizeTwoStepCheckIn,
    playSuccessChime,
    onNotification
  ]);

  // ─────────────────────────────────────────────────────────────
  // MANUAL CHECK-IN & PHOTO UPLOAD FALLBACKS
  // ─────────────────────────────────────────────────────────────
  const handleManualCheckIn = async () => {
    if (!selectedStaffId) return;
    setIsLoading(true);
    setStatusMessage(null);

    try {
      const staffObj = staffList.find(s => s.id === selectedStaffId);
      await checkInStaff({
        staffId: selectedStaffId,
        staffName: staffObj?.name || selectedStaffId,
        penId: currentPenId || '123',
        checkType,
        confidence: 1.0,
        isReal: true,
        note: `Chấm công thủ công dự phòng`
      });

      const typeLabel = checkType === 'check_in' ? 'Vào ca' : 'Tan ca';
      const msg = `✅ Đã chấm công [${typeLabel}] thành công cho ${staffObj?.name || selectedStaffId}`;
      setStatusMessage({ type: 'success', text: msg });

      if (onNotification) {
        onNotification('Chấm Công Nhân Sự', msg);
      }

      const updatedLogs = await getStaffAttendanceHistory(20);
      setAttendanceLogs(updatedLogs);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Lỗi khi chấm công thủ công.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setStatusMessage(null);

    try {
      const res = await checkInStaffUpload(file, currentPenId || '123', checkType);
      const staffName = res.attendance?.staff_name || 'Nhân sự';
      const staffId = res.attendance?.staff_id || selectedStaffId;

      setIdentifiedStaff({
        staffId,
        staffName,
        confidence: 0.98,
        isReal: true,
        detectedAt: Date.now()
      });
      setSelectedStaffId(staffId);

      const msg = `✅ Đã nhận diện ảnh: ${staffName} (${staffId}). Vui lòng bấm [Quét Trang Phục & Khẩu Trang]!`;
      setStatusMessage({ type: 'success', text: msg });
      if (onNotification) {
        onNotification('Xác thực khuôn mặt', msg);
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Lỗi khi quét ảnh khuôn mặt.'
      });
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleUniformFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setStatusMessage(null);
    try {
      const res = await scanUniformUploadAPI(file, FIXED_UNIFORM_RULE);
      const u = res.uniform || {};
      setUniformResult(u);

      if (u.person_detected) {
        if (u.is_correct) {
          if (identifiedStaff) {
            handleFinalizeTwoStepCheckIn(identifiedStaff, u);
          } else {
            setStatusMessage({
              type: 'success',
              text: `✅ Ảnh đạt chuẩn: Áo xanh bảo hộ, quần tối màu & khẩu trang y tế!`
            });
          }
        } else {
          setStatusMessage({
            type: 'error',
            text: `❌ ${u.message || 'Ảnh tải lên chưa đúng quy chuẩn trang phục an toàn sinh học!'}`
          });
        }
      } else {
        setStatusMessage({
          type: 'error',
          text: '⚠️ Không nhận diện được vóc dáng người trong ảnh. Vui lòng chọn ảnh chụp rõ toàn thân.'
        });
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Lỗi khi kiểm tra đồng phục qua ảnh.'
      });
    } finally {
      setIsLoading(false);
      if (uniformFileInputRef.current) uniformFileInputRef.current.value = '';
    }
  };

  // ─────────────────────────────────────────────────────────────
  // ENROLL FACEID (eKYC 3 GÓC: THẲNG, NGHIÊNG TRÁI, NGHIÊNG PHẢI)
  // ─────────────────────────────────────────────────────────────
  const captureAngleFromServerCamera = async (angle: 'thang' | 'nghieng_trai' | 'nghieng_phai') => {
    try {
      setIsLoading(true);
      const res = await fetch(`${FACE_API_URL}/api/v1/camera/snapshot?overlay=false`);
      if (!res.ok) {
        throw new Error('Không thể chụp ảnh từ Camera Server');
      }
      const blob = await res.blob();
      const filename = `${enrollStaffId || 'NV'}_${angle}.jpg`;
      const file = new File([blob], filename, { type: 'image/jpeg' });
      const previewUrl = URL.createObjectURL(blob);

      if (angle === 'thang') {
        setEnrollFileThang(file);
        setPreviewThang(previewUrl);
      } else if (angle === 'nghieng_trai') {
        setEnrollFileTrai(file);
        setPreviewTrai(previewUrl);
      } else if (angle === 'nghieng_phai') {
        setEnrollFilePhai(file);
        setPreviewPhai(previewUrl);
      }
    } catch (err: any) {
      setEnrollModalMsg({
        type: 'error',
        text: `Lỗi chụp ảnh góc ${angle}: ${err.message || err}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAngleFileChange = (angle: 'thang' | 'nghieng_trai' | 'nghieng_phai', e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const previewUrl = URL.createObjectURL(file);

    if (angle === 'thang') {
      setEnrollFileThang(file);
      setPreviewThang(previewUrl);
    } else if (angle === 'nghieng_trai') {
      setEnrollFileTrai(file);
      setPreviewTrai(previewUrl);
    } else if (angle === 'nghieng_phai') {
      setEnrollFilePhai(file);
      setPreviewPhai(previewUrl);
    }
  };

  const handleEnrollSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollStaffId || !enrollStaffName) {
      setEnrollModalMsg({ type: 'error', text: 'Vui lòng điền đủ mã nhân viên và họ tên.' });
      return;
    }

    if (!enrollFileThang || !enrollFileTrai || !enrollFilePhai) {
      setEnrollModalMsg({
        type: 'error',
        text: 'Quy trình eKYC yêu cầu chụp đủ cả 3 góc (Nhìn Thẳng, Nghiêng Trái, Nghiêng Phải) để tối ưu độ chính xác!'
      });
      return;
    }

    setIsEnrolling(true);
    setEnrollModalMsg(null);

    try {
      await enrollStaffFace({
        staffId: enrollStaffId,
        staffName: enrollStaffName,
        role: enrollRole,
        penId: enrollPenId || currentPenId || '123',
        fileThang: enrollFileThang,
        fileNghiengTrai: enrollFileTrai,
        fileNghiengPhai: enrollFilePhai
      });

      try {
        await reloadStaffFacesAPI();
      } catch (e) {}

      setEnrollModalMsg({
        type: 'success',
        text: `🎉 Đã đăng ký thành công FaceID 3 góc eKYC cho ${enrollStaffName} (${enrollStaffId})!`
      });

      await fetchInitialData();
      setTimeout(() => {
        setIsEnrollModalOpen(false);
        setEnrollModalMsg(null);
        setEnrollStaffId('');
        setEnrollStaffName('');
        setEnrollFileThang(null);
        setEnrollFileTrai(null);
        setEnrollFilePhai(null);
        setPreviewThang(null);
        setPreviewTrai(null);
        setPreviewPhai(null);
      }, 2000);

    } catch (err: any) {
      setEnrollModalMsg({
        type: 'error',
        text: `Lỗi đăng ký FaceID: ${err.message || err}`
      });
    } finally {
      setIsEnrolling(false);
    }
  };

  const handleReloadFaces = async () => {
    setIsLoading(true);
    try {
      const res = await reloadStaffFacesAPI();
      setStatusMessage({
        type: 'success',
        text: `✅ ${res.message || 'Đã làm mới danh sách khuôn mặt nhận diện!'}`
      });
      await fetchInitialData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `Không thể làm mới khuôn mặt: ${err.message}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  const todayDateStr = new Date().toISOString().split('T')[0];
  const todayLogs = attendanceLogs.filter(l => (l.created_at || '').startsWith(todayDateStr));
  const activeStaffIds = new Set(todayLogs.filter(l => l.check_type !== 'check_out').map(l => l.staff_id));

  return (
    <div className="bg-white rounded-3xl p-4 sm:p-6 shadow-sm border border-slate-200/90 space-y-5">
      {/* ─────────────────────────────────────────────────────────────
          1. HEADER SECTION (Gọn gàng, thanh thoát)
      ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shadow-md shadow-emerald-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-base text-slate-900 tracking-tight">
                Chấm Công & Kiểm Soát An Toàn Sinh Học
              </h3>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200/80 px-2 py-0.5 rounded-full">
                AI 24/7
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Nhận diện khuôn mặt FaceID • Tự động quét trang phục bảo hộ chuẩn nông trại
            </p>
          </div>
        </div>

        {/* Action Controls & Badges */}
        <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
          <span className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-700">
            Đang trực: <strong className="text-emerald-600 font-bold">{activeStaffIds.size}</strong>/{staffList.length} nhân sự
          </span>

          <button
            onClick={() => {
              setEnrollStaffId(`NV${String(staffList.length + 1).padStart(2, '0')}`);
              setEnrollPenId(currentPenId || '123');
              setIsEnrollModalOpen(true);
            }}
            className="text-xs px-3.5 py-1.5 rounded-xl font-bold bg-slate-900 hover:bg-slate-800 text-white shadow-sm transition flex items-center gap-1.5 cursor-pointer"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>+ Thêm FaceID</span>
          </button>

          <button
            onClick={handleReloadFaces}
            title="Làm mới thư mục khuôn mặt known_faces"
            className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert / Toast Notification */}
      {statusMessage && (
        <div 
          className={`p-3 rounded-2xl text-xs font-medium flex items-center justify-between gap-2 transition animate-in fade-in ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
              : 'bg-rose-50 text-rose-900 border border-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button 
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-slate-600 p-0.5 rounded-lg"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          2. STEP PROGRESS PIPELINE (Trực quan, không rối mắt)
      ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* BƯỚC 1: XÁC THỰC KHUÔN MẶT */}
        <button
          onClick={() => setCheckinStep('step1_face')}
          className={`p-3.5 rounded-2xl border text-left transition relative cursor-pointer ${
            checkinStep === 'step1_face'
              ? 'bg-emerald-50/70 border-emerald-500 shadow-sm'
              : identifiedStaff
              ? 'bg-slate-50 border-emerald-300'
              : 'bg-slate-50/50 border-slate-200 opacity-80'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
                identifiedStaff
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : checkinStep === 'step1_face'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-200 text-slate-500'
              }`}>
                {identifiedStaff ? <Check className="w-4 h-4 stroke-[3]" /> : '1'}
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  <span>Bước 1: Xác Thực Khuôn Mặt (FaceID)</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {identifiedStaff ? (
                    <span className="text-emerald-700 font-semibold">
                      Đã khớp: {identifiedStaff.staffName} ({identifiedStaff.staffId})
                    </span>
                  ) : (
                    'Bỏ khẩu trang để nhận diện danh tính'
                  )}
                </div>
              </div>
            </div>

            {checkinStep === 'step1_face' && (
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100/70 px-2.5 py-1 rounded-full">
                Đang Quét
              </span>
            )}
          </div>
        </button>

        {/* BƯỚC 2: QUÉT TRANG PHỤC & KHẨU TRANG */}
        <button
          onClick={() => { if (identifiedStaff) setCheckinStep('step2_uniform'); }}
          disabled={!identifiedStaff}
          className={`p-3.5 rounded-2xl border text-left transition relative ${
            checkinStep === 'step2_uniform'
              ? 'bg-cyan-50/70 border-cyan-500 shadow-sm'
              : checkinStep === 'completed'
              ? 'bg-slate-50 border-emerald-300'
              : 'bg-slate-50/40 border-slate-200 text-slate-400 cursor-not-allowed'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
                checkinStep === 'completed'
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : checkinStep === 'step2_uniform'
                  ? 'bg-cyan-500 text-white shadow-sm'
                  : 'bg-slate-200 text-slate-400'
              }`}>
                {checkinStep === 'completed' ? <Check className="w-4 h-4 stroke-[3]" /> : '2'}
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  <span>Bước 2: Quét Trang Phục & Khẩu Trang</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {checkinStep === 'completed' ? (
                    <span className="text-emerald-700 font-semibold">✓ Đã duyệt an toàn sinh học 100%</span>
                  ) : identifiedStaff ? (
                    'Đeo khẩu trang & kiểm tra áo xanh, quần tối'
                  ) : (
                    'Cần nhận diện khuôn mặt ở Bước 1'
                  )}
                </div>
              </div>
            </div>

            {checkinStep === 'step2_uniform' && (
              <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-700 bg-cyan-100/70 px-2.5 py-1 rounded-full">
                Đang Quét
              </span>
            )}
          </div>
        </button>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN INTERACTION AREA: VIEWPORT & LIVE CONTEXT PANEL
      ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* CAMERA VIEWPORT (8 cols) */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-3">
          <div className="relative rounded-2xl overflow-hidden bg-slate-950 aspect-video max-h-[440px] flex items-center justify-center border border-slate-800 shadow-inner group">
            {/* Server Hardware MJPEG Video Stream */}
            {isCameraActive && (
              <img
                key={hardwareStreamKey}
                src={hardwareStreamUrl}
                alt="Luồng máy ảnh chuồng trại"
                className="w-full h-full object-contain"
                onError={() => {
                  setHardwareStreamUrl((prev) =>
                    prev.includes(FACE_API_URL)
                      ? `${BACKEND_URL}/api/camera/video_feed?overlay=true&t=${Date.now()}`
                      : `${FACE_API_URL}/api/v1/camera/video_feed?overlay=true&t=${Date.now()}`
                  );
                }}
              />
            )}

            {/* Inactive Camera Placeholder */}
            {!isCameraActive && (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center space-y-3 bg-gradient-to-b from-slate-900 to-slate-950 text-white">
                <div className="w-14 h-14 rounded-2xl bg-slate-800 border border-slate-700 text-emerald-400 flex items-center justify-center shadow-lg">
                  <Camera className="w-7 h-7" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-slate-100">
                    Camera Chuồng Trại Đang Tắt • Sẵn Sàng Quét AI 24/7
                  </h4>
                  <p className="text-xs text-slate-400 max-w-sm mt-1">
                    Bật camera máy chủ để tự động nhận diện khuôn mặt và kiểm tra trang phục bảo hộ nông trại.
                  </p>
                </div>
                <div className="pt-2 flex flex-wrap gap-2.5 justify-center">
                  <button
                    onClick={startCamera}
                    disabled={isLoading}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-md transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <Camera className="w-4 h-4" />
                    <span>{isLoading ? 'Đang Khởi Động Camera...' : 'Bật Camera Chuồng Trại'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Floating Top Badges when Active */}
            {isCameraActive && (
              <div className="absolute top-3 inset-x-3 flex items-center justify-between pointer-events-none z-10">
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md border border-slate-700 text-slate-200 text-[10px] font-semibold px-2.5 py-1 rounded-full shadow">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    Camera chuồng trại (Server AI)
                  </span>
                  <span className="bg-emerald-950/80 backdrop-blur-md border border-emerald-600 text-emerald-300 text-[10px] font-bold px-2 py-1 rounded-full">
                    {checkType === 'check_in' ? '🟢 Vào ca' : '🔴 Tan ca'}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md border border-slate-700 text-slate-300 text-[10px] font-mono px-2.5 py-1 rounded-full shadow">
                  <span className="text-emerald-400 font-bold">{liveScanFps} FPS</span>
                  <span>•</span>
                  <span className="text-cyan-400">{liveLatencyMs}ms</span>
                </div>
              </div>
            )}

            {/* Floating Live Uniform Status Bar (Step 2) */}
            {isCameraActive && checkinStep === 'step2_uniform' && uniformResult && (
              <div className="absolute bottom-3 inset-x-3 flex justify-center pointer-events-none z-10">
                <div className={`px-4 py-1.5 rounded-full backdrop-blur-md border text-xs font-bold shadow-lg flex items-center gap-2 ${
                  uniformResult.is_correct
                    ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500'
                    : 'bg-rose-950/90 text-rose-300 border-rose-500'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${uniformResult.is_correct ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`} />
                  <span>
                    {uniformResult.is_correct 
                      ? '✅ ĐẠT CHUẨN ĐỒNG PHỤC BẢO HỘ NÔNG TRẠI'
                      : uniformResult.mask && !uniformResult.mask.has_mask
                      ? '❌ BẮT BUỘC: ĐEO KHẨU TRANG Y TẾ'
                      : `❌ VI PHẠM: ${uniformResult.message || 'Chưa đúng chuẩn trang phục'}`}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Action Toolbar Below Viewfinder */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-2.5 bg-slate-50 border border-slate-200 rounded-2xl">
            {/* Mode: Vào ca / Tan ca */}
            <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200">
              <button
                onClick={() => setCheckType('check_in')}
                className={`py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                  checkType === 'check_in'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Vào Ca</span>
              </button>
              <button
                onClick={() => setCheckType('check_out')}
                className={`py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                  checkType === 'check_out'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Tan Ca</span>
              </button>
            </div>

            {/* Camera Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              {isCameraActive ? (
                <>
                  <button
                    onClick={togglePauseLive}
                    className="text-xs px-2.5 py-1.5 rounded-xl font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition flex items-center gap-1 cursor-pointer"
                  >
                    {isLivePaused ? <Play className="w-3.5 h-3.5 text-emerald-600" /> : <Pause className="w-3.5 h-3.5" />}
                    <span>{isLivePaused ? 'Tiếp tục' : 'Tạm dừng'}</span>
                  </button>

                  <button
                    onClick={stopCamera}
                    className="text-xs px-3 py-1.5 rounded-xl font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition flex items-center gap-1 cursor-pointer"
                  >
                    <CameraOff className="w-3.5 h-3.5" />
                    <span>Tắt Camera</span>
                  </button>
                </>
              ) : (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-xs px-3 py-1.5 rounded-xl font-medium bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <Upload className="w-3.5 h-3.5 text-slate-500" />
                    <span>Tải ảnh khuôn mặt</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* LIVE CONTEXT & ASSESSMENT PANEL (4 cols) */}
        <div className="lg:col-span-5 xl:col-span-4 space-y-3">
          {/* STEP 1: CHỜ QUÉT KHUÔN MẶT */}
          {checkinStep === 'step1_face' && !identifiedStaff && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-sm">
                  1
                </div>
                <div>
                  <h4 className="font-bold text-xs text-slate-900">Bước 1: Quét Khuôn Mặt (FaceID)</h4>
                  <p className="text-[11px] text-slate-500">Đứng trước máy ảnh và bỏ khẩu trang</p>
                </div>
              </div>

              <div className="p-3 bg-white rounded-xl border border-slate-200/80 text-xs text-slate-600 space-y-1.5">
                <div className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Nhìn thẳng vào máy ảnh, giữ khoảng cách 0.5m - 1.2m.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Hệ thống AI tự động phân tích và chống giả mạo ảnh chụp.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span>Sau khi nhận diện, hệ thống tự động chuyển sang kiểm tra đồng phục.</span>
                </div>
              </div>

              {liveFaces.length > 0 && (
                <div className="text-[11px] font-medium text-emerald-700 bg-emerald-50 p-2.5 rounded-xl border border-emerald-200 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  <span>Đang phát hiện {liveFaces.length} khuôn mặt trong khung hình...</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 1: ĐÃ NHẬN DIỆN KHUÔN MẶT -> NÚT CHUYỂN SANG BƯỚC 2 */}
          {checkinStep === 'step1_face' && identifiedStaff && (
            <div className="p-4 rounded-2xl bg-emerald-50/70 border-2 border-emerald-400 space-y-3 shadow-sm animate-in fade-in">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-200/80 px-2.5 py-0.5 rounded-full">
                  Bước 1 Hoàn Tất
                </span>
                <span className="text-xs text-emerald-700 font-mono font-bold">
                  Khớp {Math.round(identifiedStaff.confidence * 100)}%
                </span>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500 text-white font-black text-xl flex items-center justify-center shadow-md">
                  ✓
                </div>
                <div>
                  <h4 className="font-extrabold text-sm text-slate-900">
                    {identifiedStaff.staffName}
                  </h4>
                  <p className="text-xs text-slate-500 font-mono">
                    Mã NV: {identifiedStaff.staffId}
                  </p>
                </div>
              </div>

              <div className="p-3 bg-white/90 rounded-xl border border-emerald-200 text-xs text-slate-700 space-y-1">
                <p className="font-bold text-amber-700 flex items-center gap-1.5">
                  <span>😷 Yêu cầu bắt buộc:</span>
                </p>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Vui lòng <strong>đeo khẩu trang y tế</strong> và lùi lại cách máy ảnh 1.5m - 2m để kiểm tra trang phục bảo hộ chuẩn nông trại.
                </p>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={goToStep2}
                  className="flex-1 py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition flex items-center justify-center gap-2 cursor-pointer"
                >
                  <span>Quét Trang Phục & Khẩu Trang</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={resetToStep1}
                  title="Nhận diện lại người khác"
                  className="p-3 rounded-xl bg-white border border-slate-200 hover:bg-slate-100 text-slate-600 transition"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: QUÉT TRANG PHỤC & KHẨU TRANG (Chuẩn an toàn sinh học) */}
          {checkinStep === 'step2_uniform' && (
            <div className="p-4 rounded-2xl bg-slate-900 text-white space-y-3.5 shadow-md">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded-full border border-cyan-800">
                    Bước 2: Quét An Toàn Sinh Học
                  </span>
                  <h4 className="font-bold text-xs text-slate-200 mt-1">
                    Nhân viên: <span className="text-cyan-300 font-extrabold">{identifiedStaff?.staffName}</span>
                  </h4>
                </div>
                <button
                  onClick={goBackToStep1}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                >
                  ← Quay lại
                </button>
              </div>

              {/* 3 Checklist Items (Mặc định chuẩn image.jpg/png) */}
              <div className="space-y-2 text-xs">
                {/* 1. Khẩu trang y tế */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  uniformResult?.mask?.has_mask 
                    ? 'bg-emerald-950/70 border-emerald-500 text-emerald-200' 
                    : 'bg-rose-950/70 border-rose-500 text-rose-200'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className="text-base">😷</span>
                    <div>
                      <div className="font-bold">1. Khẩu Trang Y Tế</div>
                      <div className="text-[10px] opacity-75">Bắt buộc che kín mũi miệng</div>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                    uniformResult?.mask?.has_mask ? 'bg-emerald-500 text-slate-950' : 'bg-rose-500 text-white'
                  }`}>
                    {uniformResult?.mask?.has_mask ? '✓ ĐÃ ĐEO' : '✗ CHƯA ĐEO'}
                  </span>
                </div>

                {/* 2. Áo bảo hộ màu xanh dương */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  ['blue', 'cyan', 'white'].includes(uniformResult?.shirt_color)
                    ? 'bg-emerald-950/70 border-emerald-500 text-emerald-200'
                    : 'bg-slate-800/80 border-slate-700 text-slate-300'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className="text-base">👔</span>
                    <div>
                      <div className="font-bold">2. Áo Bảo Hộ Xanh</div>
                      <div className="text-[10px] opacity-75">Chuẩn màu xanh nông trại</div>
                    </div>
                  </div>
                  <span className="font-bold text-[10px] uppercase px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
                    {uniformResult?.shirt_color ? uniformResult.shirt_color.toUpperCase() : 'QUÉT...'}
                  </span>
                </div>

                {/* 3. Quần dài tối màu */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  uniformResult?.pants_color === 'dark'
                    ? 'bg-emerald-950/70 border-emerald-500 text-emerald-200'
                    : 'bg-slate-800/80 border-slate-700 text-slate-300'
                }`}>
                  <div className="flex items-center gap-2">
                    <span className="text-base">👖</span>
                    <div>
                      <div className="font-bold">3. Quần Dài Tối Màu</div>
                      <div className="text-[10px] opacity-75">Quần đen / xanh đen</div>
                    </div>
                  </div>
                  <span className="font-bold text-[10px] uppercase px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
                    {uniformResult?.pants_color ? uniformResult.pants_color.toUpperCase() : 'QUÉT...'}
                  </span>
                </div>
              </div>

              {/* Status & Confirm */}
              <div className="pt-1 space-y-2">
                {uniformResult?.is_correct ? (
                  <button
                    onClick={() => handleFinalizeTwoStepCheckIn(identifiedStaff, uniformResult)}
                    disabled={isFinalizingCheckin}
                    className="w-full py-2.5 px-4 rounded-xl font-bold text-xs uppercase bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-md flex items-center justify-center gap-2 transition cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Xác Nhận Đạt Chuẩn & Vào Ca</span>
                  </button>
                ) : (
                  <p className="text-[11px] text-amber-300/90 text-center leading-relaxed">
                    💡 Đứng lùi lại 1.5m - 2m và đeo khẩu trang y tế để hệ thống tự động xác nhận vào ca.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* STEP 3: HOÀN TẤT VÀO CA */}
          {checkinStep === 'completed' && (
            <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 text-white space-y-3 shadow-lg animate-in zoom-in-95">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-white text-emerald-600 font-black text-2xl flex items-center justify-center shadow">
                  🎉
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-white/20 px-2 py-0.5 rounded-full">
                    Thành Công 100%
                  </span>
                  <h4 className="font-extrabold text-sm mt-0.5">
                    {identifiedStaff?.staffName}
                  </h4>
                  <p className="text-[11px] text-emerald-100 font-mono">
                    {new Date().toLocaleTimeString('vi-VN')} • Chuồng: {penName}
                  </p>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-black/15 text-xs space-y-1">
                <div className="flex items-center gap-1.5 text-emerald-100">
                  <span>✓</span>
                  <span>Đã đối chiếu FaceID chính xác</span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-100">
                  <span>✓</span>
                  <span>Đạt chuẩn trang phục & khẩu trang an toàn sinh học</span>
                </div>
              </div>

              <button
                onClick={resetToStep1}
                className="w-full py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-white text-emerald-800 hover:bg-emerald-50 shadow transition flex items-center justify-center gap-2 cursor-pointer"
              >
                <UserCheck className="w-4 h-4" />
                <span>Tiếp tục người kế tiếp {autoResetTimer ? `(${autoResetTimer}s)` : ''}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          4. FOOTER: STANDARD UNIFORM SPECIFICATION & ATTENDANCE LOGS
      ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 pt-3 border-t border-slate-100">
        {/* Cột Trái: Quy Chuẩn Trang Phục (Cố Định Mặc Định) & Dự Phòng (5 cols) */}
        <div className="md:col-span-5 space-y-3">
          {/* Card: Quy chuẩn đồng phục nông trại cố định (Khóa mặc định, không cần chọn) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
                <Shirt className="w-4 h-4 text-emerald-600" />
                <span>Quy Chuẩn Đồng Phục Nông Trại (Cố Định)</span>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                Mặc Định
              </span>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed">
              Hệ thống áp dụng duy nhất quy chuẩn trang phục bảo hộ nông trại đạt chuẩn an toàn sinh học:
            </p>

            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center gap-2 p-1.5 bg-white rounded-lg border border-slate-200 text-slate-700">
                <span>😷</span>
                <span className="font-semibold">Khẩu trang y tế:</span>
                <span className="text-slate-500">Màu xanh hoặc trắng, che kín mũi & miệng</span>
              </div>
              <div className="flex items-center gap-2 p-1.5 bg-white rounded-lg border border-slate-200 text-slate-700">
                <span>👔</span>
                <span className="font-semibold">Áo bảo hộ:</span>
                <span className="text-slate-500">Áo sơ mi cộc tay màu xanh dương</span>
              </div>
              <div className="flex items-center gap-2 p-1.5 bg-white rounded-lg border border-slate-200 text-slate-700">
                <span>👖</span>
                <span className="font-semibold">Quần dài:</span>
                <span className="text-slate-500">Quần sẫm màu (đen / xanh đen)</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <input
                ref={uniformFileInputRef}
                type="file"
                accept="image/*"
                onChange={handleUniformFileUpload}
                className="hidden"
              />
              <button
                onClick={() => uniformFileInputRef.current?.click()}
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 cursor-pointer hover:underline"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Tải ảnh toàn thân để quét thử</span>
              </button>
            </div>
          </div>

          {/* Card: Chấm công thủ công dự phòng */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-2">
            <label className="text-xs font-bold text-slate-700 block">
              Chấm Công Thủ Công (Dự Phòng Khi Không Dùng Máy Ảnh)
            </label>
            <div className="flex gap-2">
              <select
                value={selectedStaffId}
                onChange={(e) => setSelectedStaffId(e.target.value)}
                className="flex-1 bg-white border border-slate-300 text-slate-800 text-xs rounded-xl px-2.5 py-2 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {staffList.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.id} - {s.name} ({s.role || 'Kỹ thuật'})
                  </option>
                ))}
              </select>
              <button
                onClick={handleManualCheckIn}
                disabled={isLoading || !selectedStaffId}
                className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition shrink-0 flex items-center gap-1 disabled:opacity-50 cursor-pointer"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Ghi Nhận</span>
              </button>
            </div>
          </div>
        </div>

        {/* Cột Phải: Nhật ký chấm công gần nhất (7 cols) */}
        <div className="md:col-span-7 space-y-2">
          <div className="flex items-center justify-between pb-1">
            <span className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-emerald-600" />
              Nhật Ký Chấm Công Gần Nhất
            </span>
            <span className="text-[11px] text-slate-500 font-medium">
              {attendanceLogs.length} lượt gần nhất
            </span>
          </div>

          {attendanceLogs.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 rounded-2xl">
              Chưa có lượt chấm công nào trong hôm nay.
            </div>
          ) : (
            <div className="max-h-56 overflow-y-auto space-y-2 pr-1 text-xs">
              {attendanceLogs.map((log, idx) => {
                const isCheckOut = log.check_type === 'check_out';
                const createdDate = new Date(log.created_at || Date.now());
                const timeStr = createdDate.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                const dateStr = createdDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });

                return (
                  <div 
                    key={log.id || idx}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-200/80 transition"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs text-white shrink-0 ${
                        isCheckOut ? 'bg-rose-500' : 'bg-emerald-600'
                      }`}>
                        {log.staff_name ? log.staff_name.charAt(0).toUpperCase() : 'N'}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-900 truncate">{log.staff_name}</span>
                          <span className="text-[11px] text-slate-500 font-mono">({log.staff_id})</span>
                        </div>
                        <span className="text-[10px] text-slate-500 block truncate">
                          {log.note || 'Chấm công tự động'}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 shrink-0 text-right">
                      <span 
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-lg ${
                          isCheckOut 
                            ? 'bg-rose-100 text-rose-800' 
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {isCheckOut ? 'Tan Ca' : 'Vào Ca'}
                      </span>
                      <div className="text-[10px] font-mono text-slate-500">
                        <div className="font-semibold text-slate-700">{timeStr}</div>
                        <div className="text-[9px] text-slate-400">{dateStr}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          5. MODAL: ĐĂNG KÝ FACEID eKYC 3 GÓC (Chuẩn Ngân Hàng)
      ───────────────────────────────────────────────────────────── */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden text-slate-800">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center">
                  <ShieldCheck className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h4 className="font-bold text-sm">Đăng Ký FaceID eKYC 3 Góc (Chuẩn Ngân Hàng)</h4>
                  <p className="text-[11px] text-emerald-100">Chụp 3 góc: Thẳng, Nghiêng Trái, Nghiêng Phải để nhận diện chính xác 100%</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  setIsEnrollModalOpen(false);
                  setEnrollModalMsg(null);
                  setEnrollFileThang(null);
                  setEnrollFileTrai(null);
                  setEnrollFilePhai(null);
                  setPreviewThang(null);
                  setPreviewTrai(null);
                  setPreviewPhai(null);
                }}
                className="p-1 rounded-lg hover:bg-white/20 text-white/80 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleEnrollSubmit} className="p-6 space-y-4 max-h-[82vh] overflow-y-auto">
              {enrollModalMsg && (
                <div className={`p-3 rounded-xl text-xs font-semibold flex items-center gap-2 ${
                  enrollModalMsg.type === 'success'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-rose-50 text-rose-800 border border-rose-200'
                }`}>
                  {enrollModalMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                  <span>{enrollModalMsg.text}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Mã Nhân Viên *</label>
                  <input
                    type="text"
                    required
                    value={enrollStaffId}
                    onChange={(e) => setEnrollStaffId(e.target.value.toUpperCase())}
                    placeholder="VD: NV05"
                    className="w-full text-xs font-semibold px-3 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none uppercase"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Họ và Tên *</label>
                  <input
                    type="text"
                    required
                    value={enrollStaffName}
                    onChange={(e) => setEnrollStaffName(e.target.value)}
                    placeholder="VD: Nguyễn Văn A"
                    className="w-full text-xs font-semibold px-3 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Chức Vụ</label>
                  <select
                    value={enrollRole}
                    onChange={(e) => setEnrollRole(e.target.value)}
                    className="w-full text-xs font-medium px-3 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
                  >
                    <option value="Kỹ thuật viên">Kỹ thuật viên</option>
                    <option value="Công nhân nhà kính">Công nhân nhà kính</option>
                    <option value="Bác sĩ thú y">Bác sĩ thú y</option>
                    <option value="Quản lý trang trại">Quản lý trang trại</option>
                    <option value="Kỹ sư nông học">Kỹ sư nông học</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Khu Vực Phân Công</label>
                  <input
                    type="text"
                    value={enrollPenId}
                    onChange={(e) => setEnrollPenId(e.target.value)}
                    placeholder="VD: 123"
                    className="w-full text-xs font-medium px-3 py-2 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* ─────────────────────────────────────────────────────────────
                  eKYC 3-ANGLE FACE CAPTURE SECTION
              ───────────────────────────────────────────────────────────── */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <span>Ảnh Chân Dung 3 Góc (Chuẩn eKYC Ngân Hàng)</span>
                    <span className="text-rose-500">*</span>
                  </label>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    (enrollFileThang && enrollFileTrai && enrollFilePhai)
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : 'bg-amber-100 text-amber-800 border border-amber-300'
                  }`}>
                    {[enrollFileThang, enrollFileTrai, enrollFilePhai].filter(Boolean).length}/3 Góc Đã Chụp
                  </span>
                </div>

                {/* Hidden File Inputs */}
                <input
                  ref={fileInputThangRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleAngleFileChange('thang', e)}
                  className="hidden"
                />
                <input
                  ref={fileInputTraiRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleAngleFileChange('nghieng_trai', e)}
                  className="hidden"
                />
                <input
                  ref={fileInputPhaiRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleAngleFileChange('nghieng_phai', e)}
                  className="hidden"
                />

                {/* 3-Angle Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* GÓC 1: NHÌN THẲNG */}
                  <div className={`p-3 rounded-2xl border transition-all ${
                    enrollFileThang ? 'border-emerald-400 bg-emerald-50/40 shadow-sm' : 'border-slate-200 bg-slate-50'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-800 flex items-center gap-1">
                        <span>👤 1. Nhìn Thẳng</span>
                      </span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        enrollFileThang ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}>
                        {enrollFileThang ? '✓ Đạt' : 'Chưa chụp'}
                      </span>
                    </div>

                    <div className="w-full aspect-[4/3] rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden mb-2 relative shadow-inner">
                      {previewThang ? (
                        <img src={previewThang} alt="Góc thẳng" className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-center p-2 text-slate-400 space-y-1">
                          <Users className="w-7 h-7 mx-auto opacity-40" />
                          <span className="text-[10px] block">Chính diện 0°</span>
                        </div>
                      )}
                      <span className="absolute bottom-1 right-1 bg-slate-900/70 text-slate-200 text-[8px] font-mono px-1 py-0.5 rounded">
                        _thang.jpg
                      </span>
                    </div>

                    <div className="flex gap-1.5">
                      {isCameraActive && (
                        <button
                          type="button"
                          onClick={() => captureAngleFromServerCamera('thang')}
                          className="flex-1 py-1.5 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] transition flex items-center justify-center gap-1 shadow-sm cursor-pointer"
                          title="Chụp từ camera server"
                        >
                          <Camera className="w-3 h-3" />
                          <span>Chụp</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => fileInputThangRef.current?.click()}
                        className="flex-1 py-1.5 px-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-semibold text-[10px] transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Tải ảnh góc thẳng"
                      >
                        <Upload className="w-3 h-3" />
                        <span>Tải ảnh</span>
                      </button>
                    </div>
                  </div>

                  {/* GÓC 2: NGHIÊNG TRÁI */}
                  <div className={`p-3 rounded-2xl border transition-all ${
                    enrollFileTrai ? 'border-emerald-400 bg-emerald-50/40 shadow-sm' : 'border-slate-200 bg-slate-50'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-800 flex items-center gap-1">
                        <span>🫲 2. Nghiêng Trái</span>
                      </span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        enrollFileTrai ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}>
                        {enrollFileTrai ? '✓ Đạt' : 'Chưa chụp'}
                      </span>
                    </div>

                    <div className="w-full aspect-[4/3] rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden mb-2 relative shadow-inner">
                      {previewTrai ? (
                        <img src={previewTrai} alt="Góc nghiêng trái" className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-center p-2 text-slate-400 space-y-1">
                          <Users className="w-7 h-7 mx-auto opacity-40 -scale-x-100" />
                          <span className="text-[10px] block">Nghiêng trái ~30°</span>
                        </div>
                      )}
                      <span className="absolute bottom-1 right-1 bg-slate-900/70 text-slate-200 text-[8px] font-mono px-1 py-0.5 rounded">
                        _nghieng_trai.jpg
                      </span>
                    </div>

                    <div className="flex gap-1.5">
                      {isCameraActive && (
                        <button
                          type="button"
                          onClick={() => captureAngleFromServerCamera('nghieng_trai')}
                          className="flex-1 py-1.5 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] transition flex items-center justify-center gap-1 shadow-sm cursor-pointer"
                          title="Chụp từ camera server"
                        >
                          <Camera className="w-3 h-3" />
                          <span>Chụp</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => fileInputTraiRef.current?.click()}
                        className="flex-1 py-1.5 px-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-semibold text-[10px] transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Tải ảnh nghiêng trái"
                      >
                        <Upload className="w-3 h-3" />
                        <span>Tải ảnh</span>
                      </button>
                    </div>
                  </div>

                  {/* GÓC 3: NGHIÊNG PHẢI */}
                  <div className={`p-3 rounded-2xl border transition-all ${
                    enrollFilePhai ? 'border-emerald-400 bg-emerald-50/40 shadow-sm' : 'border-slate-200 bg-slate-50'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-800 flex items-center gap-1">
                        <span>🫱 3. Nghiêng Phải</span>
                      </span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        enrollFilePhai ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}>
                        {enrollFilePhai ? '✓ Đạt' : 'Chưa chụp'}
                      </span>
                    </div>

                    <div className="w-full aspect-[4/3] rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden mb-2 relative shadow-inner">
                      {previewPhai ? (
                        <img src={previewPhai} alt="Góc nghiêng phải" className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-center p-2 text-slate-400 space-y-1">
                          <Users className="w-7 h-7 mx-auto opacity-40" />
                          <span className="text-[10px] block">Nghiêng phải ~30°</span>
                        </div>
                      )}
                      <span className="absolute bottom-1 right-1 bg-slate-900/70 text-slate-200 text-[8px] font-mono px-1 py-0.5 rounded">
                        _nghieng_phai.jpg
                      </span>
                    </div>

                    <div className="flex gap-1.5">
                      {isCameraActive && (
                        <button
                          type="button"
                          onClick={() => captureAngleFromServerCamera('nghieng_phai')}
                          className="flex-1 py-1.5 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] transition flex items-center justify-center gap-1 shadow-sm cursor-pointer"
                          title="Chụp từ camera server"
                        >
                          <Camera className="w-3 h-3" />
                          <span>Chụp</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => fileInputPhaiRef.current?.click()}
                        className="flex-1 py-1.5 px-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-semibold text-[10px] transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Tải ảnh nghiêng phải"
                      >
                        <Upload className="w-3 h-3" />
                        <span>Tải ảnh</span>
                      </button>
                    </div>
                  </div>
                </div>

                <p className="text-[10px] text-slate-500 leading-relaxed mt-2.5 bg-slate-100/80 p-2.5 rounded-xl border border-slate-200">
                  💡 <strong>Quy trình eKYC chuẩn ngân hàng:</strong> Bạn vui lòng chụp đủ cả 3 góc (Nhìn thẳng, Nghiêng trái, Nghiêng phải). Các ảnh sẽ tự động được lưu với hậu tố <code className="text-emerald-700 font-mono">_thang</code>, <code className="text-emerald-700 font-mono">_nghieng_trai</code>, <code className="text-emerald-700 font-mono">_nghieng_phai</code> để AI nhận diện khuôn mặt tức thì ở mọi góc nhìn!
                </p>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setIsEnrollModalOpen(false);
                    setEnrollModalMsg(null);
                    setEnrollFileThang(null);
                    setEnrollFileTrai(null);
                    setEnrollFilePhai(null);
                    setPreviewThang(null);
                    setPreviewTrai(null);
                    setPreviewPhai(null);
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition cursor-pointer"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isEnrolling || !enrollStaffId || !enrollStaffName || !enrollFileThang || !enrollFileTrai || !enrollFilePhai}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2 cursor-pointer"
                >
                  {isEnrolling ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Đang lưu 3 góc eKYC...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Lưu & Kích Hoạt FaceID 3 Góc</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
