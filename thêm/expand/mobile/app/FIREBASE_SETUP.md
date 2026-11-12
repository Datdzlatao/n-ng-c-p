# Hướng dẫn setup Firebase cho Smart Attendance App
#
# BƯỚC 1: Tạo Firebase project
# - Truy cập: https://console.firebase.google.com
# - Tạo project mới: "smart-attendance-stem"
# - Bật Authentication (Email/Password)
# - Tạo Firestore database (production mode)
# - Tạo Storage bucket
#
# BƯỚC 2: Thêm Android app
# - Package name: com.stemschool.smart_attendance
# - Tải google-services.json -> đặt vào android/app/
#
# BƯỚC 3: Thêm iOS app  
# - Bundle ID: com.stemschool.smartAttendance
# - Tải GoogleService-Info.plist -> đặt vào ios/Runner/
#
# BƯỚC 4: Chạy FlutterFire CLI
#   flutter pub global activate flutterfire_cli
#   flutterfire configure --project=smart-attendance-stem
# File firebase_options.dart sẽ được tạo tự động

# File này là placeholder — xóa và chạy lệnh ở Bước 4
