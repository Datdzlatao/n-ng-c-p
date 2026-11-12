import 'package:connectivity_plus/connectivity_plus.dart';

/// Abstract interface để dễ mock khi testing
abstract class NetworkInfo {
  /// Trả về true nếu thiết bị đang có kết nối mạng
  Future<bool> get isConnected;
}

/// Implementation thực tế dùng connectivity_plus
class NetworkInfoImpl implements NetworkInfo {
  final Connectivity connectivity;

  const NetworkInfoImpl(this.connectivity);

  @override
  Future<bool> get isConnected async {
    final results = await connectivity.checkConnectivity();
    // Có mạng nếu kết quả không rỗng VÀ không phải ConnectivityResult.none
    return results.isNotEmpty &&
        !results.contains(ConnectivityResult.none);
  }
}
