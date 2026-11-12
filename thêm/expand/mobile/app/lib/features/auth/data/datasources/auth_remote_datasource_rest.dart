import 'dart:async';
import 'package:dio/dio.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/security/secure_storage_service.dart';
import '../../domain/entities/user_entity.dart';
import '../models/user_model.dart';
import 'auth_remote_datasource.dart';

/// Hiện thực AuthRemoteDataSource giao tiếp trực tiếp với FastAPI REST API Backend
class AuthRemoteDataSourceRestImpl implements AuthRemoteDataSource {
  final Dio dio;
  final SecureStorageService storage;
  final _authStateController = StreamController<UserModel?>.broadcast();

  AuthRemoteDataSourceRestImpl({
    required this.dio,
    required this.storage,
  });

  Future<String> _getBaseUrl() async {
    final customUrl = await storage.read(AppConstants.keyApiBaseUrl);
    return (customUrl != null && customUrl.isNotEmpty)
        ? customUrl.replaceAll(RegExp(r'/+$'), '')
        : AppConstants.defaultApiBaseUrl;
  }

  @override
  Future<UserModel> login({
    required String email,
    required String password,
  }) async {
    try {
      final baseUrl = await _getBaseUrl();
      final response = await dio.post(
        '$baseUrl/api/v1/auth/login',
        data: {
          'username_or_phone': email.trim(),
          'password': password,
        },
        options: Options(
          headers: {'Content-Type': 'application/json'},
          validateStatus: (status) => status != null && status < 500,
        ),
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        final token = data['access_token'] as String?;
        final refreshToken = data['refresh_token'] as String?;
        final userMap = (data['user'] as Map<String, dynamic>?) ?? {};

        // Lưu JWT token vào Secure Storage
        if (token != null) {
          await storage.write(AppConstants.keyAuthToken, token);
        }
        if (refreshToken != null) {
          await storage.write(AppConstants.keyRefreshToken, refreshToken);
        }

        final userModel = _mapToUserModel(userMap);
        await storage.write(AppConstants.keyUserId, userModel.id);
        if (userMap['school_id'] != null) {
          await storage.write(AppConstants.keySchoolId, userMap['school_id'].toString());
        }

        _authStateController.add(userModel);
        return userModel;
      } else {
        final errDetail = response.data is Map ? response.data['detail'] : 'Đăng nhập thất bại';
        throw AuthException(errDetail?.toString() ?? 'Tài khoản hoặc mật khẩu không đúng');
      }
    } on DioException catch (e) {
      if (e.response != null && e.response?.data is Map) {
        final detail = e.response?.data['detail'];
        throw AuthException(detail?.toString() ?? 'Lỗi xác thực');
      }
      throw const AuthException('Không thể kết nối đến Máy Chủ Điểm Danh');
    } catch (e) {
      if (e is AuthException) rethrow;
      throw ServerException(e.toString());
    }
  }

  @override
  Future<void> logout() async {
    await storage.delete(AppConstants.keyAuthToken);
    await storage.delete(AppConstants.keyRefreshToken);
    await storage.delete(AppConstants.keyUserId);
    _authStateController.add(null);
  }

  @override
  Future<UserModel?> getCurrentUser() async {
    try {
      final token = await storage.read(AppConstants.keyAuthToken);
      if (token == null || token.isEmpty) return null;

      final baseUrl = await _getBaseUrl();
      final response = await dio.get(
        '$baseUrl/api/v1/auth/me',
        options: Options(
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
        ),
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        final userMap = (data['user'] as Map<String, dynamic>?) ?? {};
        final user = _mapToUserModel(userMap);
        _authStateController.add(user);
        return user;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  @override
  Stream<UserModel?> get authStateChanges => _authStateController.stream;

  UserModel _mapToUserModel(Map<String, dynamic> json) {
    final rawRole = (json['role'] as String? ?? 'STUDENT').toUpperCase();
    UserRole role = UserRole.student;
    if (rawRole == 'TEACHER') {
      role = UserRole.teacher;
    } else if (rawRole == 'HEADMASTER' || rawRole == 'ADMIN' || rawRole == 'PLATFORM_ADMIN') {
      role = UserRole.admin;
    }

    final id = json['id']?.toString() ?? '0';
    final email = (json['email'] as String?) ?? (json['username'] as String?) ?? '';
    final fullName = (json['full_name'] as String?) ?? email;
    final studentCode = (json['student_code'] as String?) ?? (json['user_code'] as String?);

    return UserModel(
      id: id,
      email: email,
      fullName: fullName,
      studentId: studentCode,
      classId: json['class_name'] as String?,
      role: role,
      avatarUrl: json['avatar_url'] as String?,
      isActive: json['status'] != 'SUSPENDED',
      hasFaceRegistered: json['verified_status'] == 'VERIFIED',
    );
  }
}
