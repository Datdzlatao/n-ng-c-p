// app/js/views/cameras.js — Camera Wall, RTSP/WebRTC Streams & Edge AI Config
// ── Cameras (Webcam / RTSP / Edge Config) ─────────
let activeEdgeConfigSnippet = '';
let currentLoadedCameras = [];
let currentCamViewMode = 'grid';
let currentCamCols = 2;
let currentCamSearchKw = '';

if (!window._camDropdownListenerAttached) {
  document.addEventListener('click', closeAllCamDropdowns);
  window._camDropdownListenerAttached = true;
}

function updateCameraKpiStats(rows) {
  const total = rows ? rows.length : 0;
  const online = rows ? rows.filter(c => c.status === 'ONLINE').length : 0;
  
  const elTotal = document.getElementById('camKpiTotal');
  const elOnline = document.getElementById('camKpiOnline');
  const elLive = document.getElementById('camKpiLive');

  if (elTotal) elTotal.innerText = `${total} Trạm`;
  if (elOnline) elOnline.innerText = `${online} Online`;
  if (elLive) elLive.innerText = total > 0 ? `${total} Sẵn Sàng` : '0 Luồng';
}

function filterCamerasGrid(keyword) {
  currentCamSearchKw = (keyword || '').toLowerCase().trim();
  if (!currentLoadedCameras) return;
  if (!currentCamSearchKw) {
    renderCamerasGrid(currentLoadedCameras);
    return;
  }
  const filtered = currentLoadedCameras.filter(c => {
    const name = (c.name || '').toLowerCase();
    const loc = (c.location || '').toLowerCase();
    const type = (c.stream_type || '').toLowerCase();
    const url = String(c.stream_url || '').toLowerCase();
    return name.includes(currentCamSearchKw) || loc.includes(currentCamSearchKw) || type.includes(currentCamSearchKw) || url.includes(currentCamSearchKw);
  });
  renderCamerasGrid(filtered);
}

function toggleCamDropdown(event, camId) {
  event.stopPropagation();
  const dropdown = document.getElementById(`camDropdown_${camId}`);
  const btn = document.getElementById(`camMoreBtn_${camId}`);
  if (!dropdown) return;
  const isShown = dropdown.style.display === 'block';
  closeAllCamDropdowns();
  if (!isShown) {
    dropdown.style.display = 'block';
    if (btn) btn.classList.add('active');
  }
}

function closeAllCamDropdowns() {
  document.querySelectorAll('.cam-dropdown-menu').forEach(m => m.style.display = 'none');
  document.querySelectorAll('.cam-more-btn').forEach(b => b.classList.remove('active'));
}

function toggleSingleCamFullscreen(camId) {
  const viewport = document.getElementById(`camViewport_${camId}`);
  if (!viewport) return;
  if (!document.fullscreenElement) {
    if (viewport.requestFullscreen) {
      viewport.requestFullscreen().catch(() => {
        toast('Toàn màn hình', 'Trình duyệt không cho phép phóng to ô này', 'warning');
      });
    }
  } else {
    document.exitFullscreen();
  }
}

function setCamViewMode(mode) {
  currentCamViewMode = mode;
  const btnList = document.getElementById('btnCamListView');
  const btnGrid = document.getElementById('btnCamGridView');
  const tableWrap = document.getElementById('camTableViewWrap');
  const gridWrap = document.getElementById('camGridViewWrap');

  if (mode === 'grid') {
    if (btnList) btnList.className = 'btn btn-xs btn-outline';
    if (btnGrid) btnGrid.className = 'btn btn-xs btn-primary';
    if (tableWrap) tableWrap.style.display = 'none';
    if (gridWrap) gridWrap.style.display = 'block';
    renderCamerasGrid(currentLoadedCameras);
    if (window.LiveStreamPlayer) LiveStreamPlayer.resumeGrid();
  } else {
    if (btnList) btnList.className = 'btn btn-xs btn-primary';
    if (btnGrid) btnGrid.className = 'btn btn-xs btn-outline';
    if (tableWrap) tableWrap.style.display = 'block';
    if (gridWrap) gridWrap.style.display = 'none';
    if (window.LiveStreamPlayer) LiveStreamPlayer.pauseGrid();
  }
}

function setCamGridLayout(num) {
  currentCamCols = num;
  try { localStorage.setItem('stem_cam_cols', num); } catch(e){}
  [1, 2, 3, 4].forEach(n => {
    const btn = document.getElementById(`btnLayout${n}`);
    if (btn) {
      btn.className = (n === num) ? 'btn btn-xs btn-primary cam-layout-btn' : 'btn btn-xs btn-outline cam-layout-btn';
    }
  });

  const grid = document.getElementById('camGridContainer');
  if (!grid) return;

  grid.classList.remove('cam-cols-1', 'cam-cols-2', 'cam-cols-3', 'cam-cols-4');
  grid.classList.add(`cam-cols-${num}`);

  if (num === 1) {
    grid.style.gridTemplateColumns = '1fr';
  } else if (num === 2) {
    grid.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
  } else if (num === 3) {
    grid.style.gridTemplateColumns = 'repeat(3, minmax(0, 1fr))';
  } else if (num === 4) {
    grid.style.gridTemplateColumns = 'repeat(4, minmax(0, 1fr))';
  } else {
    grid.style.gridTemplateColumns = `repeat(${num}, minmax(0, 1fr))`;
  }
}

