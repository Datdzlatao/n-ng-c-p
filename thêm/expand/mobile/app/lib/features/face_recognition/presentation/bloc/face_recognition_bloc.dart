// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  face_recognition_bloc.dart — BLoC cho nhận diện khuôn mặt              ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:image/image.dart' as img;
import 'package:equatable/equatable.dart';
import '../../../../core/constants/app_constants.dart';
import '../../domain/entities/face_data_entity.dart';
import '../../domain/usecases/register_face_usecase.dart';
import '../../domain/usecases/verify_face_usecase.dart';

// ── Events ──────────────────────────────────────────────────────────────────
abstract class FaceRecognitionEvent extends Equatable {
  const FaceRecognitionEvent();
  @override
  List<Object?> get props => [];
}

/// Xử lý 1 frame từ camera để detect + verify khuôn mặt
class ProcessCameraFrame extends FaceRecognitionEvent {
  final CameraImage cameraImage;
  final InputImageRotation rotation;
  final String classId; // Chỉ so sánh trong cùng lớp
  const ProcessCameraFrame({
    required this.cameraImage,
    required this.rotation,
    required this.classId,
  });
  @override
  List<Object> get props => [classId];
}

/// Đăng ký khuôn mặt mới
class RegisterFaceRequested extends FaceRecognitionEvent {
  final String studentId;
  final img.Image faceImage;
  const RegisterFaceRequested({
    required this.studentId,
    required this.faceImage,
  });
  @override
  List<Object> get props => [studentId];
}

/// Reset về trạng thái ban đầu
class FaceRecognitionReset extends FaceRecognitionEvent {}

// ── States ───────────────────────────────────────────────────────────────────
abstract class FaceRecognitionState extends Equatable {
  const FaceRecognitionState();
  @override
  List<Object?> get props => [];
}

class FaceRecognitionInitial extends FaceRecognitionState {}
class FaceRecognitionLoading extends FaceRecognitionState {}

/// Đang detect face realtime nhưng chưa nhận ra ai
class FaceDetecting extends FaceRecognitionState {
  final int faceCount; // Số khuôn mặt phát hiện được
  const FaceDetecting({required this.faceCount});
  @override
  List<Object> get props => [faceCount];
}

/// Đã nhận diện thành công
class FaceVerified extends FaceRecognitionState {
  final FaceVerificationResult result;
  const FaceVerified(this.result);
  @override
  List<Object> get props => [result];
}

/// Nhận diện không ra (stranger)
class FaceUnknown extends FaceRecognitionState {}

/// Đăng ký khuôn mặt thành công
class FaceRegistered extends FaceRecognitionState {}

class FaceRecognitionError extends FaceRecognitionState {
  final String message;
  const FaceRecognitionError(this.message);
  @override
  List<Object> get props => [message];
}

// ── BLoC ─────────────────────────────────────────────────────────────────────
class FaceRecognitionBloc
    extends Bloc<FaceRecognitionEvent, FaceRecognitionState> {
  final RegisterFaceUseCase registerFaceUseCase;
  final VerifyFaceUseCase verifyFaceUseCase;

  // Throttle: chỉ chạy inference mỗi N frame để giảm tải CPU
  int _frameCount = 0;
  static const int _inferenceInterval = 10; // Mỗi 10 frame mới inference

  FaceRecognitionBloc({
    required this.registerFaceUseCase,
    required this.verifyFaceUseCase,
  }) : super(FaceRecognitionInitial()) {
    on<ProcessCameraFrame>(_onProcessFrame);
    on<RegisterFaceRequested>(_onRegisterFace);
    on<FaceRecognitionReset>((_, emit) => emit(FaceRecognitionInitial()));
  }

  Future<void> _onProcessFrame(
    ProcessCameraFrame event,
    Emitter<FaceRecognitionState> emit,
  ) async {
    _frameCount++;

    // Skip frame nếu chưa đến interval — tránh overload
    if (_frameCount % _inferenceInterval != 0) return;

    // Chuyển CameraImage sang img.Image để xử lý
    final image = _convertCameraImage(event.cameraImage);
    if (image == null) return;

    // Verify khuôn mặt
    final result = await verifyFaceUseCase(
      faceImage: image,
      classId: event.classId,
    );

    result.fold(
      (failure) => emit(FaceRecognitionError(failure.message)),
      (verification) {
        if (verification.isMatch) {
          emit(FaceVerified(verification));
        } else if (verification.confidence > 0) {
          emit(FaceUnknown()); // Có khuôn mặt nhưng không nhận ra
        } else {
          emit(FaceDetecting(faceCount: 0)); // Không detect được mặt
        }
      },
    );
  }

  Future<void> _onRegisterFace(
    RegisterFaceRequested event,
    Emitter<FaceRecognitionState> emit,
  ) async {
    emit(FaceRecognitionLoading());
    final result = await registerFaceUseCase(
      studentId: event.studentId,
      faceImage: event.faceImage,
    );
    result.fold(
      (failure) => emit(FaceRecognitionError(failure.message)),
      (_) => emit(FaceRegistered()),
    );
  }

  /// Chuyển đổi CameraImage (YUV420) sang img.Image (RGB)
  img.Image? _convertCameraImage(CameraImage cameraImage) {
    try {
      final width  = cameraImage.width;
      final height = cameraImage.height;

      // Xử lý format YUV420 (Android)
      if (cameraImage.format.group == ImageFormatGroup.yuv420) {
        final yPlane  = cameraImage.planes[0];
        final uvPlane = cameraImage.planes[1];

        // Simple YUV to RGB conversion
        final image = img.Image(width: width, height: height);
        final yBuffer  = yPlane.bytes;
        final uvBuffer = uvPlane.bytes;

        for (int y = 0; y < height; y++) {
          for (int x = 0; x < width; x++) {
            final yValue = yBuffer[y * yPlane.bytesPerRow + x];
            final uvIndex = (y ~/ 2) * uvPlane.bytesPerRow + (x ~/ 2) * 2;
            final uValue = uvBuffer[uvIndex];
            final vValue = uvBuffer[uvIndex + 1];

            // YUV to RGB
            final r = (yValue + 1.370705 * (vValue - 128)).clamp(0, 255).toInt();
            final g = (yValue - 0.698001 * (vValue - 128) - 0.337633 * (uValue - 128)).clamp(0, 255).toInt();
            final b = (yValue + 1.732446 * (uValue - 128)).clamp(0, 255).toInt();

            image.setPixelRgb(x, y, r, g, b);
          }
        }
        return image;
      }

      // Format BGRA8888 (iOS)
      if (cameraImage.format.group == ImageFormatGroup.bgra8888) {
        final bytes = cameraImage.planes[0].bytes;
        return img.Image.fromBytes(
          width: width,
          height: height,
          bytes: bytes.buffer,
          order: img.ChannelOrder.bgra,
        );
      }

      return null;
    } catch (_) {
      return null;
    }
  }
}
