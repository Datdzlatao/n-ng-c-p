import 'dart:io';
import 'dart:typed_data';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:dartz/dartz.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:image/image.dart' as img;
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/face_data_entity.dart';
import '../../domain/repositories/face_repository.dart';
import '../services/face_detection_service.dart';
import '../services/face_embedding_service.dart';

class FaceRepositoryImpl implements FaceRepository {
  final FaceDetectionService detectionService;
  final FaceEmbeddingService embeddingService;
  final FirebaseFirestore firestore;
  final FirebaseStorage storage;

  const FaceRepositoryImpl({
    required this.detectionService,
    required this.embeddingService,
    required this.firestore,
    required this.storage,
  });

  @override
  Future<Either<Failure, void>> registerFace({
    required String studentId,
    required img.Image faceImage,
  }) async {
    try {
      // Bước 1: Trích xuất embedding
      final embedding = await embeddingService.extractEmbedding(faceImage);

      // Bước 2: Lưu embedding vào Firestore (không lưu ảnh gốc vì privacy)
      await firestore
          .collection(AppConstants.colFaceData)
          .doc(studentId)
          .set({
        'studentId':   studentId,
        'embedding':   embedding,      // List<double> 128 phần tử
        'registeredAt': DateTime.now().toIso8601String(),
      });

      // Bước 3: Cập nhật flag hasFaceRegistered trong user doc
      await firestore
          .collection(AppConstants.colUsers)
          .doc(studentId)
          .update({'hasFaceRegistered': true});

      return const Right(null);
    } catch (e) {
      return Left(FaceRecognitionFailure('Đăng ký thất bại: $e'));
    }
  }

  @override
  Future<Either<Failure, FaceVerificationResult>> verifyFace({
    required img.Image faceImage,
    required String classId,
  }) async {
    try {
      // Bước 1: Trích xuất embedding từ ảnh hiện tại
      final currentEmbedding = await embeddingService.extractEmbedding(faceImage);

      // Bước 2: Lấy tất cả embeddings trong lớp từ Firestore
      // TODO: Tối ưu bằng cách cache embeddings trong RAM khi đưa lớp
      final studentsQuery = await firestore
          .collection(AppConstants.colUsers)
          .where('classId', isEqualTo: classId)
          .where('hasFaceRegistered', isEqualTo: true)
          .get();

      final studentIds = studentsQuery.docs.map((d) => d.id).toList();
      if (studentIds.isEmpty) {
        return const Right(FaceVerificationResult(isMatch: false, confidence: 0));
      }

      // Bước 3: Lấy embeddings và so sánh
      double bestSimilarity = 0.0;
      String? bestStudentId;
      String? bestStudentName;

      for (final sid in studentIds) {
        final faceDoc = await firestore
            .collection(AppConstants.colFaceData)
            .doc(sid)
            .get();
        if (!faceDoc.exists) continue;

        final storedEmbedding = List<double>.from(
          faceDoc.data()!['embedding'] as List<dynamic>,
        );
        final similarity = embeddingService.cosineSimilarity(
          currentEmbedding,
          storedEmbedding,
        );

        if (similarity > bestSimilarity) {
          bestSimilarity = similarity;
          bestStudentId = sid;
          // Lấy tên từ users collection
          bestStudentName = studentsQuery.docs
              .firstWhere((d) => d.id == sid)
              .data()['fullName'] as String?;
        }
      }

      final isMatch = bestSimilarity >= AppConstants.faceThreshold;
      return Right(FaceVerificationResult(
        isMatch:     isMatch,
        studentId:   isMatch ? bestStudentId  : null,
        studentName: isMatch ? bestStudentName : null,
        confidence:  bestSimilarity,
      ));
    } catch (e) {
      return Left(FaceRecognitionFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, FaceDataEntity?>> getFaceData(String studentId) async {
    try {
      final doc = await firestore
          .collection(AppConstants.colFaceData)
          .doc(studentId)
          .get();
      if (!doc.exists) return const Right(null);
      final data = doc.data()!;
      return Right(FaceDataEntity(
        studentId:    data['studentId'] as String,
        embedding:    List<double>.from(data['embedding'] as List),
        registeredAt: DateTime.parse(data['registeredAt'] as String),
      ));
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteFaceData(String studentId) async {
    try {
      await firestore.collection(AppConstants.colFaceData).doc(studentId).delete();
      await firestore.collection(AppConstants.colUsers).doc(studentId)
          .update({'hasFaceRegistered': false});
      return const Right(null);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }
}