// =============================================================================
// LIVE STREAM PLAYER (WebRTC WHEP H.264 + WebSocket + HTTP MJPEG Fallback)
// =============================================================================
const LiveStreamPlayer = {
  activeStreams: {}, // key: elementId -> streamState

  async start(elementId, camId, isModal = false, streamType = 'ai') {
    this.stop(elementId);
    const img = document.getElementById(elementId);
    if (!img) return;

    const token = localStorage.getItem('stem_auth_token') || '';
    const sId = (typeof schoolId !== 'undefined' && schoolId) ? schoolId : 1;
    const isHttps = (location.protocol === 'https:');
    const wsProto = isHttps ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${location.host}/api/v1/s/${sId}/cameras/${camId}/live-ws?token=${encodeURIComponent(token)}`;
    const httpUrl = `/api/v1/s/${sId}/cameras/${camId}/live-stream?token=${encodeURIComponent(token)}&t=${Date.now()}`;
    const webrtcUrl = `/api/v1/s/${sId}/cameras/${camId}/webrtc?stream_type=${streamType}&token=${encodeURIComponent(token)}`;

    // Tạo hoặc tái sử dụng thẻ <video> dành riêng cho WebRTC
    let video = document.getElementById(`webrtc_${elementId}`);
    if (!video) {
      video = document.createElement('video');
      video.id = `webrtc_${elementId}`;
      video.autoplay = true;
      video.playsInline = true;
      video.muted = true;
      if (isModal) {
        video.style.cssText = 'width:100%;height:auto;max-height:65vh;object-fit:contain;display:none;position:relative;z-index:2;';
      } else {
        video.style.cssText = 'width:100%;height:100%;object-fit:cover;display:none;position:absolute;top:0;left:0;z-index:2;';
      }
      img.parentElement.insertBefore(video, img);
    }

    const streamState = {
      pc: null,
      ws: null,
      img: img,
      video: video,
      camId: camId,
      frameCount: 0,
      fpsTimer: null,
      fallbackTimeout: null,
      usingWebRtc: false,
      usingWs: false,
      isModal: isModal,
      stopped: false,
      rafId: null
    };
    this.activeStreams[elementId] = streamState;

    // 1. ƯU TIÊN SỐ 1: WEBRTC WHEP H.264 (Độ trễ < 0.2s, Băng thông 1-2 Mbps, Chuẩn công nghiệp)
    if (window.RTCPeerConnection) {
      try {
        const pc = new RTCPeerConnection({
          iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
          ]
        });
        streamState.pc = pc;

        pc.addTransceiver('video', { direction: 'recvonly' });

        pc.ontrack = (event) => {
          if (streamState.stopped) return;
          streamState.usingWebRtc = true;
          if (streamState.fallbackTimeout) {
            clearTimeout(streamState.fallbackTimeout);
            streamState.fallbackTimeout = null;
          }
          video.srcObject = event.streams[0];
          video.style.display = 'block';
          img.style.display = 'none';

          if (isModal) {
            const loading = document.getElementById('liveStreamLoading');
            if (loading) loading.style.display = 'none';
          } else {
            onGridStreamSuccess(camId);
          }

          const badgeId = isModal ? 'liveModalFpsBadge' : `gridFpsBadge_${camId}`;
          const badge = document.getElementById(badgeId);
          if (badge) {
            badge.style.display = 'inline-flex';
            badge.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg><span>30 FPS</span><span style="background:#10b981;color:#000;padding:1px 5px;border-radius:4px;font-size:0.62rem;font-weight:800;margin-left:2px;">WebRTC</span>`;
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Timeout 3.5s nếu đàm phán WebRTC bị gián đoạn thì tự động sang WebSocket/MJPEG
        streamState.fallbackTimeout = setTimeout(() => {
          if (!streamState.stopped && !streamState.usingWebRtc) {
            console.warn(`[LiveStreamPlayer] WebRTC timeout trạm #${camId}, chuyển sang WebSocket fallback`);
            this._startWsFallback(streamState, wsUrl, httpUrl);
          }
        }, 3500);

        const res = await fetch(webrtcUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: offer.sdp
        });

        if (res.ok) {
          const answerSdp = await res.text();
          if (!streamState.stopped && pc.signalingState !== 'closed') {
            await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
          }
          return;
        } else {
          console.warn(`[LiveStreamPlayer] WebRTC signaling status ${res.status}, chuyển sang fallback`);
          this._startWsFallback(streamState, wsUrl, httpUrl);
        }
      } catch (err) {
        console.warn('[LiveStreamPlayer] WebRTC exception, chuyển sang fallback:', err);
        this._startWsFallback(streamState, wsUrl, httpUrl);
      }
    } else {
      this._startWsFallback(streamState, wsUrl, httpUrl);
    }
  },

  _startWsFallback(streamState, wsUrl, httpUrl) {
    if (streamState.stopped || streamState.usingWebRtc) return;
    if (streamState.pc) {
      try { streamState.pc.close(); } catch(e){}
      streamState.pc = null;
    }
    if (streamState.video) {
      streamState.video.style.display = 'none';
      streamState.video.srcObject = null;
    }

    // 2. DỰ PHÒNG 1: WebSocket Binary Stream
    if (window.WebSocket) {
      try {
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'blob';
        streamState.ws = ws;

        if (streamState.fallbackTimeout) clearTimeout(streamState.fallbackTimeout);
        streamState.fallbackTimeout = setTimeout(() => {
          if (!streamState.stopped && !streamState.usingWs) {
            this._fallbackHttp(streamState, httpUrl);
          }
        }, 3000);

        let pendingBlob = null;
        ws.onmessage = (e) => {
          if (streamState.stopped) return;
          if (typeof e.data === 'string') return;
          streamState.usingWs = true;
          streamState.frameCount++;
          if (streamState.fallbackTimeout) {
            clearTimeout(streamState.fallbackTimeout);
            streamState.fallbackTimeout = null;
          }

          if (!streamState.isModal) {
            pendingBlob = e.data;
            if (!streamState.rafId) {
              streamState.rafId = requestAnimationFrame(() => {
                streamState.rafId = null;
                if (streamState.stopped || !pendingBlob) return;
                const blobUrl = URL.createObjectURL(pendingBlob);
                const oldUrl = streamState.img.src;
                streamState.img.src = blobUrl;
                streamState.img.style.display = 'block';
                onGridStreamSuccess(streamState.camId);
                if (oldUrl && oldUrl.startsWith('blob:')) URL.revokeObjectURL(oldUrl);
              });
            }
          } else {
            const blobUrl = URL.createObjectURL(e.data);
            const oldUrl = streamState.img.src;
            streamState.img.src = blobUrl;
            streamState.img.style.display = 'block';
            const loading = document.getElementById('liveStreamLoading');
            if (loading) loading.style.display = 'none';
            if (oldUrl && oldUrl.startsWith('blob:')) URL.revokeObjectURL(oldUrl);
          }
        };

        ws.onerror = () => this._fallbackHttp(streamState, httpUrl);
        ws.onclose = () => {
          if (!streamState.stopped && !streamState.usingWs) this._fallbackHttp(streamState, httpUrl);
        };

        streamState.fpsTimer = setInterval(() => {
          if (streamState.stopped) return;
          const fps = streamState.frameCount;
          streamState.frameCount = 0;
          const badgeId = streamState.isModal ? 'liveModalFpsBadge' : `gridFpsBadge_${streamState.camId}`;
          const badge = document.getElementById(badgeId);
          if (badge && fps > 0) {
            badge.style.display = 'inline-flex';
            badge.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg><span>${fps} FPS</span><span style="opacity:0.65;font-size:0.62rem;">${streamState.usingWs ? 'WSS' : 'MJPEG'}</span>`;
          }
        }, 1000);
        return;
      } catch (e) {}
    }

    // 3. DỰ PHÒNG CUỐI CÙNG: HTTP MJPEG
    this._fallbackHttp(streamState, httpUrl);
  },

  _fallbackHttp(streamState, httpUrl) {
    if (streamState.stopped) return;
    if (streamState.ws) {
      try { streamState.ws.close(); } catch(e){}
      streamState.ws = null;
    }
    streamState.usingWs = false;
    if (streamState.img) {
      streamState.img.src = httpUrl;
      streamState.img.style.display = 'block';
    }
    const badgeId = streamState.isModal ? 'liveModalFpsBadge' : `gridFpsBadge_${streamState.camId}`;
    const badge = document.getElementById(badgeId);
    if (badge) {
      badge.style.display = 'inline-flex';
      badge.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg><span>MJPEG</span>`;
    }
    if (streamState.isModal) {
      const loading = document.getElementById('liveStreamLoading');
      if (loading) loading.style.display = 'none';
    }
  },

  stop(elementId) {
    const streamState = this.activeStreams[elementId];
    if (!streamState) return;
    streamState.stopped = true;
    if (streamState.rafId) {
      cancelAnimationFrame(streamState.rafId);
      streamState.rafId = null;
    }
    if (streamState.pc) {
      try { streamState.pc.close(); } catch(e){}
      streamState.pc = null;
    }
    if (streamState.ws) {
      try { streamState.ws.close(); } catch(e){}
      streamState.ws = null;
    }
    if (streamState.video) {
      streamState.video.srcObject = null;
      streamState.video.style.display = 'none';
    }
    if (streamState.fpsTimer) {
      clearInterval(streamState.fpsTimer);
      streamState.fpsTimer = null;
    }
    if (streamState.fallbackTimeout) {
      clearTimeout(streamState.fallbackTimeout);
      streamState.fallbackTimeout = null;
    }
    if (streamState.img) {
      const oldUrl = streamState.img.src;
      streamState.img.src = '';
      if (oldUrl && oldUrl.startsWith('blob:')) {
        URL.revokeObjectURL(oldUrl);
      }
    }
    const badgeId = streamState.isModal ? 'liveModalFpsBadge' : `gridFpsBadge_${streamState.camId}`;
    const badge = document.getElementById(badgeId);
    if (badge) badge.style.display = 'none';
    delete this.activeStreams[elementId];
  },

  pauseGrid() {
    Object.keys(this.activeStreams).forEach(id => {
      if (id.startsWith('gridStreamImg_')) {
        this.stop(id);
      }
    });
  },

  resumeGrid() {
    if (!currentLoadedCameras || !currentLoadedCameras.length) return;
    if (typeof currentCamViewMode !== 'undefined' && currentCamViewMode !== 'grid') return;
    currentLoadedCameras.forEach(c => {
      this.start(`gridStreamImg_${c.id}`, c.id, false);
    });
  },

  stopAll() {
    Object.keys(this.activeStreams).forEach(id => {
      this.stop(id);
    });
  }
};
window.LiveStreamPlayer = LiveStreamPlayer;

// Tự động tạm ngắt stream khi tab trình duyệt bị thu nhỏ/ẩn đi để tiết kiệm CPU và mạng
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    LiveStreamPlayer.pauseGrid();
  } else {
    const modal = document.getElementById('modalLiveStream');
    if (!modal || modal.style.display !== 'flex') {
      LiveStreamPlayer.resumeGrid();
    }
  }
});

