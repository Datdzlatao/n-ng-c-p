// Hằng số toàn cục của ứng dụng
class AppConstants {
  AppConstants._();

  // ── QR Code Security ────────────────────────────────────────────────────────
  /// Thời gian sống của QR code (giây) — hết hạn sau 60s để chống screenshot
  static const int qrTtlSeconds = 60;
  
  /// Độ dài nonce ngẫu nhiên trong QR payload (bytes)
  static const int qrNonceBytes = 16;

  // ── Face Recognition ────────────────────────────────────────────────────────
  /// Ngưỡng độ tương đồng cosine để xác nhận là cùng 1 người (0.0 - 1.0)
  /// Giá trị càng cao = càng khó nhận diện (chặt hơn)
  static const double faceThreshold = 0.75;
  
  /// Số lần chụp ảnh khi đăng ký khuôn mặt (để lấy embedding trung bình)
  static const int faceRegistrationSamples = 5;

  // ── Dress Code ─────────────────────────────────────────────────────────────
  /// Ngưỡng confidence để phân loại đúng trang phục (0.0 - 1.0)
  static const double dressCodeThreshold = 0.80;
  
  /// Đường dẫn TFLite model trong assets
  static const String dressCodeModelPath = 'assets/models/dress_code_classifier.tflite';
  static const String faceEmbeddingModelPath = 'assets/models/face_embedding.tflite';

  // ── Attendance ─────────────────────────────────────────────────────────────
  /// Cooldown giữa 2 lần điểm danh (giây) — tránh điểm danh trùng
  static const int attendanceCooldownSeconds = 300; // 5 phút
  
  /// Grace period sau khi giáo viên tạo session (phút)
  static const int sessionGracePeriodMinutes = 30;

  // ── Offline Sync ───────────────────────────────────────────────────────────
  /// Thời gian giữa các lần auto-sync dữ liệu offline (giây)
  static const int autoSyncIntervalSeconds = 60;

  // ── Firestore Collections ──────────────────────────────────────────────────
  static const String colUsers       = 'users';
  static const String colSessions    = 'sessions';
  static const String colAttendances = 'attendances';
  static const String colFaceData    = 'face_data';
  static const String colClasses     = 'classes';

  // ── Storage Paths ─────────────────────────────────────────────────────────
  static const String storageFaceImages = 'face_images/';
  static const String storageViolations = 'violations/';

  // ── Backend REST API ───────────────────────────────────────────────────────
  /// Base URL của Backend FastAPI REST API
  /// - Android Emulator: 'http://10.0.2.2:8000'
  /// - iOS Simulator / Desktop: 'http://localhost:8000'
  /// - Production / LAN: domain VPS hoặc IP máy chủ
  static const String defaultApiBaseUrl = 'http://10.0.2.2:8000';
  static const String keyApiBaseUrl     = 'api_base_url';
  static const String keySchoolId       = 'school_id';
  static const String keyRefreshToken   = 'refresh_token';
  static const String keyUseRestApi     = 'use_rest_api';

  // ── Secure Storage Keys ───────────────────────────────────────────────────
  static const String keyUserId     = 'user_id';
  static const String keyUserRole   = 'user_role';
  static const String keyAuthToken  = 'auth_token';
  static const String keyQrSecret   = 'qr_aes_key';
}
