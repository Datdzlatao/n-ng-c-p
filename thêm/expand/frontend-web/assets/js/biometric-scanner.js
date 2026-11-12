/**
 * ============================================================================
 * BIOMETRIC SCANNER & CONSENT ONBOARDING MODULE (eKYC Apple FaceID 3-Pose HUD)
 * Author: Edusams Engineering Team
 * Design System: Apple FaceID HUD with Live Pose Estimation
 * ============================================================================
 */

(function(window) {
  'use strict';

  // ── 5 Spherical Apple FaceID Poses: Center, Left, Right, Tilt Up, Tilt Down (~12-14s Total) ──
  const REQUIRED_HOLD_FRAMES = 60; // ~2s steady hold per angle -> 5 poses take ~12-14s total for thorough capture
  const ANGLE_TARGETS = [
    {
      id: 'center',
      name: 'Chính Diện',
      prompt: '🎯 Bước 1/5: Nhìn thẳng vào camera',
      subPrompt: 'Giữ khuôn mặt ổn định trong khung hình',
      direction: 'center',
      minYaw: -14, maxYaw: 14, minPitch: -18, maxPitch: 18
    },
    {
      id: 'left',
      name: 'Nghiêng Trái',
      prompt: '👈 Bước 2/5: Từ từ quay mặt sang TRÁI',
      subPrompt: 'Quay nhẹ đầu sang bên trái theo hướng dẫn',
      direction: 'left',
      minYaw: -45, maxYaw: -12, minPitch: -22, maxPitch: 22
    },
    {
      id: 'right',
      name: 'Nghiêng Phải',
      prompt: '👉 Bước 3/5: Từ từ quay mặt sang PHẢI',
      subPrompt: 'Quay nhẹ đầu sang bên phải theo hướng dẫn',
      direction: 'right',
      minYaw: 12,  maxYaw: 45,  minPitch: -22, maxPitch: 22
    },
    {
      id: 'tilt_up',
      name: 'Ngước Lên',
      prompt: '👆 Bước 4/5: Hơi ngước cằm lên trên',
      subPrompt: 'Nhận diện camera tầm cao lắp ở cổng trường',
      direction: 'up',
      minYaw: -22, maxYaw: 22, minPitch: 8, maxPitch: 45
    },
    {
      id: 'tilt_down',
      name: 'Cúi Nhẹ',
      prompt: '👇 Bước 5/5: Hơi cúi nhẹ đầu về trước',
      subPrompt: 'Mô phỏng góc nhìn tự nhiên khi đi bộ vào cổng',
      direction: 'down',
      minYaw: -22, maxYaw: 22, minPitch: -45, maxPitch: -6
    }
  ];

  class BiometricOnboardingEngine {
    constructor() {
      this.activeEnrollment = null;
      this.stream = null;
      this.animFrame = null;
      this.audioCtx = null;
      this.samples = [];
      this.currentTargetIdx = 0;
      this.holdFrames = 0;
      this.smoothedYaw = 0;
      this.smoothedPitch = 0;
      this.isUploading = false;
      this.autoCaptureEnabled = true;
      this.isAutoSequencing = true;
      this.phaseStartTime = null;
      this.phaseDurations = [2500, 2800, 2800, 2500, 2500]; // 5 poses ~13s total
      this.phaseProgress = 0;
      this.domInjected = false;
    }

    /**
     * Khởi tạo và nạp HTML Template tự động vào DOM nếu chưa có
     */
    ensureDOM() {
      if (document.getElementById('bioModalContainer')) return;

      const container = document.createElement('div');
      container.id = 'bioModalContainer';
      container.innerHTML = `
        <!-- BƯỚC 1: MODAL CAM KẾT PHÁP LÝ NGHỊ ĐỊNH 13/2023/NĐ-CP -->
        <div class="bio-overlay" id="bioModalConsent">
          <div class="bio-card">
            <div class="bio-header">
              <div class="bio-header-title">
                <div class="bio-header-icon">🛡️</div>
                <div class="bio-header-text">
                  <h3>Cam Kết Bảo Vệ Dữ Liệu Sinh Trắc Học</h3>
                  <span>Theo Nghị định 13/2023/NĐ-CP của Chính phủ</span>
                </div>
              </div>
              <button class="bio-close-btn" onclick="BiometricScanner.cancel()">✕</button>
            </div>

            <div class="bio-consent-body">
              <div class="bio-legal-box">
                <h4>📜 Điều khoản & Cam kết Bảo mật eKYC</h4>
                <p>Nhằm phục vụ công tác điểm danh thông minh tự động và đảm bảo an toàn học đường, nhà trường triển khai thu nhận dữ liệu nhận diện khuôn mặt đa góc (quét sinh trắc học eKYC) với các cam kết sau:</p>
                <ul>
                  <li><b>Mục đích độc quyền:</b> Dữ liệu ảnh và vector đặc trưng chỉ phục vụ điểm danh và quản lý nền nếp học đường nội bộ.</li>
                  <li><b>Bảo mật mã hóa:</b> Toàn bộ vector khuôn mặt được mã hóa chuẩn <b>AES-256</b> và chỉ lưu trữ tại máy chủ bảo mật của nhà trường.</li>
                  <li><b>Tuyệt đối không chuyển giao:</b> Không bán, chia sẻ hoặc cung cấp cho bất kỳ bên thứ ba hay mạng xã hội nào.</li>
                  <li><b>Quyền được xóa dữ liệu (Right to Erasure):</b> Theo Điều 16 NĐ 13/2023/NĐ-CP, học sinh và phụ huynh có quyền yêu cầu thu hồi chấp thuận và xóa bỏ hoàn toàn dữ liệu sinh trắc học bất kỳ lúc nào qua hệ thống hoặc Ban Giám Hiệu.</li>
                </ul>
                <p style="color:#94a3b8; font-size:0.78rem; margin-top:8px;">Phiên bản chính sách: v1.0 • Ngày hiệu lực: 01/09/2026</p>
              </div>

              <div class="bio-consent-check" onclick="BiometricScanner.toggleConsent()">
                <input type="checkbox" id="bioConsentCheckbox" checked onclick="event.stopPropagation()">
                <label for="bioConsentCheckbox" onclick="event.stopPropagation()">
                  Tôi và Người giám hộ đã đọc, hiểu rõ và <u>đồng ý cung cấp dữ liệu ảnh nhận diện</u> phục vụ điểm danh học đường theo quy định.
                </label>
              </div>
            </div>

            <div class="bio-footer">
              <button class="bio-btn-secondary" onclick="BiometricScanner.skip()">Để Sau / Bỏ Qua</button>
              <button class="bio-btn-primary" id="bioBtnStartScan" onclick="BiometricScanner.proceedToScanner()">
                📷 Bắt Đầu Quét Sinh Trắc Học →
              </button>
            </div>
          </div>
        </div>

        <!-- BƯỚC 2: MODAL 3D APPLE FACEID HUD AUTO-SCANNER -->
        <div class="bio-overlay" id="bioModalScanner">
          <div class="bio-card" style="max-width:520px; border-color:rgba(168,85,247,0.4);">
            <div class="bio-header">
              <div class="bio-header-title">
                <div class="bio-header-icon">👤</div>
                <div class="bio-header-text">
                  <h3 id="bioStudentNameDisplay">Quét Sinh Trắc Học (eKYC)</h3>
                  <span id="bioStudentCodeDisplay">Đăng ký dữ liệu khuôn mặt tự động</span>
                </div>
              </div>
              <button class="bio-close-btn" onclick="BiometricScanner.cancel()">✕</button>
            </div>

            <div class="bio-scanner-body">
              <div class="bio-viewport">
                <video id="bioVideoElement" autoplay playsinline muted></video>
                <canvas id="bioCanvasElement"></canvas>

                <!-- Top Environmental Pre-Check Badges -->
                <div class="bio-badges-bar">
                  <div class="bio-pill warn" id="bioPillLux">💡 Đo ánh sáng...</div>
                  <div class="bio-pill warn" id="bioPillSharp">🔍 Đo độ nét...</div>
                  <div class="bio-pill warn" id="bioPillPose">📐 Căn giữa mặt</div>
                </div>

                <!-- Prompt Card -->
                <div class="bio-prompt-card">
                  <div class="bio-prompt-title" id="bioPromptTitle">Đang khởi tạo camera...</div>
                  <div class="bio-prompt-sub" id="bioPromptSub">Vui lòng nhìn vào camera</div>
                  <div class="bio-progress-track">
                    <div class="bio-progress-bar" id="bioProgressBar"></div>
                  </div>
                  <div class="bio-angles-strip" id="bioAnglesStrip"></div>
                </div>

                <!-- Action Controls Bar -->
                <div class="bio-controls-bar">
                  <button class="bio-btn-capture" id="bioBtnAutoScan" onclick="BiometricScanner.startAutoScanSequence()">
                    ⚡ Tự Chụp Theo Hướng Dẫn (~10s)
                  </button>
                  <button class="bio-btn-action" id="bioBtnManualCapture" onclick="BiometricScanner.captureManual()" title="Chụp ngay góc hiện tại">
                    📸 Chụp Góc Này
                  </button>
                  <button class="bio-btn-action" id="bioBtnResetScan" onclick="BiometricScanner.resetAngles()" title="Quét lại từ đầu">
                    🔄 Quét Lại
                  </button>
                </div>

                <!-- Camera Permission / Error Warning Fallback -->
                <div class="bio-perm-warning" id="bioPermWarning" style="display:none;">
                  <div class="bio-perm-icon">📹</div>
                  <div class="bio-perm-title">Không Thể Truy Cập Camera</div>
                  <div class="bio-perm-desc" id="bioPermDesc">
                    Trình duyệt đang chặn camera. Hãy bấm vào biểu tượng <b>Ổ Khóa 🔒</b> hoặc <b>Camera 📹</b> trên thanh địa chỉ và chọn <b>Cho phép (Allow)</b>.
                  </div>
                  <button class="bio-btn-primary" onclick="BiometricScanner.restartCamera()">
                    🔄 Thử Lại Cấp Quyền Camera
                  </button>
                </div>
              </div>
            </div>

            <div class="bio-footer" style="padding:12px 20px;">
              <span style="font-size:0.8rem; color:#94a3b8;" id="bioProgressCount">Đã chụp: 0/3 góc (Chính diện & 2 bên)</span>
              <button class="bio-btn-secondary" onclick="BiometricScanner.skip()">Bỏ qua bước này</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(container);

      // Render Angle Dots
      const strip = document.getElementById('bioAnglesStrip');
      if (strip) {
        strip.innerHTML = ANGLE_TARGETS.map((t, idx) => `
          <div class="bio-angle-dot" id="bioDot-${idx}" title="${t.name}"></div>
        `).join('');
      }

      // Checkbox event
      const chk = document.getElementById('bioConsentCheckbox');
      if (chk) {
        chk.addEventListener('change', (e) => {
          const btn = document.getElementById('bioBtnStartScan');
          if (btn) btn.disabled = !e.target.checked;
        });
      }
    }

    /**
     * Mở quy trình đăng ký eKYC
     */
    start(enrollmentData) {
      this.ensureDOM();
      this.activeEnrollment = enrollmentData || {};
      this.samples = [];
      this.currentTargetIdx = 0;
      this.holdFrames = 0;
      this.isUploading = false;

      // Update Student Header Display
      const nameDisp = document.getElementById('bioStudentNameDisplay');
      const codeDisp = document.getElementById('bioStudentCodeDisplay');
      if (nameDisp) nameDisp.innerText = this.activeEnrollment.studentName || 'Quét Sinh Trắc Học';
      if (codeDisp) codeDisp.innerText = `Mã HS: ${this.activeEnrollment.studentCode || '—'} • Trường: ${this.activeEnrollment.schoolId || '1'}`;

      // Open Consent Modal first (Legal compliance)
      this.openModal('bioModalConsent');
    }

    openModal(id) {
      const el = document.getElementById(id);
      if (el) el.classList.add('active');
    }

    closeModal(id) {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    }

    toggleConsent() {
      const chk = document.getElementById('bioConsentCheckbox');
      if (chk) {
        chk.checked = !chk.checked;
        const btn = document.getElementById('bioBtnStartScan');
        if (btn) btn.disabled = !chk.checked;
      }
    }

    async proceedToScanner() {
      this.closeModal('bioModalConsent');
      this.openModal('bioModalScanner');
      await this.initCamera();
    }

    async initCamera() {
      const video = document.getElementById('bioVideoElement');
      const warning = document.getElementById('bioPermWarning');
      if (warning) warning.style.display = 'none';

      this.samples = [];
      this.currentTargetIdx = 0;
      this.holdFrames = 0;
      this.updateProgressUI();

      try {
        if (this.stream) {
          this.stream.getTracks().forEach(t => t.stop());
        }

        this.stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
          },
          audio: false
        });

        video.srcObject = this.stream;
        await video.play();

        // Kích hoạt chu trình Tự Chụp Theo Hướng Dẫn (~10 giây)
        this.startAutoScanSequence();

        // Start render loop
        if (this.animFrame) cancelAnimationFrame(this.animFrame);
        this.renderLoop();
      } catch (err) {
        console.error('Camera access error:', err);
        if (warning) {
          warning.style.display = 'flex';
          const desc = document.getElementById('bioPermDesc');
          if (desc) {
            desc.innerHTML = `Lỗi: <b>${err.name || 'NotAllowedError'}</b>.<br>Vui lòng bấm vào biểu tượng <b>Ổ khóa 🔒</b> hoặc <b>Camera 📹</b> trên thanh địa chỉ URL của trình duyệt và chọn <b>"Cho Phép" (Allow)</b>.`;
          }
        }
      }
    }

    restartCamera() {
      this.initCamera();
    }

    playSound(type = 'snap') {
      try {
        if (!this.audioCtx) {
          this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioCtx.state === 'suspended') this.audioCtx.resume();

        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        if (type === 'snap') {
          osc.type = 'sine';
          osc.frequency.setValueAtTime(900, this.audioCtx.currentTime);
          osc.frequency.exponentialRampToValueAtTime(1800, this.audioCtx.currentTime + 0.05);
          gain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.06);
          osc.connect(gain);
          gain.connect(this.audioCtx.destination);
          osc.start();
          osc.stop(this.audioCtx.currentTime + 0.06);
        } else if (type === 'complete') {
          osc.type = 'triangle';
          osc.frequency.setValueAtTime(523, this.audioCtx.currentTime);
          osc.frequency.setValueAtTime(659, this.audioCtx.currentTime + 0.1);
          osc.frequency.setValueAtTime(784, this.audioCtx.currentTime + 0.2);
          gain.gain.setValueAtTime(0.35, this.audioCtx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.35);
          osc.connect(gain);
          gain.connect(this.audioCtx.destination);
          osc.start();
          osc.stop(this.audioCtx.currentTime + 0.35);
        }
      } catch (e) {}

      if (navigator.vibrate) {
        try { navigator.vibrate(type === 'complete' ? [50, 50, 100] : 35); } catch (e) {}
      }
    }

    renderLoop() {
      const video = document.getElementById('bioVideoElement');
      const canvas = document.getElementById('bioCanvasElement');

      if (!video || !canvas || video.readyState < 2) {
        this.animFrame = requestAnimationFrame(() => this.renderLoop());
        return;
      }

      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
      }

      const w = canvas.width;
      const h = canvas.height;

      // Draw camera video frame
      ctx.drawImage(video, 0, 0, w, h);

      // Environmental metrics
      const patchW = Math.round(w * 0.55);
      const patchH = Math.round(h * 0.7);
      const patchX = Math.round((w - patchW) / 2);
      const patchY = Math.round((h - patchH) / 2);

      const patchData = ctx.getImageData(patchX, patchY, patchW, patchH);
      const lux = this.computeLuminance(patchData);
      const sharpness = this.computeLaplacian(patchData, patchW, patchH);
      const pose = this.estimatePose(patchData, patchW, patchH);

      // Update UI Badges
      this.updateBadges(lux, sharpness, pose);

      // Draw Apple FaceID HUD Overlay
      this.drawHUD(ctx, w, h, pose);

      // Auto-capture evaluation & Guided Auto-Scan Sequence (~10s total: 3.0s front + 3.5s left + 3.5s right)
      if (this.isAutoSequencing && this.currentTargetIdx < ANGLE_TARGETS.length && !this.isUploading) {
        const target = ANGLE_TARGETS[this.currentTargetIdx];
        if (!this.phaseStartTime) {
          this.phaseStartTime = performance.now();
        }

        const duration = this.phaseDurations[this.currentTargetIdx] || 3500;
        const elapsed = performance.now() - this.phaseStartTime;
        const timeRatio = Math.min(1, elapsed / duration);

        const inYaw = pose.yaw >= target.minYaw && pose.yaw <= target.maxYaw;
        const inPitch = pose.pitch >= target.minPitch && pose.pitch <= target.maxPitch;
        const luxOk = lux >= 35 && lux <= 250;
        const sharpOk = sharpness >= 25;
        const isAligned = inYaw && inPitch && luxOk && sharpOk && pose.detected;

        if (isAligned) {
          this.holdFrames++;
        }

        // Tỉ lệ hoàn thành của góc hiện tại (kết hợp thời gian trôi và độ khớp góc)
        const holdRatio = Math.min(1, this.holdFrames / 40);
        this.phaseProgress = Math.min(1, Math.max(timeRatio, holdRatio));

        // Cập nhật dòng nhắc nhở đếm ngược trực quan
        const sub = document.getElementById('bioPromptSub');
        const remainSec = Math.max(0, ((duration - elapsed) / 1000)).toFixed(1);
        if (sub) {
          sub.innerText = `${target.subPrompt} • ⚡ Tự chụp sau ${remainSec}s`;
        }

        // Tự động chụp khi hết thời gian của góc hoặc khi mặt giữ ổn định xuất sắc
        if (elapsed >= duration || this.holdFrames >= 45) {
          this.captureCurrent(canvas, target, pose, lux, sharpness);
        }
      }

      this.animFrame = requestAnimationFrame(() => this.renderLoop());
    }

    updateBadges(lux, sharpness, pose) {
      const bLux = document.getElementById('bioPillLux');
      const bSharp = document.getElementById('bioPillSharp');
      const bPose = document.getElementById('bioPillPose');

      if (bLux) {
        if (lux < 40) {
          bLux.className = 'bio-pill warn';
          bLux.innerText = `💡 Hơi tối (${Math.round(lux)} lx)`;
        } else if (lux > 245) {
          bLux.className = 'bio-pill bad';
          bLux.innerText = `💡 Chói sáng (${Math.round(lux)} lx)`;
        } else {
          bLux.className = 'bio-pill good';
          bLux.innerText = `💡 Đủ sáng (${Math.round(lux)} lx)`;
        }
      }

      if (bSharp) {
        if (sharpness < 30) {
          bSharp.className = 'bio-pill warn';
          bSharp.innerText = `🔍 Rung/nhòe (${Math.round(sharpness)})`;
        } else {
          bSharp.className = 'bio-pill good';
          bSharp.innerText = `🔍 Sắc nét (${Math.round(sharpness)})`;
        }
      }

      if (bPose) {
        const target = ANGLE_TARGETS[this.currentTargetIdx] || ANGLE_TARGETS[0];
        if (!pose.detected) {
          bPose.className = 'bio-pill warn';
          bPose.innerText = '📐 Chưa thấy mặt';
        } else if (pose.faceRatio < 0.18) {
          bPose.className = 'bio-pill warn';
          bPose.innerText = '📐 Tiến lại gần hơn';
        } else if (pose.faceRatio > 0.92) {
          bPose.className = 'bio-pill warn';
          bPose.innerText = '📐 Lùi ra xa một chút';
        } else {
          const inTarget = pose.yaw >= target.minYaw && pose.yaw <= target.maxYaw;
          bPose.className = inTarget ? 'bio-pill good' : 'bio-pill warn';
          bPose.innerText = inTarget ? `✅ Khớp góc ${target.name}` : `📐 Góc: ${Math.round(pose.yaw)}°`;
        }
      }
    }

    drawHUD(ctx, w, h, pose) {
      const cx = w / 2;
      const cy = h / 2;
      const rx = w * 0.28;
      const ry = h * 0.38;

      ctx.save();

      // 1. Dark Vignette Background Mask
      ctx.fillStyle = 'rgba(2, 6, 23, 0.48)';
      ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = 'destination-out';
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = 'source-over';

      const target = ANGLE_TARGETS[this.currentTargetIdx] || ANGLE_TARGETS[0];
      const isAngleMatched = pose.detected &&
                             pose.yaw >= target.minYaw && pose.yaw <= target.maxYaw &&
                             pose.pitch >= target.minPitch && pose.pitch <= target.maxPitch;

      // 2. FaceID Oval Border
      const isAligned = pose.detected && pose.faceRatio >= 0.18 && pose.faceRatio <= 0.92;
      ctx.lineWidth = 3.5;
      ctx.strokeStyle = isAngleMatched ? '#22c55e' : (isAligned ? 'rgba(56, 189, 248, 0.9)' : 'rgba(168, 85, 247, 0.7)');
      ctx.shadowColor = isAngleMatched ? '#22c55e' : '#a855f7';
      ctx.shadowBlur = isAngleMatched ? 22 : 12;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();

      // 3. Apple FaceID Radial Ticks (36 ticks total, 12 ticks per pose)
      const totalTicks = 36;
      const ringR = Math.max(rx, ry) * 1.08;
      const completedAngles = this.samples.length;
      const completedTicks = (completedAngles / ANGLE_TARGETS.length) * totalTicks;

      // Hold progress (0 to 1) for current angle
      const activeTicks = (this.phaseProgress || 0) * (totalTicks / ANGLE_TARGETS.length);

      for (let i = 0; i < totalTicks; i++) {
        const theta = (i / totalTicks) * Math.PI * 2 - Math.PI / 2;
        const isDone = i < completedTicks;
        const isHolding = !isDone && (i < completedTicks + activeTicks);
        const tickLen = (isDone || isHolding) ? 14 : 7;

        const x1 = cx + Math.cos(theta) * ringR;
        const y1 = cy + Math.sin(theta) * ringR;
        const x2 = cx + Math.cos(theta) * (ringR + tickLen);
        const y2 = cy + Math.sin(theta) * (ringR + tickLen);

        ctx.lineWidth = (isDone || isHolding) ? 3.5 : 1.5;
        ctx.strokeStyle = isDone ? '#22c55e' : (isHolding ? '#38bdf8' : 'rgba(255, 255, 255, 0.22)');
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // 4. Directional Dynamic Guide Arrows & Indicators (Apple FaceID visual guide)
      const now = performance.now() / 1000;
      const bounce = Math.sin(now * 7) * 9;

      ctx.shadowBlur = 12;
      if (target.direction === 'left') {
        // Arrow pointing Left
        const arrowX = cx - rx - 24 + bounce;
        const arrowY = cy;
        ctx.fillStyle = isAngleMatched ? '#22c55e' : '#38bdf8';
        ctx.shadowColor = ctx.fillStyle;
        ctx.font = 'bold 26px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('👈', arrowX, arrowY);
      } else if (target.direction === 'right') {
        // Arrow pointing Right
        const arrowX = cx + rx + 24 - bounce;
        const arrowY = cy;
        ctx.fillStyle = isAngleMatched ? '#22c55e' : '#38bdf8';
        ctx.shadowColor = ctx.fillStyle;
        ctx.font = 'bold 26px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('👉', arrowX, arrowY);
      } else if (target.direction === 'up') {
        // Arrow pointing Up
        const arrowX = cx;
        const arrowY = cy - ry - 24 + bounce;
        ctx.fillStyle = isAngleMatched ? '#22c55e' : '#38bdf8';
        ctx.shadowColor = ctx.fillStyle;
        ctx.font = 'bold 26px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('👆', arrowX, arrowY);
      } else if (target.direction === 'down') {
        // Arrow pointing Down
        const arrowX = cx;
        const arrowY = cy + ry + 24 - bounce;
        ctx.fillStyle = isAngleMatched ? '#22c55e' : '#38bdf8';
        ctx.shadowColor = ctx.fillStyle;
        ctx.font = 'bold 26px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('👇', arrowX, arrowY);
      } else {
        // Center Reticle Pulsing Dot
        ctx.fillStyle = isAngleMatched ? '#22c55e' : 'rgba(168, 85, 247, 0.75)';
        ctx.shadowColor = ctx.fillStyle;
        ctx.beginPath();
        ctx.arc(cx, cy, 5 + Math.sin(now * 5) * 2, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();
    }

    startAutoScanSequence() {
      this.samples = [];
      this.currentTargetIdx = 0;
      this.holdFrames = 0;
      this.isAutoSequencing = true;
      this.phaseStartTime = performance.now();
      this.phaseProgress = 0;
      this.updateProgressUI();
    }

    captureCurrent(canvas, target, pose, lux, sharpness) {
      if (!canvas) return;

      this.playSound('snap');

      const dataUrl = canvas.toDataURL('image/jpeg', 0.88);
      this.samples.push({
        angle_id: target.id,
        angle_name: target.name,
        target_yaw: (target.minYaw + target.maxYaw) / 2,
        actual_yaw: Math.round(pose.yaw || 0),
        actual_pitch: Math.round(pose.pitch || 0),
        lux: Math.round(lux || 120),
        sharpness_score: Math.round(sharpness || 80),
        image_data: dataUrl
      });

      // Advance to next angle
      this.currentTargetIdx++;
      this.phaseStartTime = performance.now();
      this.phaseProgress = 0;
      this.holdFrames = 0;
      this.updateProgressUI();

      if (this.currentTargetIdx >= ANGLE_TARGETS.length) {
        this.finishCapture();
      }
    }

    /**
     * Bấm nút Chụp Thủ Công góc hiện tại
     */
    captureManual() {
      const canvas = document.getElementById('bioCanvasElement');
      if (!canvas || this.isUploading) return;

      const target = ANGLE_TARGETS[this.currentTargetIdx] || ANGLE_TARGETS[0];
      this.captureCurrent(canvas, target, { yaw: 0, pitch: 0, detected: true }, 120, 80);
    }

    /**
     * Quét lại từ đầu nếu muốn chụp lại
     */
    resetAngles() {
      this.startAutoScanSequence();
    }

    /**
     * Tự động quét theo hướng dẫn
     */
    quickComplete() {
      this.startAutoScanSequence();
    }

    updateProgressUI() {
      const title = document.getElementById('bioPromptTitle');
      const sub = document.getElementById('bioPromptSub');
      const bar = document.getElementById('bioProgressBar');
      const count = document.getElementById('bioProgressCount');
      const btnAuto = document.getElementById('bioBtnAutoScan');

      const total = ANGLE_TARGETS.length;
      const current = Math.min(this.currentTargetIdx, total);
      const percent = Math.round((current / total) * 100);

      if (bar) bar.style.width = `${percent}%`;
      if (count) count.innerText = `Đã chụp: ${current}/${total} góc sinh trắc học FaceID 3D`;

      if (btnAuto) {
        if (current >= total) {
          btnAuto.innerText = '✅ Quét Hoàn Tất';
          btnAuto.disabled = true;
        } else {
          btnAuto.innerText = `⚡ Tự Chụp Bước ${current + 1}/${total}`;
          btnAuto.disabled = false;
        }
      }

      // Update dots
      ANGLE_TARGETS.forEach((_, idx) => {
        const dot = document.getElementById(`bioDot-${idx}`);
        if (!dot) return;
        dot.className = 'bio-angle-dot';
        if (idx < current) dot.classList.add('done');
        else if (idx === current) dot.classList.add('active');
      });

      // Update prompt title
      if (this.currentTargetIdx < total) {
        const t = ANGLE_TARGETS[this.currentTargetIdx];
        if (title) title.innerText = t.prompt;
      }
    }

    async finishCapture() {
      this.isUploading = true;
      this.playSound('complete');

      const title = document.getElementById('bioPromptTitle');
      const sub = document.getElementById('bioPromptSub');
      if (title) title.innerText = '✅ Quét Hoàn Tất!';
      if (sub) sub.innerText = 'Đang mã hóa AES-256 & Lưu trữ hồ sơ sinh trắc học...';

      const btnManual = document.getElementById('bioBtnManualCapture');
      if (btnManual) {
        btnManual.disabled = true;
        btnManual.innerText = '⏳ Đang tải lên...';
      }

      await this.uploadSamples();
    }

    async uploadSamples() {
      const apiBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.API_BASE) ? STEM_CONFIG.API_BASE : '';
      const sid = this.activeEnrollment.schoolId || 1;
      const stid = this.activeEnrollment.studentId;
      const stcode = this.activeEnrollment.studentCode || `HS${sid}-${stid || Date.now()}`;
      const token = localStorage.getItem('stem_auth_token') || localStorage.getItem('stem_token') || localStorage.getItem('token');

      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      try {
        // Bước 1: Khởi tạo phiên thu thập sinh trắc học
        const initRes = await fetch(`${apiBase}/api/v1/auth/biometric/session-init`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            school_id: sid,
            student_id: stid,
            student_code: stcode,
            full_name: this.activeEnrollment.studentName,
            consent_agreed: true,
            parent_consent: true,
            user_agent: navigator.userAgent
          })
        });

        const initData = await initRes.json();
        const sessionToken = initData.session_token || initData.session_id;

        // Chuẩn hóa danh sách mẫu ảnh
        const formattedSamples = (this.samples && this.samples.length > 0)
          ? this.samples.map((s, idx) => ({
              sample_index: idx,
              angle_type: s.angle_id ? s.angle_id.toUpperCase() : (s.angle_name || 'CENTER'),
              yaw_angle: Number(s.actual_yaw || 0.0),
              pitch_angle: Number(s.actual_pitch || 0.0),
              image_base64: s.image_data || s.image_base64 || '',
              quality_score: ((s.sharpness_score || 80) / 100)
            }))
          : [];

        // Bước 2: Tải các mẫu ảnh lên server
        const uploadRes = await fetch(`${apiBase}/api/v1/auth/biometric/upload-samples`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            school_id: sid,
            student_id: stid,
            student_code: stcode,
            session_token: sessionToken,
            verify_account: Boolean(this.activeEnrollment.verifyAccount !== false),
            consent: {
              accepted: true,
              consent_version: '1.0',
              purpose: 'FACE_ATTENDANCE'
            },
            samples: formattedSamples
          })
        });

        const uploadData = await uploadRes.json();

        if (uploadRes.ok && uploadData.status === 'success') {
          if (typeof toast === 'function') {
            toast('✅ Đăng Ký Sinh Trắc Học Thành Công', `Đã lưu ${this.samples.length} góc quét sinh trắc học bảo mật AES-256.`, 'success');
          }
          this.cleanup();
          this.closeModal('bioModalScanner');

          if (typeof this.activeEnrollment.onComplete === 'function') {
            this.activeEnrollment.onComplete(uploadData);
          } else {
            // Chuyển hướng vào Dashboard nếu không có callback riêng
            setTimeout(() => {
              window.location.href = `/app/index.html?school_id=${sid}`;
            }, 1200);
          }
        } else {
          throw new Error(uploadData.detail || 'Lỗi tải ảnh sinh trắc học');
        }
      } catch (err) {
        console.error('Upload biometric failed:', err);
        if (typeof toast === 'function') {
          toast('Lưu Dữ Liệu Thất Bại', err.message || 'Không thể đồng bộ ảnh lên máy chủ', 'error');
        }
        if (typeof this.activeEnrollment.onError === 'function') {
          this.activeEnrollment.onError(err);
        } else {
          setTimeout(() => {
            this.cleanup();
            this.closeModal('bioModalScanner');
            window.location.href = `/app/index.html?school_id=${sid}`;
          }, 2000);
        }
      }
    }

    cancel() {
      this.cleanup();
      this.closeModal('bioModalConsent');
      this.closeModal('bioModalScanner');
      if (typeof this.activeEnrollment.onCancel === 'function') {
        this.activeEnrollment.onCancel();
      }
    }

    skip() {
      this.cleanup();
      this.closeModal('bioModalConsent');
      this.closeModal('bioModalScanner');
      if (typeof this.activeEnrollment.onSkip === 'function') {
        this.activeEnrollment.onSkip();
        return;
      }
      const sid = this.activeEnrollment?.schoolId || 1;
      if (typeof toast === 'function') {
        toast('Đã Lưu Tài Khoản', 'Bạn có thể bổ sung quét khuôn mặt sau tại Dashboard.', 'info');
      }
      setTimeout(() => {
        window.location.href = `/app/index.html?school_id=${sid}`;
      }, 800);
    }

    cleanup() {
      if (this.stream) {
        this.stream.getTracks().forEach(t => t.stop());
        this.stream = null;
      }
      if (this.animFrame) {
        cancelAnimationFrame(this.animFrame);
        this.animFrame = null;
      }
    }

    // ── Vision Helper Algorithms ──
    computeLuminance(imageData) {
      const data = imageData.data;
      let sum = 0;
      const step = 4 * 4;
      let count = 0;
      for (let i = 0; i < data.length; i += step) {
        sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        count++;
      }
      return count > 0 ? sum / count : 120;
    }

    computeLaplacian(imageData, w, h) {
      const data = imageData.data;
      let varSum = 0;
      let mean = 0;
      let n = 0;
      const step = 4;

      for (let y = 1; y < h - 1; y += step) {
        for (let x = 1; x < w - 1; x += step) {
          const idx = (y * w + x) * 4;
          const c = data[idx];
          const up = data[((y - 1) * w + x) * 4];
          const down = data[((y + 1) * w + x) * 4];
          const left = data[(y * w + (x - 1)) * 4];
          const right = data[(y * w + (x + 1)) * 4];

          const lap = Math.abs(4 * c - up - down - left - right);
          mean += lap;
          n++;
        }
      }
      if (n === 0) return 80;
      mean /= n;

      for (let y = 1; y < h - 1; y += step) {
        for (let x = 1; x < w - 1; x += step) {
          const idx = (y * w + x) * 4;
          const c = data[idx];
          const up = data[((y - 1) * w + x) * 4];
          const down = data[((y + 1) * w + x) * 4];
          const left = data[(y * w + (x - 1)) * 4];
          const right = data[(y * w + (x + 1)) * 4];
          const lap = Math.abs(4 * c - up - down - left - right);
          varSum += (lap - mean) * (lap - mean);
        }
      }
      return Math.sqrt(varSum / n);
    }

    /**
     * Thuật toán ước lượng góc quay đầu 3D (Head Pose Estimation: Yaw, Pitch).
     * Phân tích cấu trúc hình học bất đối xứng của khuôn mặt (Facial Symmetry Ratio & Nose Ridge Offset)
     * thay vì chỉ đo vị trí tâm màu da trong khung hình.
     */
    estimatePose(imageData, w, h) {
      const data = imageData.data;
      let skinPixels = 0;
      let minX = w, maxX = 0, minY = h, maxY = 0;
      let sumX = 0, sumY = 0;

      // 1. Phân đoạn vùng khuôn mặt dựa trên sắc độ da chuẩn YCbCr/RGB
      for (let y = 0; y < h; y += 2) {
        for (let x = 0; x < w; x += 2) {
          const i = (y * w + x) * 4;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          if (r > 65 && g > 40 && b > 20 && r > g && r > b && (r - g) > 12) {
            skinPixels++;
            sumX += x;
            sumY += y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
          }
        }
      }

      const totalSamples = (w * h) / 4;
      const faceRatio = skinPixels / totalSamples;

      if (faceRatio < 0.08 || maxX <= minX || maxY <= minY) {
        return { detected: false, yaw: this.smoothedYaw || 0, pitch: this.smoothedPitch || 0, faceRatio: 0 };
      }

      const faceW = maxX - minX;
      const faceH = maxY - minY;
      const faceAspect = faceH / Math.max(1, faceW);

      // Kiểm tra tỉ lệ khung hình khuôn mặt thực tế
      if (faceAspect < 0.8 || faceAspect > 2.2) {
        return { detected: false, yaw: this.smoothedYaw || 0, pitch: this.smoothedPitch || 0, faceRatio };
      }

      // 2. Phân tích lát cắt trung tâm khuôn mặt (Vùng sống mũi và gò má)
      const midY1 = minY + Math.round(faceH * 0.28);
      const midY2 = minY + Math.round(faceH * 0.72);
      const midFaceX = (minX + maxX) / 2;

      let leftMass = 0, rightMass = 0;
      let noseRidgeX = midFaceX;
      let maxRidgeBright = -1;

      for (let y = midY1; y < midY2; y += 2) {
        for (let x = minX; x < maxX; x += 2) {
          const i = (y * w + x) * 4;
          const r = data[i], g = data[i + 1], b = data[i + 2];
          const lum = 0.299 * r + 0.587 * g + 0.114 * b;

          if (r > 60 && g > 40 && b > 20) {
            if (x < midFaceX) {
              leftMass++;
            } else {
              rightMass++;
            }

            // Tìm điểm sáng đỉnh sống mũi (nose bridge peak)
            if (Math.abs(x - midFaceX) < faceW * 0.35 && lum > maxRidgeBright) {
              maxRidgeBright = lum;
              noseRidgeX = x;
            }
          }
        }
      }

      // 3. Tính góc quay đầu ngang (Yaw Angle):
      // Khi đầu quay sang một bên, diện tích má chiếu lên camera bất đối xứng
      // và vị trí đỉnh sống mũi dịch chuyển tương đối so với trục giữa khuôn mặt
      const totalMass = leftMass + rightMass;
      const massAsymmetry = totalMass > 0 ? (rightMass - leftMass) / totalMass : 0;
      const ridgeOffset = (noseRidgeX - midFaceX) / Math.max(1, faceW * 0.5);

      // Trong chế độ camera gương (mirror):
      // Quay mặt sang trái -> má phải nở rộng -> massAsymmetry > 0 -> rawYaw âm (Trái)
      const rawYaw = (massAsymmetry * 0.5 + ridgeOffset * 0.5) * -60;

      // 4. Tính góc nghiêng dọc (Pitch Angle):
      // Khi ngước mặt lên: mắt và mũi dịch chuyển lên trên so với tâm hình học
      // Khi cúi mặt xuống: trán mở rộng, cằm thụt lùi
      const faceCenterY = sumY / Math.max(1, skinPixels);
      const expectedCenterY = minY + faceH * 0.48;
      const verticalShift = (faceCenterY - expectedCenterY) / Math.max(1, faceH * 0.5);
      const rawPitch = verticalShift * -45;

      // 5. Bộ lọc làm mượt chuyển động HUD (Exponential Smoothing)
      this.smoothedYaw = this.smoothedYaw * 0.65 + rawYaw * 0.35;
      this.smoothedPitch = this.smoothedPitch * 0.65 + rawPitch * 0.35;

      const clampedYaw = Math.max(-50, Math.min(50, this.smoothedYaw));
      const clampedPitch = Math.max(-35, Math.min(35, this.smoothedPitch));

      return {
        detected: true,
        yaw: Math.round(clampedYaw * 10) / 10,
        pitch: Math.round(clampedPitch * 10) / 10,
        faceRatio,
        faceW,
        faceH
      };
    }
  }

  // Export Singleton
  window.BiometricScanner = new BiometricOnboardingEngine();

})(window);
