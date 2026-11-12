import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../data/services/qr_service.dart';
import '../entities/qr_payload_entity.dart';

class ValidateQrUseCase {
  final QrService qrService;
  const ValidateQrUseCase(this.qrService);

  Either<Failure, QrPayloadEntity> call(String rawQrData) {
    try {
      final payload = qrService.validateQrString(rawQrData);
      return Right(payload);
    } on QrException catch (e) {
      return Left(QrFailure(e.message));
    } catch (e) {
      return Left(QrFailure(e.toString()));
    }
  }
}