function renderCamerasGrid(rows) {
  const container = document.getElementById('camGridContainer');
  if (!container) return;

  if (!rows || !rows.length) {
    container.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:56px 20px;background:rgba(17,24,39,0.7);backdrop-filter:blur(16px);border:1px dashed rgba(255,255,255,0.12);border-radius:20px;">
        <div style="width:56px;height:56px;border-radius:16px;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.2);display:inline-flex;align-items:center;justify-content:center;color:var(--blue);margin-bottom:14px;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>
        </div>
        <div style="font-weight:700;color:var(--text);font-size:1.15rem;margin-bottom:6px;font-family:var(--font-heading);">Chưa có trạm camera nào phù hợp</div>
        <div style="font-size:0.84rem;color:var(--muted);margin-bottom:18px;max-width:440px;margin-left:auto;margin-right:auto;line-height:1.5;">
          ${currentCamSearchKw ? 'Không tìm thấy trạm camera nào khớp với từ khóa. Hãy thử tìm kiếm khác.' : 'Bấm "+ Thêm Trạm Camera" để khởi tạo các trạm giám sát AI tại cổng trường hoặc lớp học.'}
        </div>
        ${!currentCamSearchKw ? '<button class="btn btn-primary" onclick="openAddCameraModal()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> <span>+ Thêm Trạm Đầu Tiên</span></button>' : '<button class="btn btn-outline" onclick="document.getElementById(\'camSearchInput\').value=\'\';filterCamerasGrid(\'\');">Xóa Bộ Lọc</button>'}
      </div>`;
    return;
  }

  container.innerHTML = rows.map((c, idx) => {
    const isWebcam = (c.stream_type === 'WEBCAM');
    const isRtsp   = (c.stream_type === 'RTSP');
    const typeLabel = isWebcam ? 'Webcam' : (isRtsp ? 'RTSP' : 'HTTP');
    const typeColor = isWebcam ? '#38bdf8' : (isRtsp ? '#c084fc' : '#f59e0b');

    return `
      <div class="cam-grid-card" id="camGridCard_${c.id}">
        <!-- Top Header Bar with 3-Dot Menu -->
        <div class="cam-card-header" style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:rgba(17,24,39,0.85);border-top-left-radius:20px;border-top-right-radius:20px;border-bottom:1px solid var(--border);">
          <div class="cam-card-header-left" style="display:flex;align-items:center;gap:10px;min-width:0;flex:1;padding-right:8px;overflow:hidden;">
            <!-- Status Pulse Dot -->
            <div class="cam-pulse-dot ${c.status==='ONLINE'?'online':'offline'}" title="${c.status==='ONLINE'?'Trực tuyến':'Ngoại tuyến'}"></div>
            <!-- Name & Location -->
            <div style="min-width:0;overflow:hidden;">
              <div class="cam-card-title" style="font-weight:700;font-size:0.9rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:var(--font-heading);" title="${escHtml(c.name)}">
                #${c.camera_num || (idx+1)}: ${escHtml(c.name)}
              </div>
              <div class="cam-card-loc" style="font-size:0.72rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:4px;">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                <span>${escHtml(c.location || 'Chưa đặt vị trí')}</span>
              </div>
            </div>
          </div>

          <!-- Type badge & 3-Dot Button -->
          <div class="cam-card-header-right" style="display:flex;align-items:center;gap:6px;position:relative;flex-shrink:0;">
            <!-- Nút bật/tắt nhanh nhận diện trang phục 1 chạm -->
            <button class="btn btn-xs cam-btn-uniform" style="${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'background:rgba(192,132,252,0.15);color:var(--purple);border:1px solid rgba(192,132,252,0.35);font-weight:700;' : 'background:rgba(148,163,184,0.1);color:var(--muted);border:1px solid rgba(148,163,184,0.25);font-weight:600;'}" onclick="quickToggleCamUniform(${c.id}, ${(c.uniform_check === 0 || c.uniform_check === false)})" title="${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'Nhận diện trang phục: BẬT. Nhấn để TẮT.' : 'Nhận diện trang phục: TẮT. Nhấn để BẬT.'}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"/></svg>
              <span class="uniform-label">${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'Đ.Phục: BẬT' : 'Đ.Phục: TẮT'}</span>
            </button>
            <span class="chip cam-type-chip" style="font-size:0.68rem;padding:2px 8px;font-weight:700;font-family:var(--font-mono);background:rgba(255,255,255,0.06);color:${typeColor};border:1px solid ${typeColor};">
              ${typeLabel}
            </span>
            
            <!-- DẤU 3 CHẤM DỌC (Settings / Actions Button) -->
            <div style="position:relative;">
              <button class="cam-more-btn" id="camMoreBtn_${c.id}" onclick="toggleCamDropdown(event, ${c.id})" title="Cài đặt & Thao tác cho camera này">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="1.5"></circle>
                  <circle cx="12" cy="5" r="1.5"></circle>
                  <circle cx="12" cy="19" r="1.5"></circle>
                </svg>
              </button>

              <!-- Floating Dropdown Menu -->
              <div class="cam-dropdown-menu" id="camDropdown_${c.id}" onclick="event.stopPropagation()">
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); quickToggleCamUniform(${c.id}, ${(c.uniform_check === 0 || c.uniform_check === false)})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"/></svg>
                  <span>${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'Tắt kiểm tra trang phục' : 'Bật kiểm tra trang phục'}</span>
                </button>
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); openEditCameraModal(${c.id}, '${escHtml(c.name)}', '${escHtml(c.location||'')}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${(c.uniform_check !== 0 && c.uniform_check !== false)})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                  <span>Cài đặt & Sửa RTSP</span>
                </button>
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); openLiveStreamModal('${escHtml(c.name)}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${c.id})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                  <span>Phóng to cận cảnh (Modal)</span>
                </button>
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); showEdgeConfigModal(${c.id})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/></svg>
                  <span>Lấy cấu hình Edge AI (PC/Pi)</span>
                </button>
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); reloadGridStream(${c.id})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
                  <span>Tải lại luồng này</span>
                </button>
                <button class="cam-dropdown-item" onclick="closeAllCamDropdowns(); toggleSingleCamFullscreen(${c.id})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
                  <span>Toàn màn hình ô này</span>
                </button>
                <div class="cam-dropdown-divider"></div>
                <button class="cam-dropdown-item danger" onclick="closeAllCamDropdowns(); deleteCamera(${c.id})">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--red);"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                  <span style="color:var(--red);">Xóa trạm camera</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Video Viewport Frame (Nhấn vào xem cận cảnh tức thì) -->
        <div class="cam-stream-viewport" id="camViewport_${c.id}" onclick="openLiveStreamModal('${escHtml(c.name)}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${c.id})" title="Nhấn để phóng to toàn màn hình camera này">
          <!-- Fallback message (hidden when stream loads) -->
          <div id="gridFallback_${c.id}" style="display:none;position:absolute;inset:0;padding:20px;text-align:center;flex-direction:column;align-items:center;justify-content:center;background:radial-gradient(circle at center, rgba(17,24,39,0.92) 0%, #060a14 100%);z-index:2;">
            <div style="width:48px;height:48px;border-radius:50%;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.25);display:flex;align-items:center;justify-content:center;margin-bottom:8px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--orange);"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19.1"/></svg>
            </div>
            <div style="font-size:0.84rem;font-weight:700;color:var(--orange);margin-bottom:4px;font-family:var(--font-heading);">Chờ luồng video từ Trạm AI</div>
            <div style="font-size:0.72rem;color:var(--muted);max-width:260px;line-height:1.4;margin-bottom:10px;">
              Trạm AI (${escHtml(c.name)}) chưa kết nối hoặc chưa chạy <code>edge/main.py</code>
            </div>
            <button class="btn btn-xs btn-outline" onclick="event.stopPropagation(); reloadGridStream(${c.id})" style="border-color:var(--orange);color:var(--orange);padding:4px 10px;font-size:0.72rem;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
              <span>Thử Kết Nối Lại</span>
            </button>
          </div>

          <!-- Video Stream Image -->
          <img id="gridStreamImg_${c.id}"
               src=""
               alt="${escHtml(c.name)}"
               style="width:100%;height:100%;object-fit:cover;display:none;"
               onerror="onGridStreamError(${c.id}, '${escHtml(c.name)}')" />

          <!-- Overlay: Top-Left LIVE Badge with Radar Beacon -->
          <div class="cam-live-indicator">
            <span class="cam-live-beacon"></span>
            <span class="cam-live-text">TRỰC TIẾP</span>
          </div>

          <!-- Overlay: Top-Right Realtime FPS Badge -->
          <div id="gridFpsBadge_${c.id}" class="cam-telemetry-chip">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>-- FPS</span>
          </div>

          <!-- Overlay: Bottom Gradient Bar with Source Info -->
          <div class="cam-bottom-hud">
            <div style="font-size:0.72rem;color:#f8fafc;font-weight:600;display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${c.status==='ONLINE'?'#10b981':'#f43f5e'};box-shadow:0 0 8px ${c.status==='ONLINE'?'#10b981':'#f43f5e'};"></span>
              <span>${c.status==='ONLINE'?'Sẵn Sàng':'Đang kết nối'}</span>
            </div>
            <div style="font-size:0.68rem;color:#cbd5e1;font-family:var(--font-mono);background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);padding:2px 8px;border-radius:6px;border:1px solid rgba(255,255,255,0.1);max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              ${isWebcam ? 'Webcam #'+(c.stream_url||0) : escHtml(c.stream_url||'RTSP Stream')}
            </div>
          </div>
        </div>

        <!-- Footer Actions Bar -->
        <div class="cam-card-footer" style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:rgba(17,24,39,0.85);border-bottom-left-radius:20px;border-bottom-right-radius:20px;border-top:1px solid var(--border);font-size:0.75rem;gap:8px;">
          <div class="cam-footer-stream-label" style="display:flex;align-items:center;gap:6px;color:var(--muted);overflow:hidden;white-space:nowrap;">
            <span style="font-size:0.7rem;color:var(--muted);">Luồng:</span>
            <span style="font-weight:600;color:var(--text);font-family:var(--font-mono);font-size:0.72rem;overflow:hidden;text-overflow:ellipsis;">${c.status==='ONLINE'?'25-30 FPS (AI Active)':'Chờ tín hiệu'}</span>
          </div>
          <div class="cam-footer-btn-wrap" style="display:flex;gap:6px;flex-shrink:0;">
            <button class="btn btn-xs btn-outline" style="padding:4px 9px;font-size:0.72rem;" onclick="event.stopPropagation(); reloadGridStream(${c.id})" title="Tải lại luồng camera này">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
              <span>Tải lại</span>
            </button>
            <button class="btn btn-xs btn-outline" style="padding:4px 9px;font-size:0.72rem;border-color:rgba(192,132,252,0.4);color:var(--purple);" onclick="event.stopPropagation(); openLiveStreamModal('${escHtml(c.name)}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${c.id})" title="Xem phóng to cận cảnh">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
              <span>Phóng to</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Tự động khởi động luồng phát siêu mượt (WebSocket / MJPEG) cho từng ô camera
  rows.forEach(c => {
    LiveStreamPlayer.start(`gridStreamImg_${c.id}`, c.id, false);
  });
}

