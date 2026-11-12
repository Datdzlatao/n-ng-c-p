// Tiện ích xin quyền camera và storage
import 'package:permission_handler/permission_handler.dart';

class PermissionHandlerUtil {
  PermissionHandlerUtil._();

  /// Xin quyền camera — cần cho QR scan và face recognition
  static Future<bool> requestCamera() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  /// Xin quyền đọc/ghi storage — cần khi lưu ảnh vi phạm
  static Future<bool> requestStorage() async {
    // Android 13+ dùng photos permission thay storage
    if (await Permission.photos.isSupported) {
      return (await Permission.photos.request()).isGranted;
    }
    return (await Permission.storage.request()).isGranted;
  }

  /// Xin cả camera và storage cùng lúc
  static Future<Map<Permission, PermissionStatus>> requestAll() async {
    return await [
      Permission.camera,
      Permission.photos,
    ].request();
  }

  /// Mở Settings của hệ thống nếu người dùng đã từ chối vĩnh viễn
  static Future<void> openSettings() async {
    await openAppSettings();
  }
}
