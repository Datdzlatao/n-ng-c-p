// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  firebase_options.dart — PLACEHOLDER                                     ║
// ║  File này sẽ được tạo tự động bởi FlutterFire CLI                       ║
// ║  Chạy: flutterfire configure --project=<your-firebase-project-id>        ║
// ╚══════════════════════════════════════════════════════════════════════════╝

// ignore_for_file: type=lint
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Các cấu hình Firebase theo từng platform.
/// Thay thế toàn bộ file này bằng output của lệnh: flutterfire configure
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError(
        'DefaultFirebaseOptions have not been configured for web - '
        'you can reconfigure this by running the FlutterFire CLI again.',
      );
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not supported for this platform.',
        );
    }
  }

  // ⚠️ THAY THẾ các giá trị này bằng config thật từ Firebase Console!
  static const FirebaseOptions android = FirebaseOptions(
    apiKey:             'YOUR_ANDROID_API_KEY',
    appId:              'YOUR_ANDROID_APP_ID',
    messagingSenderId:  'YOUR_SENDER_ID',
    projectId:          'YOUR_PROJECT_ID',
    storageBucket:      'YOUR_PROJECT_ID.appspot.com',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey:             'YOUR_IOS_API_KEY',
    appId:              'YOUR_IOS_APP_ID',
    messagingSenderId:  'YOUR_SENDER_ID',
    projectId:          'YOUR_PROJECT_ID',
    storageBucket:      'YOUR_PROJECT_ID.appspot.com',
    iosClientId:        'YOUR_IOS_CLIENT_ID',
    iosBundleId:        'com.stemschool.smartAttendance',
  );
}
