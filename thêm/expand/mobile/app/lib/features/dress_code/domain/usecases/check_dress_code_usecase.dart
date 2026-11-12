import 'package:dartz/dartz.dart';
import 'package:image/image.dart' as img;
import '../../../../core/errors/failures.dart';
import '../entities/dress_code_result_entity.dart';
import '../repositories/dress_code_repository.dart';

class CheckDressCodeUseCase {
  final DressCodeRepository repository;
  const CheckDressCodeUseCase(this.repository);

  Future<Either<Failure, DressCodeResultEntity>> call(img.Image image) {
    return repository.checkDressCode(image);
  }
}
