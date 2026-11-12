// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  INJECTION_CONTAINER.DART — Dependency Injection với GetIt               ║
// ║  Tất cả dependencies được đăng ký tại đây (Service Locator pattern)     ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:get_it/get_it.dart';
import 'package:dio/dio.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// ── Core ────────────────────────────────────────────────────────────────────
import 'core/network/network_info.dart';
import 'core/security/encryption_service.dart';
import 'core/security/secure_storage_service.dart';

// ── Auth Feature ─────────────────────────────────────────────────────────────
import 'features/auth/data/datasources/auth_remote_datasource.dart';
import 'features/auth/data/datasources/auth_remote_datasource_rest.dart';
import 'features/auth/data/datasources/auth_local_datasource.dart';
import 'features/auth/data/repositories/auth_repository_impl.dart';
import 'features/auth/domain/repositories/auth_repository.dart';
import 'features/auth/domain/usecases/login_usecase.dart';
import 'features/auth/domain/usecases/logout_usecase.dart';
import 'features/auth/domain/usecases/get_current_user_usecase.dart';
import 'features/auth/presentation/bloc/auth_bloc.dart';

// ── Attendance Feature ────────────────────────────────────────────────────────
import 'features/attendance/data/datasources/attendance_remote_datasource.dart';
import 'features/attendance/data/datasources/attendance_remote_datasource_rest.dart';
import 'features/attendance/data/datasources/attendance_local_datasource.dart';
import 'features/attendance/data/repositories/attendance_repository_impl.dart';
import 'features/attendance/domain/repositories/attendance_repository.dart';
import 'features/attendance/domain/usecases/mark_attendance_usecase.dart';
import 'features/attendance/domain/usecases/get_attendance_history_usecase.dart';
import 'features/attendance/domain/usecases/sync_offline_attendance_usecase.dart';
import 'features/attendance/presentation/bloc/attendance_bloc.dart';

// ── QR Code Feature ───────────────────────────────────────────────────────────
import 'features/qr_code/data/services/qr_service.dart';
import 'features/qr_code/domain/usecases/generate_qr_usecase.dart';
import 'features/qr_code/domain/usecases/validate_qr_usecase.dart';
import 'features/qr_code/presentation/bloc/qr_bloc.dart';

// ── Face Recognition Feature ──────────────────────────────────────────────────
import 'features/face_recognition/data/services/face_detection_service.dart';
import 'features/face_recognition/data/services/face_embedding_service.dart';
import 'features/face_recognition/data/repositories/face_repository_impl.dart';
import 'features/face_recognition/domain/repositories/face_repository.dart';
import 'features/face_recognition/domain/usecases/register_face_usecase.dart';
import 'features/face_recognition/domain/usecases/verify_face_usecase.dart';
import 'features/face_recognition/presentation/bloc/face_recognition_bloc.dart';

// ── Dress Code Feature ────────────────────────────────────────────────────────
import 'features/dress_code/data/services/dress_code_classifier_service.dart';
import 'features/dress_code/data/repositories/dress_code_repository_impl.dart';
import 'features/dress_code/domain/repositories/dress_code_repository.dart';
import 'features/dress_code/domain/usecases/check_dress_code_usecase.dart';
import 'features/dress_code/presentation/bloc/dress_code_bloc.dart';

/// Global Service Locator — truy cập từ bất cứ đâu qua [sl]
final sl = GetIt.instance;