window._camRetryTimers = window._camRetryTimers || {};

function onGridStreamError(camId, name) {
  const img = document.getElementById(`gridStreamImg_${camId}`);
  const fallback = document.getElementById(`gridFallback_${camId}`);
  if (img) img.style.display = 'none';
  if (fallback) fallback.style.display = 'flex';

  // Tự động thử kết nối lại sau 3.5s (giúp web tự nạp luồng ngay khi camera vừa khởi động xong)
  if (window._camRetryTimers[camId]) {
    clearTimeout(window._camRetryTimers[camId]);
  }
  window._camRetryTimers[camId] = setTimeout(() => {
    reloadGridStream(camId);
  }, 3500);
}

function onGridStreamSuccess(camId) {
  if (window._camRetryTimers && window._camRetryTimers[camId]) {
    clearTimeout(window._camRetryTimers[camId]);
    delete window._camRetryTimers[camId];
  }
  const img = document.getElementById(`gridStreamImg_${camId}`);
  if (img) img.style.display = 'block';
  const fallback = document.getElementById(`gridFallback_${camId}`);
  if (fallback) fallback.style.display = 'none';
}

function reloadGridStream(camId) {
  if (window._camRetryTimers && window._camRetryTimers[camId]) {
    clearTimeout(window._camRetryTimers[camId]);
    delete window._camRetryTimers[camId];
  }
  const fallback = document.getElementById(`gridFallback_${camId}`);
  if (fallback) fallback.style.display = 'none';
  LiveStreamPlayer.start(`gridStreamImg_${camId}`, camId, false);
}

function refreshAllLiveGridStreams() {
  if (!currentLoadedCameras || !currentLoadedCameras.length) return;
  toast('Đang làm mới', 'Đang kết nối lại tất cả luồng camera...', 'info');
  currentLoadedCameras.forEach(c => {
    reloadGridStream(c.id);
  });
}

function toggleFullscreenCamGrid() {
  const elem = document.getElementById('camGridViewWrap');
  if (!elem) return;
  if (!document.fullscreenElement) {
    elem.requestFullscreen().catch(err => {
      toast('Toàn màn hình', 'Trình duyệt chặn mở toàn màn hình', 'warning');
    });
  } else {
    document.exitFullscreen();
  }
}

