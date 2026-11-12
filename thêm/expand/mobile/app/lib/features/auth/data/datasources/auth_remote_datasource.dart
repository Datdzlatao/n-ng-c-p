import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<UserModel> login({required String email, required String password});
  Future<void> logout();
  Future<UserModel?> getCurrentUser();
  Stream<UserModel?> get authStateChanges;
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final FirebaseAuth firebaseAuth;
  final FirebaseFirestore firestore;

  const AuthRemoteDataSourceImpl({
    required this.firebaseAuth,
    required this.firestore,
  });

  @override
  Future<UserModel> login({
    required String email,
    required String password,
  }) async {
    try {
      // Đăng nhập Firebase Auth
      final credential = await firebaseAuth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final uid = credential.user!.uid;

      // Lấy thêm thông tin user từ Firestore
      final doc = await firestore
          .collection(AppConstants.colUsers)
          .doc(uid)
          .get();

      if (!doc.exists) {
        throw const AuthException('Tài khoản không tồn tại trong hệ thống');
      }

      return UserModel.fromJson(doc.data()!, uid);
    } on FirebaseAuthException catch (e) {
      // Chuyển Firebase error code sang message tiếng Việt
      throw AuthException(_mapFirebaseError(e.code));
    } catch (e) {
      if (e is AuthException) rethrow;
      throw ServerException(e.toString());
    }
  }

  @override
  Future<void> logout() async {
    await firebaseAuth.signOut();
  }

  @override
  Future<UserModel?> getCurrentUser() async {
    final user = firebaseAuth.currentUser;
    if (user == null) return null;
    try {
      final doc = await firestore
          .collection(AppConstants.colUsers)
          .doc(user.uid)
          .get();
      if (!doc.exists) return null;
      return UserModel.fromJson(doc.data()!, user.uid);
    } catch (_) {
      return null;
    }
  }

  @override
  Stream<UserModel?> get authStateChanges {
    return firebaseAuth.authStateChanges().asyncMap((user) async {
      if (user == null) return null;
      return getCurrentUser();
    });
  }

  /// Map Firebase Auth error codes sang tiếng Việt
  String _mapFirebaseError(String code) {
    switch (code) {
      case 'user-not-found':       return 'Email không tồn tại';
      case 'wrong-password':       return 'Mật khẩu không đúng';
      case 'invalid-email':        return 'Email không hợp lệ';
      case 'user-disabled':        return 'Tài khoản đã bị vô hiệu hóa';
      case 'too-many-requests':    return 'Quá nhiều lần thử. Vui lòng thử lại sau';
      case 'network-request-failed': return 'Lỗi kết nối mạng';
      default:                     return 'Đăng nhập thất bại. Vui lòng thử lại';
    }
  }
}