/// Khởi tạo tất cả dependencies theo thứ tự đúng (dependency graph)
Future<void> init() async {
  // ── 1. External Services (Third-party) ─────────────────────────────────────
  // Firebase instances — singleton, dùng chung toàn app
  sl.registerLazySingleton<FirebaseAuth>(() => FirebaseAuth.instance);
  sl.registerLazySingleton<FirebaseFirestore>(() => FirebaseFirestore.instance);
  sl.registerLazySingleton<FirebaseStorage>(() => FirebaseStorage.instance);

  // Dio HTTP client với cấu hình cơ bản
  sl.registerLazySingleton<Dio>(() {
    final dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    return dio;
  });

  // Connectivity — kiểm tra mạng
  sl.registerLazySingleton<Connectivity>(() => Connectivity());

  // FlutterSecureStorage — Keychain (iOS) / Keystore (Android)
  sl.registerLazySingleton<FlutterSecureStorage>(
    () => const FlutterSecureStorage(
      aOptions: AndroidOptions(encryptedSharedPreferences: true),
    ),
  );

  // ── 2. Core Services ────────────────────────────────────────────────────────
  sl.registerLazySingleton<NetworkInfo>(
    () => NetworkInfoImpl(sl<Connectivity>()),
  );
  sl.registerLazySingleton<EncryptionService>(
    () => EncryptionService(),
  );
  sl.registerLazySingleton<SecureStorageService>(
    () => SecureStorageService(sl<FlutterSecureStorage>()),
  );

  // ── 3. Auth Feature ─────────────────────────────────────────────────────────
  // Data sources — Kết nối FastAPI REST API Backend
  sl.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSourceRestImpl(
      dio: sl<Dio>(),
      storage: sl<SecureStorageService>(),
    ),
  );
  sl.registerLazySingleton<AuthLocalDataSource>(
    () => AuthLocalDataSourceImpl(storage: sl<SecureStorageService>()),
  );
  // Repository
  sl.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(
      remoteDataSource: sl<AuthRemoteDataSource>(),
      localDataSource: sl<AuthLocalDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );
  // Use Cases
  sl.registerLazySingleton(() => LoginUseCase(sl<AuthRepository>()));
  sl.registerLazySingleton(() => LogoutUseCase(sl<AuthRepository>()));
  sl.registerLazySingleton(() => GetCurrentUserUseCase(sl<AuthRepository>()));
  // BLoC — factory (tạo mới mỗi lần, không share state)
  sl.registerFactory<AuthBloc>(
    () => AuthBloc(
      loginUseCase: sl<LoginUseCase>(),
      logoutUseCase: sl<LogoutUseCase>(),
      getCurrentUserUseCase: sl<GetCurrentUserUseCase>(),
    ),
  );

  // ── 4. QR Code Feature ──────────────────────────────────────────────────────
  sl.registerLazySingleton<QrService>(
    () => QrService(encryptionService: sl<EncryptionService>()),
  );
  sl.registerLazySingleton(() => GenerateQrUseCase(sl<QrService>()));
  sl.registerLazySingleton(() => ValidateQrUseCase(sl<QrService>()));
  sl.registerFactory<QrBloc>(
    () => QrBloc(
      generateQrUseCase: sl<GenerateQrUseCase>(),
      validateQrUseCase: sl<ValidateQrUseCase>(),
    ),
  );

  // ── 5. Face Recognition Feature ─────────────────────────────────────────────
  sl.registerLazySingleton<FaceDetectionService>(() => FaceDetectionService());
  sl.registerLazySingleton<FaceEmbeddingService>(() => FaceEmbeddingService());
  sl.registerLazySingleton<FaceRepository>(
    () => FaceRepositoryImpl(
      detectionService: sl<FaceDetectionService>(),
      embeddingService: sl<FaceEmbeddingService>(),
      firestore: sl<FirebaseFirestore>(),
      storage: sl<FirebaseStorage>(),
    ),
  );
  sl.registerLazySingleton(() => RegisterFaceUseCase(sl<FaceRepository>()));
  sl.registerLazySingleton(() => VerifyFaceUseCase(sl<FaceRepository>()));
  sl.registerFactory<FaceRecognitionBloc>(
    () => FaceRecognitionBloc(
      registerFaceUseCase: sl<RegisterFaceUseCase>(),
      verifyFaceUseCase: sl<VerifyFaceUseCase>(),
    ),
  );

  // ── 6. Dress Code Feature ────────────────────────────────────────────────────
  // DressCodeClassifierService cần khởi tạo async (load TFLite model)
  final dressCodeService = DressCodeClassifierService();
  await dressCodeService.initialize(); // Load model từ assets
  sl.registerLazySingleton<DressCodeClassifierService>(() => dressCodeService);
  sl.registerLazySingleton<DressCodeRepository>(
    () => DressCodeRepositoryImpl(classifier: sl<DressCodeClassifierService>()),
  );
  sl.registerLazySingleton(() => CheckDressCodeUseCase(sl<DressCodeRepository>()));
  sl.registerFactory<DressCodeBloc>(
    () => DressCodeBloc(checkDressCodeUseCase: sl<CheckDressCodeUseCase>()),
  );

  // ── 7. Attendance Feature ────────────────────────────────────────────────────
  sl.registerLazySingleton<AttendanceRemoteDataSource>(
    () => AttendanceRemoteDataSourceRestImpl(
      dio: sl<Dio>(),
      storage: sl<SecureStorageService>(),
    ),
  );
  sl.registerLazySingleton<AttendanceLocalDataSource>(
    () => AttendanceLocalDataSourceImpl(),
  );
  sl.registerLazySingleton<AttendanceRepository>(
    () => AttendanceRepositoryImpl(
      remoteDataSource: sl<AttendanceRemoteDataSource>(),
      localDataSource: sl<AttendanceLocalDataSource>(),
      networkInfo: sl<NetworkInfo>(),
    ),
  );
  sl.registerLazySingleton(() => MarkAttendanceUseCase(sl<AttendanceRepository>()));
  sl.registerLazySingleton(() => GetAttendanceHistoryUseCase(sl<AttendanceRepository>()));
  sl.registerLazySingleton(() => SyncOfflineAttendanceUseCase(sl<AttendanceRepository>()));
  sl.registerFactory<AttendanceBloc>(
    () => AttendanceBloc(
      markAttendanceUseCase: sl<MarkAttendanceUseCase>(),
      getAttendanceHistoryUseCase: sl<GetAttendanceHistoryUseCase>(),
      syncOfflineUseCase: sl<SyncOfflineAttendanceUseCase>(),
    ),
  );
}
