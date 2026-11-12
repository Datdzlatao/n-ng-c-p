/// Dịch vụ phát hiện khuôn mặt dùng Google ML Kit
/// Chỉ phát hiện vị trí, không nhận diện danh tính
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

class FaceDetectionService {
  late final FaceDetector _detector;

  FaceDetectionService() {
    _detector = FaceDetector(
      options: FaceDetectorOptions(
        // Chế độ ACCURATE để phát hiện chính xác hơn (chấp nhận chậm hơn)
        performanceMode: FaceDetectorMode.accurate,
        // Yêu cầu phát hiện điểm mốc (mắt, mũi, miệng) để crop chính xác
        enableLandmarks: true,
        // Xác định hướng mặt để lọc out ảnh nghiêng quá mức
        enableClassification: false,
        // Chỉ phát hiện khuôn mặt tối thiểu 80x80px
        minFaceSize: 0.15,
      ),
    );
  }

  /// Phát hiện tất cả khuôn mặt trong ảnh
  Future<List<Face>> detectFaces(InputImage inputImage) async {
    return await _detector.processImage(inputImage);
  }

  /// Kiểm tra xem ảnh có đúng 1 khuôn mặt nhìn thẳng không
  /// Dùng khi đăng ký — chỉ chấp nhận 1 mặt rõ ràng
  Future<bool> hasExactlyOneFace(InputImage inputImage) async {
    final faces = await detectFaces(inputImage);
    return faces.length == 1;
  }

  void dispose() {
    _detector.close();
  }
}
