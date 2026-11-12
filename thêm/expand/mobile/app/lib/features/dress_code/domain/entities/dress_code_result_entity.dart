import 'package:equatable/equatable.dart';

/// Kết quả phân loại trang phục (binary)
enum DressCodeStatus { correct, incorrect }

class DressCodeResultEntity extends Equatable {
  final DressCodeStatus status;    // Đúng / sai
  final double confidence;         // Độ chắc chắn (0.0 - 1.0)
  final String message;            // Thông báo

  const DressCodeResultEntity({
    required this.status,
    required this.confidence,
    required this.message,
  });

  bool get isCorrect => status == DressCodeStatus.correct;

  @override
  List<Object> get props => [status, confidence, message];
}