async function loadCameras() {
  const tbl = document.getElementById('camBody');
  if (!schoolId) {
    tbl.innerHTML = emptyRow('Chưa chọn trường nào. Bấm nút "🏫 Ngôi Trường Của Tôi" ở trên để tạo trường đầu tiên!', 7);
    return;
  }
  tbl.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted);">Đang tải danh sách camera...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/cameras`);
    currentLoadedCameras = rows || [];
    updateCameraKpiStats(currentLoadedCameras);
    renderCamerasGrid(currentLoadedCameras);
    const savedCols = parseInt(localStorage.getItem('stem_cam_cols') || '0', 10);
    setCamGridLayout(savedCols || 2);
    if (!rows.length) { tbl.innerHTML = emptyRow('Chưa có trạm camera nào trong trường này. Bấm "+ Thêm Trạm Camera" để tạo.', 7); return; }
    tbl.innerHTML = rows.map(c => {
      const isWebcam = (c.stream_type === 'WEBCAM');
      const isRtsp   = (c.stream_type === 'RTSP');
      const typeBadge = isWebcam
        ? '<span class="chip chip-blue">💻 Webcam Laptop</span>'
        : isRtsp
        ? '<span class="chip chip-purple">📹 RTSP Stream</span>'
        : '<span class="chip chip-orange">📱 HTTP Cam</span>';
      
      let streamDisplay = isWebcam ? `Index: <b>${escHtml(c.stream_url||0)}</b>` : `<code style="font-size:0.75rem;color:var(--blue);word-break:break-all;">${escHtml(c.stream_url||'—')}</code>`;
      if (c.public_stream_url) {
        streamDisplay += `<div style="margin-top:4px;display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
          <a href="${escHtml(c.public_stream_url)}" target="_blank" class="chip chip-purple" style="text-decoration:none;font-size:0.68rem;padding:2px 6px;cursor:pointer;" title="Mở luồng phát HTTPS trực tiếp qua Tailscale">🌐 HTTPS Live</a>
          <button class="btn btn-xs" style="padding:1px 5px;font-size:0.65rem;" onclick="copyStreamUrl('${escHtml(c.public_stream_url)}')" title="Sao chép link HTTPS">📋 Copy</button>
        </div>`;
      } else if (isRtsp) {
        streamDisplay += `<div style="margin-top:4px;">
          <button class="btn btn-xs btn-outline" style="border-color:var(--purple);color:var(--purple);font-size:0.68rem;padding:2px 6px;" onclick="quickPublishCameraTailscale(${c.id})" title="Kích hoạt luồng HTTPS công khai qua Tailscale">🌐 Xuất Bản HTTPS</button>
        </div>`;
      }

      return `
      <tr>
        <td><b>#${c.camera_num || c.id}</b></td>
        <td><strong>${escHtml(c.name)}</strong><br>${typeBadge}</td>
        <td>${streamDisplay}</td>
        <td>${escHtml(c.location||'—')}</td>
        <td>${c.status==='ONLINE'?'<span class="chip chip-green">🟢 ONLINE</span>':'<span class="chip chip-muted">⚫ OFFLINE</span>'}</td>
        <td>
          <button class="btn btn-xs" style="${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'background:rgba(168,85,247,0.15);color:var(--purple);border:1px solid rgba(168,85,247,0.35);font-weight:700;' : 'background:rgba(107,114,128,0.12);color:var(--muted);border:1px solid rgba(107,114,128,0.25);font-weight:600;'}" onclick="quickToggleCamUniform(${c.id}, ${(c.uniform_check === 0 || c.uniform_check === false)})" title="${(c.uniform_check !== 0 && c.uniform_check !== false) ? '👗 Nhận diện trang phục: ĐANG BẬT. Nhấn để TẮT.' : '👗 Nhận diện trang phục: ĐANG TẮT. Nhấn để BẬT.'}">
            👗 ${(c.uniform_check !== 0 && c.uniform_check !== false) ? 'BẬT' : 'TẮT'}
          </button>
        </td>
        <td style="white-space:nowrap;">
          <button class="btn btn-outline" style="padding:4px 8px;font-size:0.75rem;border-color:var(--blue);color:var(--blue);margin-right:4px;" onclick="openEditCameraModal(${c.id}, '${escHtml(c.name)}', '${escHtml(c.location||'')}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${(c.uniform_check !== 0 && c.uniform_check !== false)}, '${escHtml(c.public_stream_url||'')}')">
            ✏️ Sửa RTSP
          </button>
          <button class="btn btn-outline" style="padding:4px 8px;font-size:0.75rem;border-color:var(--green);color:var(--green);margin-right:4px;" onclick="openLiveStreamModal('${escHtml(c.name)}', '${c.stream_type}', '${escHtml(c.stream_url||'')}', ${c.id}, '${escHtml(c.public_stream_url||'')}')">
            👁️ Xem Live
          </button>
          <button class="btn btn-outline" style="padding:4px 8px;font-size:0.75rem;border-color:var(--purple);color:var(--purple);margin-right:4px;" onclick="showEdgeConfigModal(${c.id})">
            📋 Config
          </button>
          <button class="btn btn-danger" style="padding:4px 8px;font-size:0.72rem;" onclick="deleteCamera(${c.id})">Xóa</button>
        </td>
      </tr>`;
    }).join('');
  } catch(e) { tbl.innerHTML = errorRow(e, 7); }
}

function openEditCameraModal(id, name, location, streamType, streamUrl, uniformCheck, publicStreamUrl) {
  document.getElementById('editCamId').value = id;
  document.getElementById('editCamName').value = name;
  document.getElementById('editCamLocation').value = location;
  document.getElementById('editCamStreamType').value = streamType || 'WEBCAM';
  document.getElementById('editCamStreamUrl').value = streamUrl || '';
  const ucEl = document.getElementById('editCamUniformCheck');
  if (ucEl) ucEl.checked = (uniformCheck !== false && uniformCheck !== 0);

  const diag = document.getElementById('editCamDiagBox');
  if (diag) { diag.style.display = 'none'; diag.innerHTML = ''; }
  const disc = document.getElementById('editCamDiscoveredBox');
  if (disc) { disc.style.display = 'none'; disc.innerHTML = ''; }

  const pubInp = document.getElementById('editCamPublicUrl');
  if (pubInp) pubInp.value = publicStreamUrl || '';
  const tsNotice = document.getElementById('editCamTsNotice');
  if (tsNotice) tsNotice.style.display = 'none';

  onEditCamTypeChange(streamType || 'WEBCAM');
  checkEditCamTailscaleStatus(id, publicStreamUrl);
  openModal('modalEditCamera');
}

function onEditCamTypeChange(type) {
  const lbl = document.getElementById('editCamUrlLabel');
  const hint = document.getElementById('editCamUrlHint');
  const inp = document.getElementById('editCamStreamUrl');
  const tools = document.getElementById('rtspQuickTools');
  const tsCard = document.getElementById('editCamTailscaleCard');
  if (tools) tools.style.display = (type === 'RTSP') ? 'flex' : 'none';
  if (tsCard) tsCard.style.display = (type === 'RTSP') ? 'block' : 'none';

  if (type === 'WEBCAM') {
    lbl.innerText = 'Chỉ số Camera (Index) *';
    hint.innerText = '0 = Webcam tích hợp sẵn trên Laptop / PC hoặc Camera USB';
    if (!inp.value || inp.value.startsWith('rtsp')) inp.value = '0';
  } else if (type === 'RTSP') {
    lbl.innerText = 'Đường Dẫn Luồng RTSP *';
    hint.innerText = 'Ví dụ: rtsp://admin:password@192.168.1.50:554/Streaming/Channels/101';
    if (!inp.value || inp.value === '0') inp.value = 'rtsp://admin:123456@192.168.1.50:554/Streaming/Channels/101';
  } else {
    lbl.innerText = 'Đường Dẫn HTTP / MJPEG *';
    hint.innerText = 'Ví dụ: http://192.168.1.38:4747/video (DroidCam/IP Webcam)';
  }
}

async function testEditCamConnection() {
  const camId = document.getElementById('editCamId').value;
  const streamUrl = document.getElementById('editCamStreamUrl').value.trim();
  const diag = document.getElementById('editCamDiagBox');
  if (!diag) return;
  diag.style.display = 'block';
  diag.style.background = 'rgba(59,130,246,0.1)';
  diag.style.color = 'var(--blue)';
  diag.style.border = '1px solid rgba(59,130,246,0.2)';
  diag.innerHTML = '⏳ Đang kiểm tra kết nối tới Camera RTSP...';

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${camId}/test-connection`, { stream_url: streamUrl });
    if (res.status === 'success') {
      diag.style.background = 'rgba(16,185,129,0.1)';
      diag.style.color = 'var(--green)';
      diag.style.border = '1px solid rgba(16,185,129,0.25)';
      diag.innerHTML = `
        <div style="font-weight:700;margin-bottom:2px;">${res.message}</div>
        <div style="font-size:0.7rem;color:var(--muted);">${res.suggestion || ''}</div>
      `;
    } else {
      const isMismatch = (res.error_type === 'SUBNET_MISMATCH');
      diag.style.background = isMismatch ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.1)';
      diag.style.color = isMismatch ? 'var(--red)' : 'var(--orange)';
      diag.style.border = isMismatch ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(245,158,11,0.3)';
      diag.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">${res.message}</div>
        <div style="font-size:0.72rem;color:var(--text);margin-bottom:6px;">${res.suggestion || ''}</div>
        ${isMismatch ? `<button type="button" class="btn btn-xs btn-primary" onclick="autoFixEditCamIp()" style="font-size:0.72rem;padding:3px 8px;">🔄 Tự Động Sửa IP Ngay</button>` : ''}
      `;
    }
  } catch(e) {
    diag.style.background = 'rgba(239,68,68,0.1)';
    diag.style.color = 'var(--red)';
    diag.style.border = '1px solid rgba(239,68,68,0.2)';
    diag.innerHTML = `❌ Lỗi kiểm tra: ${e.detail || e.message}`;
  }
}

