// Wrapper cho FlutterSecureStorage — Keychain (iOS) / Keystore (Android)
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorageService {
  final FlutterSecureStorage _storage;

  const SecureStorageService(this._storage);

  /// Lưu giá trị bảo mật
  Future<void> write(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  /// Đọc giá trị bảo mật, trả về null nếu không tồn tại
  Future<String?> read(String key) async {
    return await _storage.read(key: key);
  }

  /// Xóa một key
  Future<void> delete(String key) async {
    await _storage.delete(key: key);
  }

  /// Xóa toàn bộ dữ liệu (dùng khi logout)
  Future<void> deleteAll() async {
    await _storage.deleteAll();
  }

  /// Kiểm tra key có tồn tại không
  Future<bool> containsKey(String key) async {
    return await _storage.containsKey(key: key);
  }
}
