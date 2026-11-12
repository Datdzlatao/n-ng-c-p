// app/js/modals/faceid_scanner.js — Apple-Style Guided FaceID Scanner
// ── Apple FaceID Guided Scanner Workflow ──────────
async function openFaceIDScanner(student = null) {
  if (typeof student === 'number' || typeof student === 'string') {
    student = (window.currentStudentsList || []).find(x => x.id == student || x.student_code == student) || null;
  }
  if (student && typeof BiometricScanner !== 'undefined') {
    BiometricScanner.start({
      schoolId: schoolId,
      studentId: student.id,
      studentCode: student.student_code,
      studentName: student.full_name,
      verifyAccount: true,
      onComplete: () => {
        toast('✨ Đã Nạp FaceID Hoàn Tất', `Đã đồng bộ ảnh nhận diện của ${student.full_name} (${student.student_code})`, 'success');
        loadStudents();
      }
    });
    return;
  }

  // Nếu bấm nút "+ Cấp Mã & Quét FaceID" trên thanh công cụ
  openModal('modalAddStudent');
  toast('Cấp Mã & Quét FaceID', 'Nhập thông tin học sinh rồi bấm "Thêm & Quét FaceID Ngay"', 'info');
}

// Fallback legacy scanner controls (kept for safety)
async function legacyOpenFaceIDScannerModal(student = null) {
  activeFaceEnrollStudent = student;
  currentFacePoseIndex = 0;
  capturedFacePoses = { front: null, left: null, right: null, tilt: null };

  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`fidPreview${i}`);
    if (el) el.src = '';
  }

  const badge = document.getElementById('faceidStepBadge');
  const prog  = document.getElementById('faceidProgressVal');
  const btnSnap = document.getElementById('btnSnapFace');
  const btnFinish = document.getElementById('btnFinishFace');
  
  if (badge) badge.innerText = FACE_STEPS[0].label;
  if (prog) prog.style.width = '0%';
  if (btnSnap) btnSnap.style.display = 'inline-block';
  if (btnFinish) btnFinish.style.display = 'none';

  if (student) {
    document.getElementById('faceidStudentInputs').style.display = 'none';
  } else {
    document.getElementById('faceidStudentInputs').style.display = 'block';
  }
  openModal('modalFaceIDScanner');

  // Start Camera
  try {
    const video = document.getElementById('faceidVideo');
    faceidStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false
    });
    video.srcObject = faceidStream;
  } catch(e) {
    toast('Lỗi Camera', 'Không thể mở Camera để quét FaceID: ' + (e.message || e), 'error');
  }
}

function snapCurrentPose() {
  const video  = document.getElementById('faceidVideo');
  const canvas = document.getElementById('faceidCanvas');
  if (!video || !canvas) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  
  // Flip horizontally so the captured photo matches the mirror view
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
  const stepKey = FACE_STEPS[currentFacePoseIndex].id;
  capturedFacePoses[stepKey] = dataUrl;

  // Update preview strip
  const previewImg = document.getElementById(`fidPreview${currentFacePoseIndex + 1}`);
  if (previewImg) previewImg.src = dataUrl;

  currentFacePoseIndex++;
  const progVal = document.getElementById('faceidProgressVal');
  const badge   = document.getElementById('faceidStepBadge');

  if (currentFacePoseIndex < FACE_STEPS.length) {
    badge.innerText = FACE_STEPS[currentFacePoseIndex].label;
    progVal.style.width = FACE_STEPS[currentFacePoseIndex - 1].pct;
    toast('📸 Đã Chụp Góc ' + currentFacePoseIndex, 'Hãy làm theo hướng dẫn bước tiếp theo', 'info');
  } else {
    progVal.style.width = '100%';
    badge.innerText = '✅ Thu thập 4 góc FaceID hoàn tất!';
    document.getElementById('btnSnapFace').style.display = 'none';
    document.getElementById('btnFinishFace').style.display = 'inline-block';
    toast('🎉 Hoàn Tất 4 Góc', 'Bấm "Hoàn Tất & Cấp Thẻ QR" để lưu trữ', 'success');
  }
}

async function finishFaceEnrollment() {
  let studentId = activeFaceEnrollStudent?.id;
  let studentCode = activeFaceEnrollStudent?.student_code;

  // If new student, create first
  if (!studentId) {
    const full_name = document.getElementById('fidStuName').value.trim();
    const class_id  = parseInt(document.getElementById('fidStuClass').value) || null;
    const parent_phone = document.getElementById('fidStuPhone').value.trim() || null;
    if (!full_name) { toast('Cần Họ Tên', 'Vui lòng nhập họ tên học sinh', 'error'); return; }

    try {
      const resNew = await api('POST', `/api/v1/s/${schoolId}/students`, {
        full_name, class_id, parent_phone
      });
      studentId = resNew.student_id;
      studentCode = resNew.student_code;
    } catch(e) {
      toast('Lỗi tạo học sinh', e.detail || '', 'error');
      return;
    }
  }

  // Upload 4-angle FaceID pictures
  try {
    const payload = {
      front_image_b64: capturedFacePoses.front,
      left_image_b64:  capturedFacePoses.left,
      right_image_b64: capturedFacePoses.right,
      tilt_image_b64:  capturedFacePoses.tilt,
    };
    const resEnroll = await api('POST', `/api/v1/s/${schoolId}/students/${studentId}/face-enroll`, payload);
    
    closeFaceIDScanner();
    toast('✨ Cấp Mã & FaceID Thành Công', `Mã HS: ${resEnroll.student_code} · Đã nạp vào bộ nhận diện`, 'success');
    loadStudents();
    showStudentCard(resEnroll.student_code);
  } catch(e) {
    toast('Lỗi Lưu FaceID', e.detail || '', 'error');
  }
}

function closeFaceIDScanner() {
  if (faceidStream) {
    faceidStream.getTracks().forEach(track => track.stop());
    faceidStream = null;
  }
  closeModal('modalFaceIDScanner');
}



export {
  closeFaceIDScanner, finishFaceEnrollment, legacyOpenFaceIDScannerModal, openFaceIDScanner, snapCurrentPose
};