async function discoverLanCamsForEdit() {
  const disc = document.getElementById('editCamDiscoveredBox');
  if (!disc) return;
  disc.style.display = 'block';
  disc.innerHTML = '🔍 Đang quét toàn bộ mạng LAN tìm Camera IP (1-2s)...';

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/discover`);
    const cams = res.cameras || [];
    if (!cams.length) {
      disc.innerHTML = `
        <div style="color:var(--orange);font-weight:600;">⚠️ Không tìm thấy Camera RTSP nào trong mạng LAN hiện tại (${res.local_network?.subnet_prefix||'192.168.1'}.x).</div>
        <div style="color:var(--muted);font-size:0.7rem;margin-top:2px;">Hãy chắc chắn Camera đã cắm nguồn và kết nối cùng WiFi với máy chủ.</div>
      `;
      return;
    }
    disc.innerHTML = `
      <div style="font-weight:700;color:var(--green);margin-bottom:6px;">🎉 Đã tìm thấy ${cams.length} Camera RTSP trong mạng:</div>
      ${cams.map(c => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:var(--card);border:1px solid var(--border);border-radius:6px;margin-bottom:4px;">
          <div>
            <b>${c.brand}</b> &bull; IP: <code style="color:var(--blue);">${c.ip}:${c.port}</code>
            ${c.mac ? `<span style="color:var(--muted);font-size:0.7rem;">(MAC: ${c.mac})</span>` : ''}
          </div>
          <button type="button" class="btn btn-xs btn-outline" style="padding:2px 8px;font-size:0.7rem;color:var(--green);border-color:var(--green);" onclick="applyDiscoveredCamIp('${c.ip}')">
            + Dùng IP này
          </button>
        </div>
      `).join('')}
    `;
  } catch(e) {
    disc.innerHTML = `<span style="color:var(--red);">Lỗi quét mạng: ${e.detail || e.message}</span>`;
  }
}

function applyDiscoveredCamIp(newIp) {
  const inp = document.getElementById('editCamStreamUrl');
  let val = inp.value.trim();
  if (val.startsWith('rtsp://')) {
    inp.value = val.replace(/@([0-9a-zA-Z.-]+):/, `@${newIp}:`);
  } else {
    inp.value = `rtsp://admin:matkhau@${newIp}:554/Streaming/Channels/101`;
  }
  toast('Đã cập nhật', `Đã điền IP mới ${newIp} vào ô cấu hình. Nhớ kiểm tra mật khẩu rồi bấm Lưu!`, 'success');
  testEditCamConnection();
}

async function autoFixEditCamIp() {
  const camId = document.getElementById('editCamId').value;
  const diag = document.getElementById('editCamDiagBox');
  if (diag) {
    diag.style.display = 'block';
    diag.style.background = 'rgba(59,130,246,0.1)';
    diag.style.color = 'var(--blue)';
    diag.innerHTML = '🔄 Đang tự động quét mạng và cập nhật IP mới cho Camera...';
  }
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${camId}/auto-fix-ip`);
    document.getElementById('editCamStreamUrl').value = res.new_url;
    toast('Thành công', res.message, 'success');
    if (diag) {
      diag.style.background = 'rgba(16,185,129,0.1)';
      diag.style.color = 'var(--green)';
      diag.innerHTML = `✅ ${res.message}<br><small style="color:var(--muted)">URL mới: ${res.new_url}</small>`;
    }
    loadCameras();
  } catch(e) {
    toast('Không thể tự sửa IP', e.detail || e.message, 'error');
    if (diag) {
      diag.style.background = 'rgba(239,68,68,0.1)';
      diag.style.color = 'var(--red)';
      diag.innerHTML = `❌ ${e.detail || e.message}`;
    }
  }
}

async function doSaveEditCamera() {
  const camId = document.getElementById('editCamId').value;
  const name = document.getElementById('editCamName').value.trim();
  const location = document.getElementById('editCamLocation').value.trim();
  const stream_type = document.getElementById('editCamStreamType').value;
  const stream_url = document.getElementById('editCamStreamUrl').value.trim();
  const uniform_check = document.getElementById('editCamUniformCheck')?.checked ?? true;

  if (!name) { toast('Lỗi', 'Vui lòng nhập tên camera', 'error'); return; }
  if (!stream_url) { toast('Lỗi', 'Vui lòng nhập đường dẫn luồng RTSP / Index', 'error'); return; }

  const btn = document.getElementById('btnSaveEditCam');
  btn.disabled = true;
  btn.innerText = 'Đang lưu...';
  try {
    const res = await api('PUT', `/api/v1/s/${schoolId}/cameras/${camId}`, {
      name,
      location,
      stream_type,
      stream_url,
      uniform_check
    });
    closeModal('modalEditCamera');
    if (res.public_stream_url) {
      toast('✅ Đã Lưu & Xuất Bản HTTPS', `Link: ${res.public_stream_url}`, 'success');
    } else {
      toast('Thành Công', res.message || 'Đã cập nhật cấu hình camera!', 'success');
    }
    loadCameras();
  } catch(e) {
    toast('Lỗi cập nhật', e.detail || e.message || 'Không thể lưu thay đổi', 'error');
  } finally {
    btn.disabled = false;
    btn.innerText = '💾 Lưu Cập Nhật →';
  }
}

async function quickToggleCamUniform(camId, enabled) {
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${camId}/toggle-uniform`, { enabled });
    toast('👗 Trang Phục Camera', res.message || `Đã ${enabled ? 'bật' : 'tắt'} nhận diện trang phục!`, 'success');
    loadCameras();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể đổi trạng thái nhận diện trang phục', 'error');
  }
}

function openLiveStreamModal(name, streamType, streamUrl, camId, publicStreamUrl) {
  document.getElementById('liveModalTitle').innerText = `👁️ Luồng Trực Tiếp: ${name || 'Camera'}`;
  document.getElementById('liveModalSub').innerText = `Nguồn: ${streamType || 'WEBCAM'} (${streamUrl || '0'})`;
  document.getElementById('liveSourceUrl').innerText = streamUrl || '0';

  // Hiển thị link Tailscale HTTPS công khai nếu có
  let finalPubUrl = publicStreamUrl;
  if (!finalPubUrl && currentLoadedCameras) {
    const found = currentLoadedCameras.find(c => c.id === camId);
    if (found && found.public_stream_url) finalPubUrl = found.public_stream_url;
  }

  const tsContainer = document.getElementById('liveTsUrlContainer');
  const tsLink = document.getElementById('liveTsLink');
  const btnCopyTs = document.getElementById('btnCopyTsLive');
  if (finalPubUrl) {
    if (tsContainer) tsContainer.style.display = 'block';
    if (tsLink) {
      tsLink.href = finalPubUrl;
      tsLink.innerText = finalPubUrl;
    }
    if (btnCopyTs) btnCopyTs.style.display = 'inline-block';
  } else {
    if (tsContainer) tsContainer.style.display = 'none';
    if (btnCopyTs) btnCopyTs.style.display = 'none';
  }
  
  const img = document.getElementById('liveStreamImg');
  const loading = document.getElementById('liveStreamLoading');
  const fpsBadge = document.getElementById('liveModalFpsBadge');
  if (fpsBadge) fpsBadge.style.display = 'none';
  img.style.display = 'none';
  loading.style.display = 'block';
  loading.innerHTML = `
    <div style="font-size:2rem;margin-bottom:10px;">📹</div>
    <div style="font-weight:600;color:var(--text);margin-bottom:6px;">Đang kết nối luồng Live Stream camera (25-30 FPS)...</div>
    <div style="font-size:0.78rem;max-width:450px;margin:0 auto;line-height:1.5;color:var(--muted);">
      Hệ thống đang mở luồng trực tiếp bảo mật qua WebSocket từ trạm AI...
    </div>
  `;

  const token = localStorage.getItem('stem_auth_token') || '';
  const cId = camId || 1;
  const sId = (typeof schoolId !== 'undefined' && schoolId) ? schoolId : 1;
  const streamSrc = `/api/v1/s/${sId}/cameras/${cId}/live-stream?token=${encodeURIComponent(token)}&t=${Date.now()}`;
  
  const directLink = document.getElementById('liveDirectLink');
  if (directLink) {
    directLink.href = streamSrc;
  }

  // TẠM DỪNG các luồng ở lưới nền để dồn 100% băng thông cho cửa sổ phóng to
  LiveStreamPlayer.pauseGrid();
  // KHỞI ĐỘNG luồng phóng to cận cảnh
  LiveStreamPlayer.start('liveStreamImg', cId, true);

  openModal('modalLiveStream');
}

