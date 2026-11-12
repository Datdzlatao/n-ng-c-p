import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_constants.dart';
import '../../domain/usecases/generate_qr_usecase.dart';
import '../../domain/usecases/validate_qr_usecase.dart';
import 'qr_event.dart';
import 'qr_state.dart';

class QrBloc extends Bloc<QrEvent, QrState> {
  final GenerateQrUseCase generateQrUseCase;
  final ValidateQrUseCase validateQrUseCase;

  Timer? _expiryTimer; // Timer tự động hết hạn QR sau TTL

  QrBloc({
    required this.generateQrUseCase,
    required this.validateQrUseCase,
  }) : super(QrInitial()) {
    on<GenerateQrRequested>(_onGenerateQr);
    on<QrRefreshRequested>(_onRefreshQr);
    on<QrScanned>(_onQrScanned);
    on<QrReset>((_, emit) => emit(QrInitial()));
  }

  Future<void> _onGenerateQr(GenerateQrRequested event, Emitter<QrState> emit) async {
    emit(QrLoading());
    final result = generateQrUseCase(
      sessionId: event.sessionId,
      teacher: event.teacher,
      classId: event.classId,
    );
    result.fold(
      (failure) => emit(QrError(failure.message)),
      (qrString) {
        final expiresAt = DateTime.now().add(
          const Duration(seconds: AppConstants.qrTtlSeconds),
        );
        emit(QrGenerated(qrString: qrString, expiresAt: expiresAt));
        _startExpiryTimer(event.sessionId, event.teacher, event.classId);
      },
    );
  }

  Future<void> _onRefreshQr(QrRefreshRequested event, Emitter<QrState> emit) async {
    _cancelTimer();
    add(GenerateQrRequested(
      sessionId: event.sessionId,
      teacher: event.teacher,
      classId: event.classId,
    ));
  }

  /// Xử lý khi scan QR
  Future<void> _onQrScanned(QrScanned event, Emitter<QrState> emit) async {
    emit(QrLoading());
    final result = validateQrUseCase(event.rawData);
    result.fold(
      (failure) => emit(QrError(failure.message)),
      (payload) => emit(QrScanSuccess(payload)),
    );
  }

  /// Bắt đầu đếm ngược — khi hết thì emit QrExpired
  void _startExpiryTimer(String sessionId, dynamic teacher, String classId) {
    _cancelTimer();
    _expiryTimer = Timer(
      const Duration(seconds: AppConstants.qrTtlSeconds),
      () => add(QrReset()), // Khi hết hạn, BLoC tự động emit expired
    );
  }

  void _cancelTimer() => _expiryTimer?.cancel();

  @override
  Future<void> close() {
    _cancelTimer();
    return super.close();
  }
}
