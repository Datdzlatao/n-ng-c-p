import 'package:dartz/dartz.dart';
import 'package:image/image.dart' as img;
import '../../../../core/errors/failures.dart';
import '../entities/face_data_entity.dart';
import '../repositories/face_repository.dart';

class VerifyFaceUseCase {
  final FaceRepository repository;
  const VerifyFaceUseCase(this.repository);

  Future<Either<Failure, FaceVerificationResult>> call({
    required img.Image faceImage,
    required String classId,
  }) {
    return repository.verifyFace(
      faceImage: faceImage,
      classId: classId,
    );
  }
}
