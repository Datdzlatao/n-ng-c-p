import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../../../auth/domain/entities/user_entity.dart';
import '../../data/services/qr_service.dart';

class GenerateQrUseCase {
  final QrService qrService;
  const GenerateQrUseCase(this.qrService);

  /// Tạo QR string cho session điểm danh
  Either<Failure, String> call({
    required String sessionId,
    required UserEntity teacher,
    required String classId,
  }) {
    try {
      final qrString = qrService.generateQrString(
        sessionId: sessionId,
        teacherId: teacher.id,
        classId:   classId,
      );
      return Right(qrString);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }
}
