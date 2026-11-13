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
  Check
} from 'lucide-react';
import { 
  BACKEND_URL,
  FACE_API_URL,
  getStaffList, 
  getStaffAttendanceHistory, 
  checkInStaff, 
  checkInStaffUpload,
  getVisionHealth,
  scanUniformUploadAPI,
  liveScanStaffAPI,
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

export default function FeedStaffAttendance({
  currentPenId,
  penName,
  onNotification,
}: FeedStaffAttendanceProps) {
  // Main Tab: 'attendance' (FaceID 24/7) vs 'uniform' (Quét toàn thân & kiểm tra đồng phục)
  const [activeTab, setActiveTab] = useState<'attendance' | 'uniform'>('attendance');

  // Quy Trình 2 Bước Bắt Buộc (An Toàn Sinh Học):
  // Bước 1 ('step1_face'): Nhận diện mặt (Không đeo khẩu trang) -> Ghi nhớ nhân sự A
  // Bước 2 ('step2_uniform'): Quét trang phục & Khẩu trang (Bắt buộc đeo khẩu trang) khi bấm Bước tiếp theo
  // Hoàn tất ('completed'): Chúc mừng và tự động sẵn sàng cho nhân viên tiếp theo
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

  // Camera Source Mode: 'webcam' (Browser Live AI) vs 'hardware' (Server MJPEG Stream 30FPS)
  const [cameraMode, setCameraMode] = useState<'webcam' | 'hardware'>('webcam');

  // Staff & Attendance State
  const [staffList, setStaffList] = useState<any[]>([]);
  const [attendanceLogs, setAttendanceLogs] = useState<any[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<string>('');
  const [checkType, setCheckType] = useState<'check_in' | 'check_out' | 'instant'>('check_in');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Vision Health
  const [visionOnline, setVisionOnline] = useState<boolean>(false);

  // Live Camera State
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

  // Enroll FaceID Modal State
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollStaffId, setEnrollStaffId] = useState('');
  const [enrollStaffName, setEnrollStaffName] = useState('');
  const [enrollRole, setEnrollRole] = useState('Kỹ thuật viên');
  const [enrollPenId, setEnrollPenId] = useState(currentPenId || '123');
  const [enrollFile, setEnrollFile] = useState<File | null>(null);
  const [enrollPreviewUrl, setEnrollPreviewUrl] = useState<string | null>(null);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [enrollModalMsg, setEnrollModalMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const enrollFileInputRef = useRef<HTMLInputElement>(null);

  // References
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const liveLoopIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hardwarePollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isProcessingFrameRef = useRef<boolean>(false);
  const bannerTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const frameCountRef = useRef<number>(0);
  const lastFpsCalcTimeRef = useRef<number>(performance.now());
  const lastHardwareCheckinTimeRef = useRef<Record<string, number>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uniformFileInputRef = useRef<HTMLInputElement | null>(null);

  // Uniform Inspection Rule
  const [uniformRuleWeekday, setUniformRuleWeekday] = useState<number>(-1);

  // Initial Data
  useEffect(() => {
    fetchInitialData();
    checkEngine();
  }, [currentPenId]);

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

  // Web Audio Synthetic Chime on Successful Face Recognition
  const playSuccessChime = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch (e) {
      // Audio autoplay blocked or unsupported
    }
  }, []);

  // ─────────────────────────────────────────────────────────────
  // WEBCAM CONTROLS (Client-Side HTML5 Live Stream)
  // ─────────────────────────────────────────────────────────────
  const startCamera = async () => {
    try {
      setStatusMessage(null);

      // Release server hardware camera first if it was locking /dev/video0
      try {
        await stopCameraDeviceAPI();
        await new Promise(r => setTimeout(r, 200));
      } catch (e) {}

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false
      });

      mediaStreamRef.current = stream;
      setCameraMode('webcam');
      setIsCameraActive(true);
      setIsLivePaused(false);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play().catch(console.error);
        };
      }
    } catch (err: any) {
      console.warn('Webcam getUserMedia error:', err);
      // Auto fallback to Server Camera mode if browser cannot open webcam (e.g. device busy or headless)
      setStatusMessage({
        type: 'error',
        text: `Máy ảnh trên trình duyệt không mở được (${err.name || 'đang bận'}). Tự động chuyển sang máy ảnh chuồng trại...`
      });
      switchToHardwareMode();
    }
  };

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (liveLoopIntervalRef.current) {
      clearInterval(liveLoopIntervalRef.current);
      liveLoopIntervalRef.current = null;
    }
    if (hardwarePollIntervalRef.current) {
      clearInterval(hardwarePollIntervalRef.current);
      hardwarePollIntervalRef.current = null;
    }
    if (cameraMode === 'hardware') {
      stopCameraDeviceAPI().catch(() => {});
    }
    clearOverlayCanvas();
    setIsCameraActive(false);
    setLiveScanFps(0);
    setLiveFaces([]);
  };

  // ─────────────────────────────────────────────────────────────
  // 2-STEP PROTOCOL CONTROLS & HANDLERS (FACEID -> UNIFORM)
  // ─────────────────────────────────────────────────────────────
  const goToStep2 = () => {
    if (!identifiedStaff) return;
    setCheckinStep('step2_uniform');
    setActiveTab('uniform');
    step2HoldCountRef.current = 0;
    setStatusMessage({
      type: 'success',
      text: `Chuyển sang Bước 2: Quét trang phục & khẩu trang bắt buộc cho ${identifiedStaff.staffName}.`
    });
  };

  const goBackToStep1 = () => {
    setCheckinStep('step1_face');
    setActiveTab('attendance');
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
    setActiveTab('attendance');
  };

  const handleFinalizeTwoStepCheckIn = useCallback(async (staff: any, uniformData: any) => {
    if (isFinalizingCheckin || !staff) return;
    setIsFinalizingCheckin(true);
    try {
      const maskColor = uniformData?.mask?.mask_color === 'blue' ? 'xanh y tế' : (uniformData?.mask?.mask_color || 'y tế');
      const noteMsg = `Vào ca thành công (Quy trình 2 bước: Nhận diện khuôn mặt + Khẩu trang ${maskColor} & Áo ${uniformData?.shirt_color || 'bảo hộ'} + Quần ${uniformData?.pants_color || 'tối màu'})`;

      await checkInStaff({
        staffId: staff.staffId,
        penId: currentPenId || '123',
        checkType,
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
        onNotification('Vào Ca Thành Công', `🎉 ${staff.staffName} (${staff.staffId}) đã hoàn thành 2 bước đạt chuẩn an toàn sinh học!`);
      }

      getStaffAttendanceHistory(20).then(setAttendanceLogs).catch(() => {});

      // Đếm ngược 8 giây tự động sẵn sàng đón nhân sự tiếp theo
      let count = 8;
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

  const togglePauseLive = () => {
    setIsLivePaused(prev => !prev);
    if (!isLivePaused) {
      clearOverlayCanvas();
    }
  };

  const clearOverlayCanvas = () => {
    const canvas = overlayCanvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // LIVE CANVAS HUD RENDERING ENGINE
  // ─────────────────────────────────────────────────────────────
  const renderLiveHud = useCallback((
    faces: any[],
    uniform: any,
    currentTab: 'attendance' | 'uniform'
  ) => {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas pixel buffer to actual video resolution
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;
    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width = vw;
      canvas.height = vh;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Coordinate conversion helper (Selfie mirrored video mode)
    const getX = (origX: number, origW: number) => {
      return vw - (origX + origW);
    };

    // 1. Draw Face Detection Boxes
    faces.forEach((f) => {
      if (!f.location) return;
      const [top, right, bottom, left] = f.location;
      const boxW = right - left;
      const boxH = bottom - top;
      const boxX = getX(left, boxW);
      const boxY = top;

      const sid = f.student_id || f.staff_id || f.id;
      const isKnown = Boolean(sid && sid !== 'UNKNOWN');
      const isReal = f.liveness ? f.liveness.is_real : true;
      const confPercent = Math.round((f.confidence || 0) * 100);

      let strokeColor = '#10b981'; // Green: Known & Real
      let tagBg = '#065f46';
      let labelText = `${f.name || 'Nhân sự'} (${sid || ''}) [${confPercent}%]`;

      if (!isReal) {
        strokeColor = '#ef4444'; // Red: Spoof
        tagBg = '#991b1b';
        labelText = `⚠️ CẢNH BÁO: ẢNH GIẢ MẠO`;
      } else if (!isKnown) {
        strokeColor = '#f59e0b'; // Amber: Unknown
        tagBg = '#92400e';
        labelText = `NGƯỜI LẠ [${confPercent}%]`;
      }

      // Draw Sci-Fi Corner Brackets
      ctx.lineWidth = 3;
      ctx.strokeStyle = strokeColor;
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 8;

      const cornerLen = Math.min(20, boxW / 4, boxH / 4);
      // Top-Left
      ctx.beginPath();
      ctx.moveTo(boxX, boxY + cornerLen);
      ctx.lineTo(boxX, boxY);
      ctx.lineTo(boxX + cornerLen, boxY);
      ctx.stroke();

      // Top-Right
      ctx.beginPath();
      ctx.moveTo(boxX + boxW - cornerLen, boxY);
      ctx.lineTo(boxX + boxW, boxY);
      ctx.lineTo(boxX + boxW, boxY + cornerLen);
      ctx.stroke();

      // Bottom-Left
      ctx.beginPath();
      ctx.moveTo(boxX, boxY + boxH - cornerLen);
      ctx.lineTo(boxX, boxY + boxH);
      ctx.lineTo(boxX + cornerLen, boxY + boxH);
      ctx.stroke();

      // Bottom-Right
      ctx.beginPath();
      ctx.moveTo(boxX + boxW - cornerLen, boxY + boxH);
      ctx.lineTo(boxX + boxW, boxY + boxH);
      ctx.lineTo(boxX + boxW, boxY + boxH - cornerLen);
      ctx.stroke();

      // Bounding Box Inner Tint
      ctx.shadowBlur = 0;
      ctx.fillStyle = isReal ? (isKnown ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)') : 'rgba(239, 68, 68, 0.15)';
      ctx.fillRect(boxX, boxY, boxW, boxH);

      // Label Tag Pill
      ctx.font = 'bold 12px Inter, sans-serif';
      const textMetrics = ctx.measureText(labelText);
      const pillW = textMetrics.width + 16;
      const pillH = 22;
      const pillY = Math.max(4, boxY - pillH - 4);

      ctx.fillStyle = tagBg;
      ctx.beginPath();
      ctx.roundRect(boxX, pillY, pillW, pillH, 6);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, boxX + 8, pillY + 15);
    });

    // 2. Draw Uniform Inspection Boxes
    if (uniform && uniform.person_detected) {
      // Body Box
      if (uniform.body_box) {
        const [bx, by, bw, bh] = uniform.body_box;
        const bodyX = getX(bx, bw);
        const bodyY = by;
        const isOk = Boolean(uniform.is_correct);
        const bodyColor = isOk ? '#10b981' : '#f43f5e';

        ctx.lineWidth = 2;
        ctx.strokeStyle = bodyColor;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(bodyX, bodyY, bw, bh);
        ctx.setLineDash([]);

        // Body Tag Pill
        const bodyTag = `TOÀN THÂN: ${isOk ? '✅ ĐẠT ĐỒNG PHỤC' : '❌ VI PHẠM'}`;
        ctx.font = 'bold 11px Inter, sans-serif';
        const btw = ctx.measureText(bodyTag).width + 12;
        ctx.fillStyle = isOk ? '#065f46' : '#881337';
        ctx.beginPath();
        ctx.roundRect(bodyX, Math.max(4, bodyY - 20), btw, 18, 4);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.fillText(bodyTag, bodyX + 6, Math.max(4, bodyY - 20) + 13);
      }

      // Shirt Box
      if (uniform.shirt_box) {
        const [sx, sy, sw, sh] = uniform.shirt_box;
        const shirtX = getX(sx, sw);
        const shirtColor = '#06b6d4'; // Cyan

        ctx.lineWidth = 2;
        ctx.strokeStyle = shirtColor;
        ctx.strokeRect(shirtX, sy, sw, sh);

        const shirtTag = `👔 ÁO: ${uniform.shirt_color || 'N/A'} (${Math.round((uniform.shirt_ratio || 0) * 100)}%)`;
        ctx.font = 'bold 11px Inter, sans-serif';
        const stw = ctx.measureText(shirtTag).width + 10;
        ctx.fillStyle = '#164e63';
        ctx.beginPath();
        ctx.roundRect(shirtX, sy + 3, stw, 18, 4);
        ctx.fill();
        ctx.fillStyle = '#a5f3fc';
        ctx.fillText(shirtTag, shirtX + 5, sy + 16);
      }

      // Pants Box
      if (uniform.pants_box) {
        const [px, py, pw, ph] = uniform.pants_box;
        const pantsX = getX(px, pw);
        const pantsColor = '#f59e0b'; // Amber

        ctx.lineWidth = 2;
        ctx.strokeStyle = pantsColor;
        ctx.strokeRect(pantsX, py, pw, ph);

        const pantsTag = `👖 QUẦN: ${uniform.pants_color || 'N/A'} (${Math.round((uniform.pants_ratio || 0) * 100)}%)`;
        ctx.font = 'bold 11px Inter, sans-serif';
        const ptw = ctx.measureText(pantsTag).width + 10;
        ctx.fillStyle = '#78350f';
        ctx.beginPath();
        ctx.roundRect(pantsX, py + 3, ptw, 18, 4);
        ctx.fill();
        ctx.fillStyle = '#fde68a';
        ctx.fillText(pantsTag, pantsX + 5, py + 16);
      }

      // 4. Mask Box (Khẩu trang y tế - Chuẩn image.png)
      if (uniform.mask && uniform.mask.mask_box) {
        const [mx, my, mw, mh] = uniform.mask.mask_box;
        const maskX = getX(mx, mw);
        const hasMask = Boolean(uniform.mask.has_mask);
        const maskStroke = hasMask ? '#10b981' : '#ef4444';

        ctx.lineWidth = 2.5;
        ctx.strokeStyle = maskStroke;
        ctx.strokeRect(maskX, my, mw, mh);

        const maskColorName = uniform.mask.mask_color === 'blue' ? 'XANH Y TẾ' : (uniform.mask.mask_color || '').toUpperCase();
        const maskTag = hasMask
          ? `😷 KHẨU TRANG: ĐÃ ĐEO (${maskColorName})`
          : `⚠️ BẮT BUỘC: CHƯA ĐEO KHẨU TRANG!`;

        ctx.font = 'bold 11px Inter, sans-serif';
        const mtw = ctx.measureText(maskTag).width + 10;
        ctx.fillStyle = hasMask ? '#065f46' : '#991b1b';
        ctx.beginPath();
        ctx.roundRect(maskX, Math.max(4, my - 20), mtw, 18, 4);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.fillText(maskTag, maskX + 5, Math.max(4, my - 20) + 13);
      }
    }
  }, []);

  // ─────────────────────────────────────────────────────────────
  // CONTINUOUS LIVE SCANNING LOOP (Webcam Mode)
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isCameraActive || isLivePaused || cameraMode !== 'webcam') {
      if (liveLoopIntervalRef.current) {
        clearInterval(liveLoopIntervalRef.current);
        liveLoopIntervalRef.current = null;
      }
      return;
    }

    // Capture small lightweight frame offscreen (480x360 JPEG 65% for ultra-fast processing)
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = 480;
    offscreenCanvas.height = 360;
    const offscreenCtx = offscreenCanvas.getContext('2d');

    const runLiveScanTick = async () => {
      if (isProcessingFrameRef.current) return;
      if (!videoRef.current || videoRef.current.readyState < 2) return;

      try {
        isProcessingFrameRef.current = true;
        const t0 = performance.now();

        if (offscreenCtx) {
          offscreenCtx.drawImage(videoRef.current, 0, 0, 480, 360);
        }
        const b64 = offscreenCanvas.toDataURL('image/jpeg', 0.65);

        // Gửi tới API Live AI Scan (autoCheckin=false để giao diện kiểm soát chặt chẽ quy trình 2 bước)
        const res = await liveScanStaffAPI({
          imageBase64: b64,
          penId: currentPenId || '123',
          checkType,
          weekday: uniformRuleWeekday,
          autoCheckin: false,
          returnAnnotated: false
        });

        const dt = Math.round(performance.now() - t0);
        setLiveLatencyMs(dt);

        // Calculate running FPS
        frameCountRef.current += 1;
        const now = performance.now();
        if (now - lastFpsCalcTimeRef.current >= 1000) {
          const fps = (frameCountRef.current * 1000) / (now - lastFpsCalcTimeRef.current);
          setLiveScanFps(Math.round(fps * 10) / 10);
          frameCountRef.current = 0;
          lastFpsCalcTimeRef.current = now;
        }

        const faces = res.faces || [];
        setLiveFaces(faces);

        if (res.uniform) {
          setUniformResult(res.uniform);
        }

        // BƯỚC 1: XÁC THỰC DANH TÍNH KHUÔN MẶT (BỎ KHẨU TRANG)
        // Hệ thống phát hiện khuôn mặt hợp lệ -> Ghi nhớ danh tính nhân sự A
        if (checkinStep === 'step1_face' && !identifiedStaff) {
          const valid = faces.find((f: any) => {
            const sid = f.student_id || f.staff_id || f.id;
            return sid && sid !== 'UNKNOWN' && (f.confidence || 0) >= 0.55 && (f.liveness ? f.liveness.is_real : true);
          });
          if (valid) {
            playSuccessChime();
            const sid = valid.student_id || valid.staff_id || valid.id;
            const staffObj = {
              staffId: sid,
              staffName: valid.name || 'Nhân sự',
              confidence: valid.confidence || 0.95,
              isReal: valid.liveness ? valid.liveness.is_real : true,
              detectedAt: Date.now()
            };
            setIdentifiedStaff(staffObj);
            setSelectedStaffId(sid);
            if (onNotification) {
              onNotification('Xác thực khuôn mặt', `✅ Đã nhận diện ${staffObj.staffName}. Vui lòng bấm [Bước tiếp theo] để quét trang phục!`);
            }
          }
        }

        // BƯỚC 2: QUÉT TRANG PHỤC & KHẨU TRANG (BẮT BUỘC ĐEO KHẨU TRANG)
        // Khi nhân sự A đã đeo khẩu trang và đạt chuẩn đồng phục (áo xanh, quần tối màu)
        if (checkinStep === 'step2_uniform' && identifiedStaff && !isFinalizingCheckin) {
          if (res.uniform && res.uniform.is_correct) {
            step2HoldCountRef.current += 1;
            if (step2HoldCountRef.current >= 2) {
              handleFinalizeTwoStepCheckIn(identifiedStaff, res.uniform);
            }
          } else {
            step2HoldCountRef.current = 0;
          }
        }

        // 3. Render Canvas HUD Overlay
        renderLiveHud(faces, res.uniform, activeTab);

      } catch (err) {
        // Drop failed frame silently to maintain live smoothness
      } finally {
        isProcessingFrameRef.current = false;
      }
    };

    // Run continuous loop every 260ms (~3.8 FPS live AI inference)
    liveLoopIntervalRef.current = setInterval(runLiveScanTick, 260);

    return () => {
      if (liveLoopIntervalRef.current) {
        clearInterval(liveLoopIntervalRef.current);
        liveLoopIntervalRef.current = null;
      }
    };
  }, [isCameraActive, isLivePaused, cameraMode, checkType, currentPenId, uniformRuleWeekday, activeTab, playSuccessChime, renderLiveHud, onNotification, checkinStep, identifiedStaff, isFinalizingCheckin, handleFinalizeTwoStepCheckIn]);

  // ─────────────────────────────────────────────────────────────
  // HARDWARE SERVER CAMERA MODE (MJPEG Stream + Telemetry Polling)
  // ─────────────────────────────────────────────────────────────
  const switchToHardwareMode = async () => {
    // Stop browser webcam first
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    clearOverlayCanvas();
    setStatusMessage(null);
    setCameraMode('hardware');
    setIsCameraActive(true);
    setIsLivePaused(false);

    const newKey = Date.now();
    setHardwareStreamKey(newKey);
    setHardwareStreamUrl(`${FACE_API_URL}/api/v1/camera/video_feed?overlay=true&t=${newKey}`);

    try {
      await startCameraDeviceAPI('0', uniformRuleWeekday);
    } catch (e) {
      console.warn('Hardware camera start warning:', e);
    }
  };

  const switchToWebcamMode = () => {
    stopCameraDeviceAPI().catch(() => {});
    setCameraMode('webcam');
    startCamera();
  };

  // Poll hardware telemetry when in hardware mode
  useEffect(() => {
    if (cameraMode !== 'hardware' || !isCameraActive) {
      if (hardwarePollIntervalRef.current) {
        clearInterval(hardwarePollIntervalRef.current);
        hardwarePollIntervalRef.current = null;
      }
      return;
    }

    hardwarePollIntervalRef.current = setInterval(async () => {
      try {
        const telemetry = await getCameraLatestTelemetryAPI();
        if (telemetry) {
          setLiveScanFps(telemetry.capture_fps || 0);
          setLiveLatencyMs(Math.round(telemetry.process_time_ms || 0));
          if (telemetry.faces) setLiveFaces(telemetry.faces);
          if (telemetry.uniform) setUniformResult(telemetry.uniform);

          // BƯỚC 1: NHẬN DIỆN MẶT TRÊN CAMERA HARDWARE (BỎ KHẨU TRANG)
          if (checkinStep === 'step1_face' && !identifiedStaff && telemetry.faces && telemetry.faces.length > 0) {
            const valid = telemetry.faces.find((f: any) => {
              const sid = f.student_id || f.staff_id || f.id;
              return sid && sid !== 'UNKNOWN' && (f.confidence || 0) >= 0.55 && (f.liveness ? f.liveness.is_real : true);
            });
            if (valid) {
              playSuccessChime();
              const sid = valid.student_id || valid.staff_id || valid.id;
              setIdentifiedStaff({
                staffId: sid,
                staffName: valid.name || 'Nhân sự',
                confidence: valid.confidence || 0.95,
                isReal: valid.liveness ? valid.liveness.is_real : true,
                detectedAt: Date.now()
              });
              setSelectedStaffId(sid);
            }
          }

          // BƯỚC 2: QUÉT TRANG PHỤC & KHẨU TRANG TRÊN CAMERA HARDWARE (BẮT BUỘC)
          if (checkinStep === 'step2_uniform' && identifiedStaff && telemetry.uniform?.is_correct && !isFinalizingCheckin) {
            handleFinalizeTwoStepCheckIn(identifiedStaff, telemetry.uniform);
          }
        }
      } catch (e) {}
    }, 400);

    return () => {
      if (hardwarePollIntervalRef.current) {
        clearInterval(hardwarePollIntervalRef.current);
        hardwarePollIntervalRef.current = null;
      }
    };
  }, [cameraMode, isCameraActive, activeTab, checkType, currentPenId, playSuccessChime, checkinStep, identifiedStaff, isFinalizingCheckin, handleFinalizeTwoStepCheckIn]);

  // Manual 1-click check-in
  const handleManualCheckIn = async () => {
    if (!selectedStaffId) return;
    setIsLoading(true);
    setStatusMessage(null);

    try {
      const staffObj = staffList.find(s => s.id === selectedStaffId);
      if (staffObj && checkType === 'check_in') {
        setIdentifiedStaff({
          staffId: staffObj.id,
          staffName: staffObj.name,
          confidence: 1.0,
          isReal: true,
          detectedAt: Date.now()
        });
      }

      await checkInStaff({
        staffId: selectedStaffId,
        penId: currentPenId || '123',
        checkType,
        note: `Chấm công thủ công 24/7 mọi lúc`
      });

      const typeLabel = checkType === 'check_in' ? 'Vào ca' : checkType === 'check_out' ? 'Tan ca' : 'Chấm công';
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
        text: err.message || 'Lỗi khi chấm công.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Upload photo checkin fallback
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

      const msg = `✅ Đã nhận diện ảnh: ${staffName} (${staffId}). Vui lòng bấm [Bước tiếp theo] để quét trang phục bắt buộc!`;
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

  // Upload photo uniform fallback
  const handleUniformFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setStatusMessage(null);
    try {
      const res = await scanUniformUploadAPI(file, uniformRuleWeekday);
      const u = res.uniform || {};
      setUniformResult(u);

      if (u.person_detected) {
        if (u.is_correct) {
          if (identifiedStaff) {
            handleFinalizeTwoStepCheckIn(identifiedStaff, u);
          } else {
            setStatusMessage({
              type: 'success',
              text: `✅ ${u.message || 'Ảnh tải lên: Đúng quy định đồng phục & khẩu trang!'}`
            });
          }
        } else {
          setStatusMessage({
            type: 'error',
            text: `❌ ${u.message || 'Ảnh tải lên: Vi phạm quy định đồng phục!'}`
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
        text: err.message || 'Lỗi khi upload ảnh kiểm tra đồng phục.'
      });
    } finally {
      setIsLoading(false);
      if (uniformFileInputRef.current) uniformFileInputRef.current.value = '';
    }
  };

  // ─────────────────────────────────────────────────────────────
  // ENROLL FACEID HANDLERS
  // ─────────────────────────────────────────────────────────────
  const handleCaptureEnrollFromWebcam = () => {
    if (!videoRef.current) return;
    const v = videoRef.current;
    if (v.videoWidth === 0 || v.videoHeight === 0) return;
    const canvas = document.createElement('canvas');
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // Mirror back because webcam is mirrored in CSS
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `${enrollStaffId || 'face'}.jpg`, { type: 'image/jpeg' });
        setEnrollFile(file);
        setEnrollPreviewUrl(canvas.toDataURL('image/jpeg', 0.9));
      }
    }, 'image/jpeg', 0.9);
  };

  const handleEnrollFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setEnrollFile(file);
    const reader = new FileReader();
    reader.onload = () => {
      setEnrollPreviewUrl(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleEnrollSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollStaffId.trim() || !enrollStaffName.trim() || !enrollFile) {
      setEnrollModalMsg({ type: 'error', text: 'Vui lòng điền đủ Mã NV, Tên và chọn ảnh khuôn mặt.' });
      return;
    }
    setIsEnrolling(true);
    setEnrollModalMsg(null);
    try {
      const res = await enrollStaffFace(
        enrollStaffId.trim(),
        enrollStaffName.trim(),
        enrollFile,
        enrollRole,
        enrollPenId || currentPenId || '123'
      );
      setEnrollModalMsg({
        type: 'success',
        text: res.message || `Đã đăng ký khuôn mặt thành công cho ${enrollStaffName}!`
      });
      await fetchInitialData();
      if (onNotification) {
        onNotification('Đăng ký khuôn mặt', `Đã thêm thành công ${enrollStaffName} (${enrollStaffId})`);
      }
      setTimeout(() => {
        setIsEnrollModalOpen(false);
        setEnrollFile(null);
        setEnrollPreviewUrl(null);
        setEnrollModalMsg(null);
      }, 1500);
    } catch (err: any) {
      setEnrollModalMsg({
        type: 'error',
        text: err.message || 'Lỗi khi đăng ký khuôn mặt. Vui lòng thử lại với ảnh rõ nét hơn.'
      });
    } finally {
      setIsEnrolling(false);
    }
  };

  const handleReloadFaces = async () => {
    try {
      setIsLoading(true);
      const res = await reloadStaffFacesAPI();
      setStatusMessage({
        type: 'success',
        text: `✅ ${res.message || `Đã làm mới ${res.total_faces || 0} khuôn mặt từ thư mục known_faces!`}`
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

  // Calculate today's headcount
  const todayDateStr = new Date().toISOString().split('T')[0];
  const todayLogs = attendanceLogs.filter(l => (l.created_at || '').startsWith(todayDateStr));
  const activeStaffIds = new Set(todayLogs.filter(l => l.check_type !== 'check_out').map(l => l.staff_id));

  return (
    <div className="bg-fb-card rounded-2xl p-4 md:p-5 shadow-fb-card border border-fb-divider space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-fb-divider gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-teal-500 to-emerald-500 text-white flex items-center justify-center shadow-md">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="font-bold text-base text-fb-text flex items-center gap-2">
              <span>Hệ Thống Quét Máy Ảnh Trực Tiếp 24/7</span>
              <span className="text-[10px] font-mono uppercase bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                Phát Trực Tiếp
              </span>
            </h3>
            <p className="text-xs text-fb-muted">
              Bật máy ảnh là tự động quét liên tục thời gian thực • Nhận diện khuôn mặt & Quét toàn thân kiểm tra đồng phục
            </p>
          </div>
        </div>

        {/* Engine status & Actions */}
        <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
          <span 
            className={`text-[11px] font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5 border ${
              visionOnline 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${visionOnline ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            {visionOnline ? 'Trí Tuệ Nhân Tạo: Trực Tuyến' : 'Hệ Thống Nhận Diện Sẵn Sàng'}
          </span>

          {/* Button: Đăng ký khuôn mặt mới */}
          <button
            onClick={() => {
              setEnrollStaffId(`NV${String(staffList.length + 1).padStart(2, '0')}`);
              setEnrollPenId(currentPenId || '123');
              setIsEnrollModalOpen(true);
            }}
            className="text-xs px-3 py-1.5 rounded-xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-sm transition flex items-center gap-1.5 cursor-pointer"
            title="Đăng ký thêm khuôn mặt mới vào hệ thống điểm danh"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>+ Thêm Khuôn Mặt</span>
          </button>

          <button
            onClick={handleReloadFaces}
            title="Làm mới thư mục ảnh known_faces"
            className="p-1.5 rounded-lg hover:bg-fb-hover text-fb-muted transition"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert / Status Toast */}
      {statusMessage && (
        <div 
          className={`p-3 rounded-xl text-xs font-medium flex items-center gap-2 transition ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* 2-STEP BIO-SECURITY ENTRANCE PROTOCOL HEADER */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 p-3.5 rounded-2xl border border-slate-800 text-white space-y-3 shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="font-extrabold text-xs uppercase tracking-wider text-emerald-400">
              Quy Trình Vào Ca 2 Bước Bắt Buộc (An Toàn Sinh Học)
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            {checkinStep === 'step1_face' 
              ? '👉 Bước 1: Xác Thực Khuôn Mặt' 
              : checkinStep === 'step2_uniform' 
              ? '👉 Bước 2: Quét Trang Phục & Khẩu Trang' 
              : '🎉 Hoàn Tất Vào Ca 100%'}
          </span>
        </div>

        {/* 2 Steps Indicator Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {/* STEP 1 PILL */}
          <button
            onClick={() => { setCheckinStep('step1_face'); setActiveTab('attendance'); }}
            className={`p-3 rounded-xl border text-left transition flex items-center justify-between cursor-pointer ${
              checkinStep === 'step1_face'
                ? 'bg-emerald-950/80 border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)]'
                : identifiedStaff
                ? 'bg-slate-900/90 border-emerald-600/70 text-slate-300'
                : 'bg-slate-900/40 border-slate-800 text-slate-500'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-black text-xs ${
                identifiedStaff
                  ? 'bg-emerald-500 text-slate-950 shadow'
                  : checkinStep === 'step1_face'
                  ? 'bg-emerald-500/30 text-emerald-300 border border-emerald-400 animate-pulse'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {identifiedStaff ? '✓' : '1'}
              </div>
              <div>
                <div className="font-bold text-xs flex items-center gap-1.5 text-white">
                  <span>Bước 1: Xác Thực Khuôn Mặt</span>
                  <span className="text-[10px] text-emerald-400 font-normal">(Bỏ khẩu trang)</span>
                </div>
                <div className="text-[10px] text-slate-400">
                  {identifiedStaff ? `Đã nhận diện: ${identifiedStaff.staffName} (${identifiedStaff.staffId})` : 'Đứng trước máy ảnh để nhận diện'}
                </div>
              </div>
            </div>
            {checkinStep === 'step1_face' && (
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
            )}
          </button>

          {/* STEP 2 PILL */}
          <button
            onClick={() => {
              if (identifiedStaff) {
                setCheckinStep('step2_uniform');
                setActiveTab('uniform');
              }
            }}
            disabled={!identifiedStaff}
            className={`p-3 rounded-xl border text-left transition flex items-center justify-between ${
              checkinStep === 'step2_uniform'
                ? 'bg-cyan-950/80 border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                : checkinStep === 'completed'
                ? 'bg-slate-900/90 border-emerald-600/70 text-slate-300'
                : 'bg-slate-900/40 border-slate-800 text-slate-500 cursor-not-allowed'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-black text-xs ${
                checkinStep === 'completed'
                  ? 'bg-emerald-500 text-slate-950 shadow'
                  : checkinStep === 'step2_uniform'
                  ? 'bg-cyan-500 text-slate-950 animate-pulse'
                  : 'bg-slate-800 text-slate-500'
              }`}>
                {checkinStep === 'completed' ? '✓' : '2'}
              </div>
              <div>
                <div className="font-bold text-xs flex items-center gap-1.5 text-white">
                  <span>Bước 2: Quét Trang Phục & Khẩu Trang</span>
                  <span className="text-[10px] text-cyan-400 font-normal">(Bắt buộc)</span>
                </div>
                <div className="text-[10px] text-slate-400">
                  {checkinStep === 'completed' 
                    ? 'Đã duyệt đạt chuẩn 100%' 
                    : identifiedStaff 
                    ? 'Đeo khẩu trang y tế và quét toàn thân' 
                    : 'Cần hoàn thành Bước 1 trước'}
                </div>
              </div>
            </div>
            {checkinStep === 'step2_uniform' && (
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            )}
          </button>
        </div>
      </div>

      {/* CONTEXTUAL STEP ACTION BANNERS */}
      {checkinStep === 'step1_face' && identifiedStaff && (
        <div className="p-4 bg-gradient-to-r from-emerald-950/95 via-teal-950/95 to-slate-950 border-2 border-emerald-400 text-white rounded-2xl shadow-xl flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in duration-300">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500 text-slate-950 font-black text-xl flex items-center justify-center shadow-lg">
              ✓
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider bg-emerald-400 text-slate-950 px-2 py-0.5 rounded-full">
                  Bước 1 Hoàn Tất
                </span>
                <span className="text-xs text-emerald-300 font-mono">
                  Khớp {Math.round(identifiedStaff.confidence * 100)}%
                </span>
              </div>
              <h4 className="text-base font-extrabold text-white mt-0.5">
                Đã ghi nhận nhân sự: <span className="text-emerald-300">{identifiedStaff.staffName} ({identifiedStaff.staffId})</span>
              </h4>
              <p className="text-xs text-amber-300 font-medium flex items-center gap-1.5 mt-1">
                <span>😷</span>
                <span><strong>Yêu cầu bắt buộc:</strong> Vui lòng <u>đeo khẩu trang y tế</u> và lùi lại để máy ảnh quét trang phục!</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={goToStep2}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl font-black text-xs uppercase tracking-wider bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 text-slate-950 shadow-[0_0_25px_rgba(6,182,212,0.6)] transition transform active:scale-95 flex items-center justify-center gap-2"
            >
              <span>Bước Tiếp Theo: Quét Trang Phục & Khẩu Trang</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={resetToStep1}
              className="px-3 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
              title="Nhận diện lại hoặc đổi người khác"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {checkinStep === 'step1_face' && !identifiedStaff && (
        <div className="p-3 bg-slate-100 border border-slate-200 rounded-xl flex items-center justify-between text-xs text-slate-700">
          <div className="flex items-center gap-2">
            <span className="text-base">💡</span>
            <span>
              <strong>Bước 1/2:</strong> Nhân sự đứng trước máy ảnh, <strong>bỏ khẩu trang</strong> để hệ thống nhận diện khuôn mặt. Sau khi nhận diện, hệ thống sẽ mở nút <strong>Bước tiếp theo</strong> để quét trang phục bắt buộc.
            </span>
          </div>
          <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full shrink-0">
            Đang chờ quét mặt
          </span>
        </div>
      )}

      {checkinStep === 'step2_uniform' && (
        <div className="p-4 bg-gradient-to-r from-cyan-950/95 via-slate-950 to-slate-900 border-2 border-cyan-400 text-white rounded-2xl shadow-xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-cyan-800/60 pb-2.5">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-cyan-500 text-slate-950 font-black text-base flex items-center justify-center shadow">
                2
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-cyan-500 text-slate-950 px-2 py-0.5 rounded-full">
                  Bước 2/2: Quét Trang Phục Bắt Buộc
                </span>
                <h4 className="text-sm font-bold text-white mt-0.5">
                  Đang kiểm tra: <span className="text-cyan-300 font-extrabold">{identifiedStaff?.staffName} ({identifiedStaff?.staffId})</span>
                </h4>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={goBackToStep1}
                className="text-[11px] px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                ← Quay lại Bước 1
              </button>
            </div>
          </div>

          {/* Real-time Bio-security Checklist */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
            {/* 1. Mask Check */}
            <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
              uniformResult?.mask?.has_mask ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200' : 'bg-rose-950/80 border-rose-500 text-rose-200'
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-base">😷</span>
                <div>
                  <div className="font-bold">1. Khẩu Trang Y Tế</div>
                  <div className="text-[10px] opacity-80">Bắt buộc che kín mũi miệng</div>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] uppercase ${
                uniformResult?.mask?.has_mask ? 'bg-emerald-500 text-slate-950' : 'bg-rose-500 text-white animate-pulse'
              }`}>
                {uniformResult?.mask?.has_mask ? (uniformResult.mask.mask_color === 'blue' ? '✓ ĐÃ ĐEO (XANH)' : '✓ ĐÃ ĐEO') : '✗ CHƯA ĐEO'}
              </span>
            </div>

            {/* 2. Shirt Check */}
            <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
              ['blue', 'cyan', 'white'].includes(uniformResult?.shirt_color) ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200' : 'bg-slate-900 border-slate-700 text-slate-300'
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-base">👔</span>
                <div>
                  <div className="font-bold">2. Áo Bảo Hộ</div>
                  <div className="text-[10px] opacity-80">Áo xanh dương / cyan</div>
                </div>
              </div>
              <span className="font-bold text-[10px] uppercase">
                {uniformResult?.shirt_color ? uniformResult.shirt_color.toUpperCase() : 'QUÉT...'}
              </span>
            </div>

            {/* 3. Pants Check */}
            <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
              uniformResult?.pants_color === 'dark' ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200' : 'bg-slate-900 border-slate-700 text-slate-300'
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-base">👖</span>
                <div>
                  <div className="font-bold">3. Quần Dài</div>
                  <div className="text-[10px] opacity-80">Quần tối màu</div>
                </div>
              </div>
              <span className="font-bold text-[10px] uppercase">
                {uniformResult?.pants_color ? uniformResult.pants_color.toUpperCase() : 'QUÉT...'}
              </span>
            </div>
          </div>

          {/* Status & Confirmation Action */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <div className="text-xs">
              {uniformResult?.is_correct ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  ✅ ĐẠT CHUẨN AN TOÀN SINH HỌC! Đang hoàn tất xác nhận vào ca...
                </span>
              ) : uniformResult?.mask && !uniformResult.mask.has_mask ? (
                <span className="text-rose-400 font-bold flex items-center gap-1.5">
                  ⚠️ Vui lòng đeo khẩu trang y tế che kín mũi miệng để được duyệt vào ca!
                </span>
              ) : (
                <span className="text-slate-400">
                  Đứng lùi lại cách máy ảnh 1.5m - 2m để quét toàn thân (áo + quần + khẩu trang).
                </span>
              )}
            </div>

            {uniformResult?.is_correct && (
              <button
                onClick={() => handleFinalizeTwoStepCheckIn(identifiedStaff, uniformResult)}
                disabled={isFinalizingCheckin}
                className="px-5 py-2.5 rounded-xl font-black text-xs uppercase bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg flex items-center justify-center gap-2 transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Xác Nhận Hoàn Tất Vào Ca</span>
              </button>
            )}
          </div>
        </div>
      )}

      {checkinStep === 'completed' && (
        <div className="p-5 bg-gradient-to-r from-emerald-950 via-teal-950 to-slate-950 border-2 border-emerald-400 text-white rounded-2xl shadow-[0_0_40px_rgba(16,185,129,0.35)] flex flex-col sm:flex-row items-center justify-between gap-4 animate-in zoom-in-95 duration-300">
          <div className="flex items-center gap-3.5">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 font-black text-2xl flex items-center justify-center shadow-lg">
              🎉
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-wider bg-emerald-400 text-slate-950 px-2.5 py-0.5 rounded-full">
                  Hoàn Tất Quy Trình 2 Bước
                </span>
                <span className="text-xs text-emerald-300 font-mono">
                  {new Date().toLocaleTimeString()}
                </span>
              </div>
              <h3 className="text-lg font-black text-white mt-1">
                Vào Ca Thành Công: {identifiedStaff?.staffName} ({identifiedStaff?.staffId})
              </h3>
              <p className="text-xs text-emerald-300 font-medium mt-0.5">
                ✓ Đã xác thực khuôn mặt &nbsp;•&nbsp; ✓ Đã kiểm tra khẩu trang y tế &nbsp;•&nbsp; ✓ Đạt chuẩn trang phục bảo hộ 100%
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              onClick={resetToStep1}
              className="flex-1 sm:flex-none px-6 py-3 rounded-xl font-bold text-xs uppercase tracking-wider bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg transition flex items-center justify-center gap-2 cursor-pointer"
            >
              <UserCheck className="w-4 h-4" />
              <span>Tiếp Tục Người Kế Tiếp {autoResetTimer ? `(${autoResetTimer}s)` : ''}</span>
            </button>
          </div>
        </div>
      )}

      {/* FUNCTION TAB SWITCHER: Face Attendance vs Full-Body Uniform */}
      <div className="flex p-1 bg-slate-100 rounded-xl gap-1">
        <button
          onClick={() => { setActiveTab('attendance'); setCheckinStep('step1_face'); }}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'attendance'
              ? 'bg-white text-emerald-800 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <UserCheck className="w-4 h-4 text-emerald-600" />
          <span>👤 Điểm Danh Khuôn Mặt (Bước 1)</span>
        </button>

        <button
          onClick={() => { setActiveTab('uniform'); if (identifiedStaff) setCheckinStep('step2_uniform'); }}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'uniform'
              ? 'bg-white text-cyan-800 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Shirt className="w-4 h-4 text-cyan-600" />
          <span>👔 Kiểm Tra Trang Phục & Khẩu Trang (Bước 2)</span>
        </button>
      </div>

      {/* SHARED LIVE CAMERA VIEWFINDER */}
      <div className="border border-fb-divider rounded-2xl p-4 bg-slate-950 text-slate-100 shadow-inner space-y-3">
        {/* Viewfinder Header Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
            <h4 className="font-bold text-sm text-cyan-300 flex items-center gap-2">
              <span>Luồng Quét Máy Ảnh Thời Gian Thực</span>
              {isCameraActive && (
                <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded-full font-mono uppercase">
                  ● TRỰC TIẾP ({liveScanFps > 0 ? `${liveScanFps} khung hình/giây` : 'Đang quét...'})
                </span>
              )}
            </h4>
          </div>

          {/* Camera Controls & Mode Toggle */}
          <div className="flex items-center gap-2 flex-wrap">
            {isCameraActive ? (
              <>
                {/* Pause/Resume Live AI Scan */}
                <button
                  onClick={togglePauseLive}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-semibold transition flex items-center gap-1 cursor-pointer ${
                    isLivePaused 
                      ? 'bg-amber-600 hover:bg-amber-500 text-white' 
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  {isLivePaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                  <span>{isLivePaused ? 'Tiếp Tục Quét' : 'Tạm Dừng'}</span>
                </button>

                {/* Source Switcher */}
                <button
                  onClick={cameraMode === 'webcam' ? switchToHardwareMode : switchToWebcamMode}
                  className="text-[11px] px-2.5 py-1 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition flex items-center gap-1 cursor-pointer"
                  title="Chuyển đổi nguồn máy ảnh"
                >
                  <Video className="w-3.5 h-3.5" />
                  <span>{cameraMode === 'webcam' ? 'Dùng Máy Ảnh Chuồng' : 'Dùng Máy Ảnh Máy Tính'}</span>
                </button>

                {/* Stop Camera */}
                <button
                  onClick={stopCamera}
                  className="text-[11px] px-3 py-1 rounded-lg font-semibold bg-rose-900/70 hover:bg-rose-800 text-rose-200 transition flex items-center gap-1 shadow cursor-pointer"
                >
                  <CameraOff className="w-3.5 h-3.5" />
                  <span>Tắt Máy Ảnh</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={startCamera}
                  className="text-[11px] px-4 py-2 rounded-xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg transition flex items-center gap-2 cursor-pointer"
                >
                  <Camera className="w-4 h-4" />
                  <span>Bật Máy Ảnh Máy Tính</span>
                </button>

                <button
                  onClick={switchToHardwareMode}
                  className="text-[11px] px-3.5 py-2 rounded-xl font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Video className="w-4 h-4" />
                  <span>Mở Máy Ảnh Chuồng Trại</span>
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-[11px] px-2.5 py-2 rounded-xl font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 cursor-pointer"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Tải ảnh</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Video Viewfinder Container (ALWAYS MOUNTED TO PREVENT NULL REFS) */}
        <div className="relative rounded-2xl overflow-hidden bg-black flex items-center justify-center border border-slate-800 aspect-video max-h-[460px] mx-auto shadow-2xl">
          {/* 1. Client Webcam Video Element */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${isCameraActive && cameraMode === 'webcam' ? 'block' : 'hidden'}`}
            style={{ transform: 'scaleX(-1)' }}
          />

          {/* 2. Client Live Canvas HUD Overlay */}
          <canvas
            ref={overlayCanvasRef}
            className={`absolute inset-0 w-full h-full pointer-events-none ${isCameraActive && cameraMode === 'webcam' ? 'block' : 'hidden'}`}
          />

          {/* 3. Server Hardware MJPEG Video Stream (30 FPS OpenCV HUD) */}
          {isCameraActive && cameraMode === 'hardware' && (
            <img
              key={hardwareStreamKey}
              src={hardwareStreamUrl}
              alt="Luồng máy ảnh trực tiếp"
              className="w-full h-full object-contain"
              onError={() => {
                // Tự động chuyển đổi giữa direct FACE_API_URL và BACKEND_URL proxy
                console.warn('Stream feed failed, toggling direct vs proxy URL...');
                setHardwareStreamUrl((prev) =>
                  prev.includes(FACE_API_URL)
                    ? `${BACKEND_URL}/api/camera/video_feed?overlay=true&t=${Date.now()}`
                    : `${FACE_API_URL}/api/v1/camera/video_feed?overlay=true&t=${Date.now()}`
                );
              }}
            />
          )}

          {/* 4. Inactive Placeholder Cover */}
          {!isCameraActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950 p-6 space-y-3 z-10">
              <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 text-cyan-400 flex items-center justify-center shadow-inner">
                <Camera className="w-6 h-6" />
              </div>
              <div className="text-center space-y-1">
                <h5 className="font-bold text-sm text-slate-200">
                  Máy Ảnh Đang Tắt • Sẵn Sàng Nhận Diện 24/7
                </h5>
                <p className="text-xs text-slate-400 max-w-md">
                  Bấm một trong hai nút bên dưới để bắt đầu quét trực tiếp theo thời gian thực (tự động hoàn toàn):
                </p>
              </div>
              <div className="pt-2 flex flex-wrap justify-center gap-2.5">
                <button
                  onClick={startCamera}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold text-xs shadow-lg transition flex items-center gap-2 cursor-pointer"
                >
                  <Camera className="w-4 h-4" />
                  <span>Bật Máy Ảnh Máy Tính</span>
                </button>
                <button
                  onClick={switchToHardwareMode}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 font-bold text-xs transition flex items-center gap-2 cursor-pointer"
                >
                  <Video className="w-4 h-4" />
                  <span>Mở Máy Ảnh Chuồng Trại</span>
                </button>
              </div>
            </div>
          )}

          {/* TOP FLOATING LIVE BADGES (When Camera is Active) */}
          {isCameraActive && (
            <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10">
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md border border-slate-700 text-cyan-300 text-[10px] font-mono font-bold px-2.5 py-1 rounded-full shadow">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {cameraMode === 'webcam' ? 'MÁY ẢNH MÁY TÍNH' : 'MÁY ẢNH CHUỒNG TRẠI'}
                </span>

                {activeTab === 'attendance' && (
                  <span className="bg-emerald-950/80 backdrop-blur-md border border-emerald-700 text-emerald-300 text-[10px] font-bold px-2 py-1 rounded-full">
                    {checkType === 'check_in' ? '🟢 Đang vào ca' : checkType === 'check_out' ? '🔴 Đang tan ca' : '⚡ Chấm công tức thì'}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 bg-slate-900/80 backdrop-blur-md border border-slate-700 text-slate-300 text-[10px] font-mono px-2.5 py-1 rounded-full shadow">
                <span className="text-emerald-400 font-bold">{liveScanFps} khung hình/giây</span>
                <span>•</span>
                <span className="text-cyan-400">{liveLatencyMs}ms</span>
              </div>
            </div>
          )}

          {/* FLOATING SUCCESS ATTENDANCE BANNER (Automatic Live Trigger) */}
          {liveSuccessBanner && (
            <div className="absolute top-12 inset-x-4 flex justify-center pointer-events-none z-20 animate-in slide-in-from-top-4 duration-300">
              <div className="bg-emerald-950/95 border-2 border-emerald-400 text-emerald-100 px-5 py-3 rounded-2xl shadow-[0_0_35px_rgba(16,185,129,0.6)] backdrop-blur-md flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500 text-slate-950 flex items-center justify-center font-black text-lg">
                  ✓
                </div>
                <div>
                  <div className="font-extrabold text-sm text-white">
                    🎉 ĐÃ ĐIỂM DANH THÀNH CÔNG: {liveSuccessBanner.staffName} ({liveSuccessBanner.staffId})
                  </div>
                  <div className="text-[11px] text-emerald-300 font-medium">
                    {liveSuccessBanner.type === 'check_out' ? 'Tan ca làm việc' : 'Vào ca làm việc'} • Xác thực người thật 100% (Tự động ghi nhận)
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* UNIFORM LIVE STATUS PILL (In Uniform Tab) */}
          {isCameraActive && activeTab === 'uniform' && uniformResult && (
            <div className="absolute bottom-3 inset-x-3 flex justify-center pointer-events-none z-10">
              <div className={`px-4 py-1.5 rounded-full backdrop-blur-md border text-xs font-bold uppercase shadow-lg flex items-center gap-2 ${
                uniformResult.is_correct
                  ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500 shadow-emerald-500/20'
                  : 'bg-rose-950/90 text-rose-300 border-rose-500 shadow-rose-500/20'
              }`}>
                <span className={`w-2 h-2 rounded-full ${uniformResult.is_correct ? 'bg-emerald-400' : 'bg-rose-400'} animate-ping`} />
                <span>
                  {uniformResult.is_correct 
                    ? `✅ ĐẠT CHUẨN ĐỒNG PHỤC (Khẩu trang + Áo ${uniformResult.shirt_color} + Quần ${uniformResult.pants_color})`
                    : uniformResult.mask && !uniformResult.mask.has_mask
                    ? '❌ VI PHẠM: CHƯA ĐEO KHẨU TRANG BẢO HỘ (BẮT BUỘC)'
                    : `❌ VI PHẠM: ${uniformResult.message || 'Không đúng quy định'}`}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* TAB 1 CONTENT: ATTENDANCE CONTROLS */}
      {activeTab === 'attendance' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Check Type Selector */}
          <div className="bg-fb-bg/70 p-3 rounded-xl border border-fb-divider space-y-2">
            <label className="text-[11px] font-bold text-fb-muted uppercase tracking-wider block">
              Loại Chấm Công (Bấm Vào Lúc Nào Cũng Được)
            </label>
            <div className="grid grid-cols-2 gap-1.5">
              <button
                onClick={() => setCheckType('check_in')}
                className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                  checkType === 'check_in'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Vào Ca</span>
              </button>

              <button
                onClick={() => setCheckType('check_out')}
                className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                  checkType === 'check_out'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Tan Ca</span>
              </button>
            </div>
          </div>

          {/* Quick Staff Selection & Manual Trigger */}
          <div className="bg-fb-bg/70 p-3 rounded-xl border border-fb-divider space-y-2">
            <label className="text-[11px] font-bold text-fb-muted uppercase tracking-wider block">
              Chấm Công Thủ Công (Dự Phòng)
            </label>
            <div className="flex gap-2">
              <select
                value={selectedStaffId}
                onChange={(e) => setSelectedStaffId(e.target.value)}
                className="flex-1 bg-white border border-slate-200 text-slate-800 text-xs rounded-lg px-2.5 py-2 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
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
                className="px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs rounded-lg shadow-sm transition shrink-0 flex items-center gap-1 disabled:opacity-50"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Ghi Nhận</span>
              </button>
            </div>
          </div>

          {/* Live Headcount */}
          <div className="bg-gradient-to-br from-cyan-50 to-teal-50 p-3 rounded-xl border border-cyan-200 flex flex-col justify-between">
            <span className="text-[11px] font-bold text-cyan-900 uppercase tracking-wider block">
              Nhân Lực Đang Trực
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-2xl font-black text-cyan-800">
                {activeStaffIds.size} <span className="text-xs font-normal text-cyan-700">/ {staffList.length} người</span>
              </span>
              <span className="text-[11px] text-cyan-600 font-medium">
                Chuồng: <strong>{penName}</strong>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2 CONTENT: LIVE UNIFORM INSPECTION CONTROLS & TELEMETRY */}
      {activeTab === 'uniform' && (
        <div className="space-y-4">
          {/* Uniform Rule Selector */}
          <div className="bg-slate-900 text-slate-100 p-3.5 rounded-xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Shirt className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-cyan-300">
                Quy Định Đồng Phục:
              </span>
            </div>

            <div className="flex-1 max-w-md flex items-center gap-2">
              <select
                value={uniformRuleWeekday}
                onChange={(e) => setUniformRuleWeekday(parseInt(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 font-medium focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                <option value="-1">⭐ Trang phục bảo hộ chuẩn: Áo xanh dương + Quần tối + BẮT BUỘC KHẨU TRANG</option>
                <option value="1">Thứ 3: Áo trắng + Quần tối màu</option>
                <option value="2">Thứ 4: Áo trắng + Quần tối màu</option>
                <option value="3">Thứ 5: Áo trắng + Quần tối màu</option>
                <option value="4">Thứ 6: Áo Đoàn thanh niên (Xanh)</option>
                <option value="0">Thứ 2: Trang phục Dân tộc</option>
              </select>

              <input
                ref={uniformFileInputRef}
                type="file"
                accept="image/*"
                onChange={handleUniformFileUpload}
                className="hidden"
              />
              <button
                onClick={() => uniformFileInputRef.current?.click()}
                className="py-1.5 px-3 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition flex items-center gap-1 shrink-0"
                title="Tải ảnh toàn thân từ máy"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Tải Ảnh Lên</span>
              </button>
            </div>
          </div>

          {/* Real-time Uniform Telemetry Cards (4 Cards: Mask + Shirt + Pants + Overall) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
            {/* 1. Mask Card (BẮT BUỘC) */}
            <div className={`p-3 rounded-xl border shadow-sm flex items-center justify-between transition ${
              uniformResult?.mask?.has_mask
                ? 'bg-emerald-50/70 border-emerald-200'
                : 'bg-rose-50/70 border-rose-200'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-base ${
                  uniformResult?.mask?.has_mask ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                }`}>
                  😷
                </div>
                <div>
                  <span className="font-bold text-slate-800 block text-xs">Khẩu Trang Y Tế</span>
                  <span className="text-[10px] text-slate-500">Yêu cầu bắt buộc</span>
                </div>
              </div>
              <div className="text-right">
                <span className={`font-bold text-[10px] uppercase px-2 py-0.5 rounded-full ${
                  uniformResult?.mask?.has_mask
                    ? 'bg-emerald-600 text-white'
                    : 'bg-rose-600 text-white'
                }`}>
                  {uniformResult?.mask?.has_mask 
                    ? (uniformResult.mask.mask_color === 'blue' ? 'ĐÃ ĐEO (XANH)' : 'ĐÃ ĐEO') 
                    : 'CHƯA ĐEO'}
                </span>
                <span className="text-[9px] text-slate-400 block mt-0.5">
                  Tin cậy: {Math.round((uniformResult?.mask?.confidence || 0) * 100)}%
                </span>
              </div>
            </div>

            {/* 2. Shirt Card */}
            <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-base">
                  👔
                </div>
                <div>
                  <span className="font-bold text-slate-800 block text-xs">Áo Xanh Dương</span>
                  <span className="text-[10px] text-slate-500">Đúng quy định bảo hộ</span>
                </div>
              </div>
              <div className="text-right">
                <span className={`font-bold text-[10px] uppercase px-2 py-0.5 rounded ${
                  uniformResult?.shirt_color === 'blue'
                    ? 'bg-cyan-100 text-cyan-800 border border-cyan-300'
                    : 'bg-slate-100 text-slate-700'
                }`}>
                  {uniformResult?.shirt_color || 'Chờ quét...'}
                </span>
                <span className="text-[9px] text-slate-400 block mt-0.5">
                  Tỷ lệ: {intPercent(uniformResult?.shirt_ratio)}%
                </span>
              </div>
            </div>

            {/* 3. Pants Card */}
            <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-base">
                  👖
                </div>
                <div>
                  <span className="font-bold text-slate-800 block text-xs">Quần Tối Màu</span>
                  <span className="text-[10px] text-slate-500">Đen / Xanh đen</span>
                </div>
              </div>
              <div className="text-right">
                <span className={`font-bold text-[10px] uppercase px-2 py-0.5 rounded ${
                  uniformResult?.pants_color === 'dark'
                    ? 'bg-amber-100 text-amber-800 border border-amber-300'
                    : 'bg-slate-100 text-slate-700'
                }`}>
                  {uniformResult?.pants_color || 'Chờ quét...'}
                </span>
                <span className="text-[9px] text-slate-400 block mt-0.5">
                  Tỷ lệ: {intPercent(uniformResult?.pants_ratio)}%
                </span>
              </div>
            </div>

            {/* 4. Overall Status Card */}
            <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 text-xs">Kết Luận Trực Tiếp</span>
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                  uniformResult?.is_correct 
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                }`}>
                  {uniformResult ? (uniformResult.is_correct ? 'ĐẠT CHUẨN' : 'VI PHẠM') : 'CHỜ DỮ LIỆU'}
                </span>
              </div>
              <p className="text-[10px] text-slate-600 line-clamp-2 mt-1">
                {uniformResult?.message || 'Bật máy ảnh để quét tự động'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* RECENT ATTENDANCE LOGS TABLE (Shared) */}
      <div className="space-y-2 pt-2 border-t border-fb-divider">
        <div className="flex items-center justify-between text-xs text-fb-muted">
          <span className="font-bold uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-600" />
            Nhật Ký Chấm Công Gần Nhất (24/7)
          </span>
          <span>{attendanceLogs.length} bản ghi</span>
        </div>

        {attendanceLogs.length === 0 ? (
          <div className="text-center py-6 text-xs text-fb-muted border border-dashed border-fb-divider rounded-xl">
            Chưa có lượt chấm công nào được ghi nhận. Hãy bật máy ảnh để nhận diện tự động!
          </div>
        ) : (
          <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1 text-xs">
            {attendanceLogs.map((log, idx) => {
              const isCheckOut = log.check_type === 'check_out';
              const createdDate = new Date(log.created_at || Date.now());
              const timeStr = createdDate.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const dateStr = createdDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });

              return (
                <div 
                  key={log.id || idx}
                  className="flex items-center justify-between p-2 rounded-xl bg-fb-bg/60 border border-fb-divider hover:bg-fb-hover transition"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${isCheckOut ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-fb-text truncate">{log.staff_name}</span>
                        <span className="text-[10px] text-fb-muted">({log.staff_id})</span>
                      </div>
                      <span className="text-[10px] text-fb-muted block truncate">
                        {log.note || 'Chấm công tự do'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 text-right">
                    <span 
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                        isCheckOut 
                          ? 'bg-rose-100 text-rose-800' 
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {isCheckOut ? 'Tan Ca' : 'Vào Ca'}
                    </span>
                    <div className="text-[10px] font-mono text-fb-muted">
                      <div>{timeStr}</div>
                      <div className="text-[9px] text-slate-400">{dateStr}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* MODAL: ĐĂNG KÝ KHUÔN MẶT FACEID MỚI */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden text-slate-800 animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-5 py-4 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-700 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                  <UserPlus className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h4 className="font-bold text-sm">Đăng Ký Khuôn Mặt Nhân Viên Mới</h4>
                  <p className="text-[11px] text-emerald-100">Lưu dữ liệu nhận diện vào hệ thống nhân sự</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  setIsEnrollModalOpen(false);
                  setEnrollModalMsg(null);
                  setEnrollPreviewUrl(null);
                  setEnrollFile(null);
                }}
                className="p-1 rounded-lg hover:bg-white/20 text-white/80 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleEnrollSubmit} className="p-5 space-y-4">
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
                    className="w-full text-xs font-semibold px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none uppercase"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Họ và Tên *</label>
                  <input
                    type="text"
                    required
                    value={enrollStaffName}
                    onChange={(e) => setEnrollStaffName(e.target.value)}
                    placeholder="VD: Nguyễn Văn C"
                    className="w-full text-xs font-semibold px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Chức Vụ</label>
                  <select
                    value={enrollRole}
                    onChange={(e) => setEnrollRole(e.target.value)}
                    className="w-full text-xs font-medium px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none bg-white"
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
                    className="w-full text-xs font-medium px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Face Photo Section */}
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1.5">Ảnh Chân Dung Khuôn Mặt (Chính diện, rõ nét) *</label>
                
                <input
                  ref={enrollFileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleEnrollFileChange}
                  className="hidden"
                />

                <div className="flex flex-col sm:flex-row items-center gap-3 p-3 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                  {/* Preview avatar */}
                  <div className="w-24 h-24 rounded-xl border border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden shrink-0 shadow-inner">
                    {enrollPreviewUrl ? (
                      <img src={enrollPreviewUrl} alt="Face preview" className="w-full h-full object-cover" />
                    ) : (
                      <Users className="w-8 h-8 text-slate-400" />
                    )}
                  </div>

                  {/* Buttons */}
                  <div className="space-y-2 flex-1 w-full">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => enrollFileInputRef.current?.click()}
                        className="flex-1 py-2 px-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs transition flex items-center justify-center gap-1.5 shadow-sm"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        <span>Chọn Ảnh Từ Máy</span>
                      </button>

                      {isCameraActive && cameraMode === 'webcam' && (
                        <button
                          type="button"
                          onClick={handleCaptureEnrollFromWebcam}
                          className="flex-1 py-2 px-3 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs transition flex items-center justify-center gap-1.5 shadow-sm"
                        >
                          <Camera className="w-3.5 h-3.5" />
                          <span>📸 Chụp Từ Máy Ảnh</span>
                        </button>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 leading-relaxed">
                      💡 Mẹo: Chụp khuôn mặt rõ nét, chính diện để hệ thống phân tích đặc trưng nhận diện chính xác nhất.
                    </p>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEnrollModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isEnrolling || !enrollStaffId || !enrollStaffName || !enrollFile}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
                >
                  {isEnrolling ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Đang trích xuất nhận diện...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Lưu & Kích Hoạt Nhận Diện</span>
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

function intPercent(val: any): number {
  const n = parseFloat(val);
  if (isNaN(n)) return 0;
  return Math.round(n * 100);
}
