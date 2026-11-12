import 'package:dartz/dartz.dart';
import 'package:image/image.dart' as img;
import '../../../../core/errors/failures.dart';
import '../repositories/face_repository.dart';

class RegisterFaceUseCase {
  final FaceRepository repository;
  const RegisterFaceUseCase(this.repository);

  Future<Either<Failure, void>> call({
    required String studentId,
    required img.Image faceImage,
  }) {
    return repository.registerFace(
      studentId: studentId,
      faceImage: faceImage,
    );
  }
}
