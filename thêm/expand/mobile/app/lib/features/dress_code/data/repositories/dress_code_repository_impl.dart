import 'package:dartz/dartz.dart';
import 'package:image/image.dart' as img;
import '../../../../core/errors/failures.dart';
import '../../domain/entities/dress_code_result_entity.dart';
import '../../domain/repositories/dress_code_repository.dart';
import '../services/dress_code_classifier_service.dart';

class DressCodeRepositoryImpl implements DressCodeRepository {
  final DressCodeClassifierService classifier;
  const DressCodeRepositoryImpl({required this.classifier});

  @override
  Future<Either<Failure, DressCodeResultEntity>> checkDressCode(img.Image image) async {
    try {
      final result = await classifier.classify(image);
      return Right(result);
    } catch (e) {
      return Left(MLFailure(e.toString()));
    }
  }
}
