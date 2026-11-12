/// Dịch vụ phân loại trang phục dùng MobileNetV2 TFLite
/// Binary classification: 0 = SAI, 1 = ĐÚNG trang phục
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';
import '../../../../core/constants/app_constants.dart';
import '../../domain/entities/dress_code_result_entity.dart';

class DressCodeClassifierService {
  Interpreter? _interpreter;
  bool _isInitialized = false;

  /// Load TFLite model từ assets/ — gọi 1 lần khi app khởi động
  Future<void> initialize() async {
    if (_isInitialized) return;
    try {
      _interpreter = await Interpreter.fromAsset(
        AppConstants.dressCodeModelPath,
        options: InterpreterOptions()..threads = 2,
      );
      _isInitialized = true;
    } catch (e) {
      // Model chưa có trong assets — fallback về "chưa bật"
      _isInitialized = false;
    }
  }

  /// Phân loại ảnh: đúng hay sai trang phục
  /// [bodyImage] là ảnh toàn thân, crop từ camera
  Future<DressCodeResultEntity> classify(img.Image bodyImage) async {
    // Nếu model chưa load được, trả về kết quả chưa xác định
    if (!_isInitialized || _interpreter == null) {
      return const DressCodeResultEntity(
        status:     DressCodeStatus.correct, // Mặc định pass khi chưa có model
        confidence: 0.5,
        message:    'Mô hình chưa sẵn sàng',
      );
    }

    // Resize về 224x224 (MobileNetV2 standard input)
    final resized = img.copyResize(bodyImage, width: 224, height: 224);
    final input   = _imageToFloat32(resized);

    // Output shape: [1, 2] — [sai, đúng]
    final output  = List.generate(1, (_) => List.filled(2, 0.0));
    _interpreter!.run(input, output);

    final probCorrect = output[0][1]; // Xác suất đúng trang phục
    final isCorrect   = probCorrect >= AppConstants.dressCodeThreshold;

    return DressCodeResultEntity(
      status:     isCorrect ? DressCodeStatus.correct : DressCodeStatus.incorrect,
      confidence: isCorrect ? probCorrect : output[0][0],
      message:    isCorrect
          ? 'Đúng trang phục ✓'
          : 'Sai trang phục! Vui lòng mặc đồng phục đúng quy định',
    );
  }

  List<List<List<List<double>>>> _imageToFloat32(img.Image image) {
    return List.generate(1, (_) =>
      List.generate(224, (y) =>
        List.generate(224, (x) {
          final pixel = image.getPixel(x, y);
          // Normalize theo ImageNet mean/std (MobileNet standard)
          return [
            (pixel.r / 255.0 - 0.485) / 0.229,
            (pixel.g / 255.0 - 0.456) / 0.224,
            (pixel.b / 255.0 - 0.406) / 0.225,
          ];
        })
      )
    );
  }

  void dispose() => _interpreter?.close();
}
