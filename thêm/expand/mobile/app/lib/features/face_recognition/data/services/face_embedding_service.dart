/// Dịch vụ trích xuất face embedding dùng TFLite MobileFaceNet model
/// Output: vector 128-d biểu diễn đặc trưng khuôn mặt
import 'dart:math';
import 'dart:typed_data';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';
import '../../../../core/constants/app_constants.dart';

class FaceEmbeddingService {
  Interpreter? _interpreter;
  bool _isInitialized = false;

  /// Khởi tạo và load TFLite model
  Future<void> initialize() async {
    if (_isInitialized) return;
    try {
      _interpreter = await Interpreter.fromAsset(
        AppConstants.faceEmbeddingModelPath,
        options: InterpreterOptions()..threads = 4,
      );
      _isInitialized = true;
    } catch (e) {
      throw Exception('Không thể load face embedding model: $e');
    }
  }

  /// Trích xuất vector 128-d từ ảnh khuôn mặt
  /// [faceImage] phải được crop và resize về 112x112px trước khi truyền vào
  Future<List<double>> extractEmbedding(img.Image faceImage) async {
    if (!_isInitialized) await initialize();

    // Resize về kích thước model yêu cầu (112x112)
    final resized = img.copyResize(faceImage, width: 112, height: 112);

    // Chuyển sang float32 tensor, normalize [-1, 1]
    final input = _imageToFloat32(resized);
    final output = List.filled(128, 0.0).reshape([1, 128]);

    _interpreter!.run(input, output);

    // Lấy vector và normalize thành unit vector (cosine similarity)
    final embedding = List<double>.from(output[0]);
    return _normalizeVector(embedding);
  }

  /// So sánh 2 embedding bằng cosine similarity
  /// Trả về [0.0, 1.0] — càng gần 1.0 càng giống nhau
  double cosineSimilarity(List<double> a, List<double> b) {
    double dot = 0.0;
    for (int i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
    }
    // Vì đã normalize nên cosine similarity = dot product
    return dot.clamp(0.0, 1.0);
  }

  /// Chuyển ảnh sang Float32List [-1, 1]
  List<List<List<List<double>>>> _imageToFloat32(img.Image image) {
    return List.generate(1, (_) =>
      List.generate(112, (y) =>
        List.generate(112, (x) {
          final pixel = image.getPixel(x, y);
          return [
            (pixel.r / 127.5) - 1.0,
            (pixel.g / 127.5) - 1.0,
            (pixel.b / 127.5) - 1.0,
          ];
        })
      )
    );
  }

  /// Chuẩn hóa vector thành unit vector
  List<double> _normalizeVector(List<double> vec) {
    final norm = sqrt(vec.fold(0.0, (sum, v) => sum + v * v));
    if (norm == 0) return vec;
    return vec.map((v) => v / norm).toList();
  }

  void dispose() => _interpreter?.close();
}