function closeLiveStreamModal() {
  LiveStreamPlayer.stop('liveStreamImg');
  closeModal('modalLiveStream');
  // KHÔI PHỤC lại các luồng camera ở lưới nền
  LiveStreamPlayer.resumeGrid();
}

function toggleLiveStreamFit() {
  const img = document.getElementById('liveStreamImg');
  const btn = document.getElementById('btnLiveFit');
  if (!img) return;
  if (img.style.objectFit === 'cover') {
    img.style.objectFit = 'contain';
    if (btn) btn.innerText = '📐 Vừa Khung';
    toast('Tỉ Lệ', 'Đã chuyển sang chế độ Vừa Khung (Xem 100% góc rộng không bị cắt xén)', 'info');
  } else {
    img.style.objectFit = 'cover';
    if (btn) btn.innerText = '🔍 Lấp Đầy';
    toast('Tỉ Lệ', 'Đã chuyển sang chế độ Lấp Đầy (Cover)', 'info');
  }
}

function toggleModalFullscreen() {
  const elem = document.getElementById('liveModalContainer') || document.getElementById('modalLiveStream');
  if (!elem) return;
  if (!document.fullscreenElement) {
    if (elem.requestFullscreen) elem.requestFullscreen();
    else if (elem.webkitRequestFullscreen) elem.webkitRequestFullscreen();
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
  }
}

function onLiveStreamError() {
  document.getElementById('liveStreamImg').style.display = 'none';
  const loading = document.getElementById('liveStreamLoading');
  loading.style.display = 'block';
  loading.innerHTML = `
    <div style="font-size:2rem;margin-bottom:10px;">⚠️</div>
    <div style="font-weight:600;color:var(--orange);margin-bottom:6px;">Chưa phát hiện luồng phát Live Stream từ Trạm AI</div>
    <div style="font-size:0.78rem;max-width:480px;margin:0 auto;line-height:1.5;color:var(--muted);">
      Trạm AI nhận diện chưa được bật hoặc chưa kết nối được luồng camera.<br>
      Để xem hình ảnh trực tiếp, hãy khởi động trạm AI trên máy tính:<br>
      <code style="background:var(--bg);color:var(--green);padding:4px 8px;border-radius:4px;display:inline-block;margin:6px 0;">cd edge && python3 main.py</code><br>
      Sau khi bật trạm AI, luồng camera sẽ tự động phát trực tiếp tại đây!
    </div>
  `;
}


async function openAddCameraModal() {
  document.getElementById('acResult').style.display = 'none';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/cameras`);
    const nextNum = rows.length + 1;
    document.getElementById('acName').value = `Camera ${nextNum}`;
    document.getElementById('acLocation').value = `Cổng ${nextNum}`;
  } catch(e) {
    document.getElementById('acName').value = 'Camera 1';
  }
  document.getElementById('camStreamType').value = 'WEBCAM';
  onCamTypeChange('WEBCAM');
  openModal('modalAddCamera');
}

function onCamTypeChange(type) {
  const lbl = document.getElementById('camUrlLabel');
  const inp = document.getElementById('acStreamUrl');
  const hint = document.getElementById('camUrlHint');
  const tsNotice = document.getElementById('acTailscaleNotice');
  if (tsNotice) tsNotice.style.display = (type === 'RTSP') ? 'block' : 'none';
  
  if (type === 'WEBCAM') {
    lbl.innerText = 'Chỉ Số Camera (Index) *';
    inp.value = '0';
    inp.placeholder = '0 (Webcam mặc định) hoặc 1';
    hint.innerText = '0 = Webcam tích hợp sẵn trên Laptop / PC hoặc Camera USB';
  } else if (type === 'RTSP') {
    lbl.innerText = 'Đường Dẫn Luồng RTSP *';
    inp.value = 'rtsp://admin:123456@192.168.1.50:554/live';
    inp.placeholder = 'rtsp://user:pass@ip:port/stream';
    hint.innerText = 'Hỗ trợ tất cả Camera IP chuẩn RTSP H.264 / H.265 (Hikvision, Dahua, Ezviz, Imou, Yoosee...)';
  } else {
    lbl.innerText = 'Đường Dẫn HTTP / MJPEG *';
    inp.value = 'http://192.168.1.38:4747/video';
    inp.placeholder = 'http://ip:port/video';
    hint.innerText = 'Dùng DroidCam hoặc IP Webcam trên điện thoại để làm camera';
  }
}

async function doAddCamera() {
  const name        = document.getElementById('acName').value.trim();
  const location    = document.getElementById('acLocation').value.trim();
  const stream_type = document.getElementById('camStreamType').value;
  const stream_url  = document.getElementById('acStreamUrl').value.trim();
  const uniform_check = document.getElementById('acUniformCheck') ? document.getElementById('acUniformCheck').checked : true;
  const direction   = document.getElementById('acDirection')?.value || 'IN';

  if (!name) { toast('Thiếu Tên Trạm','Vui lòng đặt tên cho trạm camera.','error'); return; }

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras`, { name, location, stream_type, stream_url, uniform_check, direction });
    
    let tsBlock = '';
    if (res.public_stream_url) {
      tsBlock = `
        <div style="margin-top:8px;padding:8px 10px;border-radius:6px;background:rgba(168,85,247,0.12);border:1px solid rgba(168,85,247,0.25);">
          <div style="font-size:0.75rem;font-weight:700;color:var(--purple);margin-bottom:3px;">🌐 Luồng HTTPS Công Khai (Tailscale Funnel):</div>
          <code style="font-size:0.72rem;word-break:break-all;color:var(--text);display:block;margin-bottom:6px;">${escHtml(res.public_stream_url)}</code>
          <button class="btn btn-xs" style="padding:2px 8px;" onclick="copyStreamUrl('${escHtml(res.public_stream_url)}')">📋 Sao Chép Link HTTPS</button>
        </div>
      `;
    }

    document.getElementById('acResult').style.display = 'block';
    document.getElementById('acResult').innerHTML = `
      <div style="font-weight:700;color:var(--green);margin-bottom:6px;">✅ Đã tạo thành công "${escHtml(res.name)}"!</div>
      ${tsBlock}
      <div style="font-size:0.8rem;color:var(--orange);margin-top:6px;margin-bottom:4px;">🔑 Secret Key Raspberry Pi:</div>
      <code style="background:var(--bg);padding:6px 10px;border-radius:6px;display:block;word-break:break-all;font-size:0.8rem;color:var(--green);">${escHtml(res.secret_key)}</code>
      <button class="btn btn-outline btn-sm" style="margin-top:8px;border-color:var(--purple);color:var(--purple);" onclick="showEdgeConfigModal(${res.camera_id || res.id})">📋 Xem Chi Tiết Cấu Hình Raspberry Pi & Máy Tính</button>
    `;
    loadCameras();
    toast('✅ Đã Tạo Trạm Camera', escHtml(res.name), 'success');
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function showEdgeConfigModal(cameraId) {
  window._activeConfigCamId = cameraId;
  try {
    const res = await api('GET', `/api/v1/s/${schoolId}/cameras/${cameraId}/edge-config`);
    document.getElementById('edgeSecretKey').innerText  = res.secret_key || res.camera?.secret_key || '';
    document.getElementById('edgePiConfText').innerText = res.raspberry_pi_conf || '';
    document.getElementById('edgePyConfText').innerText = res.edge_config_snippet || '';
    switchConfigTab('PI');
    openModal('modalEdgeConfig');
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể lấy cấu hình', 'error');
  }
}

