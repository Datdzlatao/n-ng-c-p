import 'package:dartz/dartz.dart';
import 'package:image/image.dart' as img;
import '../../../../core/errors/failures.dart';
import '../entities/dress_code_result_entity.dart';

abstract class DressCodeRepository {
  Future<Either<Failure, DressCodeResultEntity>> checkDressCode(img.Image image);
}
