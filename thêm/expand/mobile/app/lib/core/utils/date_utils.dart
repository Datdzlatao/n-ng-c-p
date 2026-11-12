import 'package:intl/intl.dart';

class AppDateUtils {
  AppDateUtils._();

  static final _dateFormatter   = DateFormat('dd/MM/yyyy', 'vi');
  static final _timeFormatter   = DateFormat('HH:mm', 'vi');
  static final _dateTimeFormatter = DateFormat('dd/MM/yyyy HH:mm', 'vi');
  static final _fullFormatter   = DateFormat('EEEE, dd MMMM yyyy', 'vi');

  static String formatDate(DateTime dt) => _dateFormatter.format(dt);
  static String formatTime(DateTime dt) => _timeFormatter.format(dt);
  static String formatDateTime(DateTime dt) => _dateTimeFormatter.format(dt);
  static String formatFull(DateTime dt) => _fullFormatter.format(dt);

  /// Kiểm tra QR có còn trong thời hạn sống không
  static bool isWithinTtl(DateTime createdAt, int ttlSeconds) {
    final expiry = createdAt.add(Duration(seconds: ttlSeconds));
    return DateTime.now().isBefore(expiry);
  }

  /// Lấy ngày hôm nay dưới dạng string key cho Firestore
  static String todayKey() => DateFormat('yyyy-MM-dd').format(DateTime.now());
}