async function applyConfigToLocalCamera() {
  if (!window._activeConfigCamId) return;
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${window._activeConfigCamId}/apply-local`);
    toast('Thành Công', res.message || 'Đã áp dụng cấu hình vào trạm camera AI cục bộ!', 'success');
  } catch(e) {
    toast('Lỗi', e.detail || e.message || 'Không thể áp dụng cấu hình', 'error');
  }
}

function switchConfigTab(tab) {
  const panePi = document.getElementById('cfgPanePi');
  const panePy = document.getElementById('cfgPanePy');
  const btnPi  = document.getElementById('btnTabPi');
  const btnPy  = document.getElementById('btnTabPy');

  if (tab === 'PI') {
    panePi.style.display = 'block';
    panePy.style.display = 'none';
    btnPi.className = 'btn btn-primary btn-sm';
    btnPy.className = 'btn btn-outline btn-sm';
  } else {
    panePi.style.display = 'none';
    panePy.style.display = 'block';
    btnPi.className = 'btn btn-outline btn-sm';
    btnPy.className = 'btn btn-primary btn-sm';
  }
}

function copyTextById(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const text = el.innerText || el.textContent;
  navigator.clipboard.writeText(text);
  toast('📋 Đã Sao Chép', 'Cấu hình đã lưu vào bộ nhớ tạm!', 'success');
}

async function deleteCamera(id) {
  if (!confirm(`Xóa trạm camera #${id}?`)) return;
  try {
    await api('DELETE', `/api/v1/s/${schoolId}/cameras/${id}`);
    toast('🗑️ Đã Xóa Trạm Camera','','info');
    loadCameras();
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

// =============================================================================
// TAILSCALE FUNNEL & PUBLIC HTTPS STREAM HELPERS
// =============================================================================
function copyInputText(inputId) {
  const el = document.getElementById(inputId);
  if (!el || !el.value) {
    toast('Chưa có link', 'Chưa có đường dẫn HTTPS để sao chép', 'warning');
    return;
  }
  navigator.clipboard.writeText(el.value);
  toast('📋 Đã Sao Chép', el.value, 'success');
}

function copyStreamUrl(url) {
  if (!url) return;
  navigator.clipboard.writeText(url);
  toast('📋 Đã Sao Chép Link Stream HTTPS', url, 'success');
}

function copyLiveTsUrl() {
  const link = document.getElementById('liveTsLink');
  if (!link || !link.href || link.href === '#' || link.innerText === '—') return;
  navigator.clipboard.writeText(link.href);
  toast('📋 Đã Sao Chép Link Live HTTPS', link.href, 'success');
}

async function checkEditCamTailscaleStatus(camId, publicStreamUrl) {
  const badge = document.getElementById('editCamTsStatusBadge');
  const notice = document.getElementById('editCamTsNotice');
  const pubInp = document.getElementById('editCamPublicUrl');
  if (!badge) return;

  badge.className = 'chip chip-muted';
  badge.innerText = 'Đang kiểm tra...';
  if (notice) notice.style.display = 'none';

  try {
    const res = await api('GET', `/api/v1/s/${schoolId}/cameras/tailscale-status`);
    if (res.is_running && res.domain) {
      badge.className = 'chip chip-green';
      badge.innerText = `🟢 Sẵn Sàng (${res.domain})`;
      if (!pubInp.value && camId) {
        pubInp.value = `https://${res.domain}/api/v1/s/${schoolId}/cameras/${camId}/live-stream`;
      }
    } else if (res.backend_state === 'NeedsLogin') {
      badge.className = 'chip chip-orange';
      badge.innerText = '🟡 Cần Đăng Nhập Tailscale';
      if (notice) {
        notice.style.display = 'block';
        notice.innerHTML = `⚠️ <b>Tailscale chưa đăng nhập trên máy chủ.</b><br>Mở Terminal máy chủ chạy: <code style="background:var(--bg);padding:2px 6px;border-radius:4px;color:var(--orange);">tailscale up</code> để kích hoạt kết nối HTTPS toàn cầu.`;
      }
    } else if (!res.installed) {
      badge.className = 'chip chip-muted';
      badge.innerText = '⚪ Chưa Cài Đặt Tailscale';
    } else {
      badge.className = 'chip chip-muted';
      badge.innerText = `⚫ ${res.backend_state || 'Chưa Bật'}`;
    }
  } catch(e) {
    badge.className = 'chip chip-muted';
    badge.innerText = '⚫ Không Rõ Trạng Thái';
  }
}

async function publishEditCamTailscale() {
  const camId = document.getElementById('editCamId').value;
  const btn = document.getElementById('btnPublishTs');
  const pubInp = document.getElementById('editCamPublicUrl');
  const notice = document.getElementById('editCamTsNotice');
  if (!camId) return;

  if (btn) { btn.disabled = true; btn.innerText = 'Đang xuất bản...'; }
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${camId}/publish-tailscale`);
    if (res.public_stream_url) {
      if (pubInp) pubInp.value = res.public_stream_url;
      const badge = document.getElementById('editCamTsStatusBadge');
      if (badge) {
        badge.className = 'chip chip-green';
        badge.innerText = '🟢 ĐÃ XUẤT BẢN HTTPS';
      }
      if (notice) notice.style.display = 'none';
      toast('✅ Đã Xuất Bản HTTPS', res.public_stream_url, 'success');
      loadCameras();
    } else {
      if (notice) {
        notice.style.display = 'block';
        notice.innerHTML = `⚠️ ${res.message || 'Chưa thể tạo link HTTPS công khai. Vui lòng kiểm tra đăng nhập Tailscale.'}`;
      }
      toast('Thông Báo', res.message || 'Cần đăng nhập Tailscale trên máy chủ (tailscale up)', 'warning');
    }
  } catch(e) {
    toast('Lỗi Xuất Bản', e.detail || e.message || 'Không thể xuất bản Tailscale', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = '🚀 Xuất Bản'; }
  }
}

async function quickPublishCameraTailscale(camId) {
  try {
    toast('Đang xử lý', 'Đang kết nối Tailscale và tạo link HTTPS...', 'info');
    const res = await api('POST', `/api/v1/s/${schoolId}/cameras/${camId}/publish-tailscale`);
    if (res.public_stream_url) {
      toast('✅ Đã Xuất Bản HTTPS', res.public_stream_url, 'success');
    } else {
      toast('Thông Báo', res.message || 'Cần đăng nhập Tailscale trên máy chủ (tailscale up)', 'warning');
    }
    loadCameras();
  } catch(e) {
    toast('Lỗi', e.detail || e.message || 'Không thể xuất bản Tailscale', 'error');
  }
}



export {
  applyConfigToLocalCamera, applyDiscoveredCamIp, autoFixEditCamIp, checkEditCamTailscaleStatus, closeAllCamDropdowns, closeLiveStreamModal, copyInputText, copyLiveTsUrl, copyStreamUrl, copyTextById, deleteCamera, discoverLanCamsForEdit, doAddCamera, doSaveEditCamera, filterCamerasGrid, loadCameras, onCamTypeChange, onEditCamTypeChange, onGridStreamError, onGridStreamSuccess, onLiveStreamError, openAddCameraModal, openEditCameraModal, openLiveStreamModal, publishEditCamTailscale, quickPublishCameraTailscale, quickToggleCamUniform, refreshAllLiveGridStreams, reloadGridStream, renderCamerasGrid, setCamGridLayout, setCamViewMode, showEdgeConfigModal, switchConfigTab, testEditCamConnection, toggleCamDropdown, toggleFullscreenCamGrid, toggleLiveStreamFit, toggleModalFullscreen, toggleSingleCamFullscreen, updateCameraKpiStats
};
