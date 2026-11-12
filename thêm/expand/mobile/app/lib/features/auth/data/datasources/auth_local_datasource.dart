import '../../../../core/constants/app_constants.dart';
import '../../../../core/security/secure_storage_service.dart';

abstract class AuthLocalDataSource {
  Future<void> cacheUserId(String uid);
  Future<String?> getCachedUserId();
  Future<void> clearCache();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final SecureStorageService storage;
  const AuthLocalDataSourceImpl({required this.storage});

  @override
  Future<void> cacheUserId(String uid) async {
    await storage.write(AppConstants.keyUserId, uid);
  }

  @override
  Future<String?> getCachedUserId() async {
    return await storage.read(AppConstants.keyUserId);
  }

  @override
  Future<void> clearCache() async {
    await storage.deleteAll();
  }
}
