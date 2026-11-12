// Dịch vụ mã hóa AES-256 CBC cho QR payload
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:encrypt/encrypt.dart' as enc;

class EncryptionService {
  // AES key 256-bit (32 bytes) — được tạo ngẫu nhiên khi khởi tạo
  // Trong production: lưu key này vào Firebase Remote Config hoặc secure backend
  late final enc.Key _aesKey;
  final Random _random = Random.secure();

  EncryptionService() {
    // Tạo key từ chuỗi cố định (demo) — thực tế nên lấy từ server
    final keyBytes = utf8.encode('STEM_SCHOOL_SECURE_KEY_2024_V1_XY');
    _aesKey = enc.Key(Uint8List.fromList(keyBytes.take(32).toList()));
  }

  /// Mã hóa chuỗi plaintext bằng AES-256 CBC
  /// Trả về base64 encoded: IV (16 bytes) + ciphertext
  String encrypt(String plainText) {
    final iv = enc.IV.fromSecureRandom(16); // IV ngẫu nhiên mỗi lần
    final encrypter = enc.Encrypter(enc.AES(_aesKey, mode: enc.AESMode.cbc));
    final encrypted = encrypter.encrypt(plainText, iv: iv);
    // Ghép IV + ciphertext rồi encode base64
    final combined = [...iv.bytes, ...encrypted.bytes];
    return base64Url.encode(combined);
  }

  /// Giải mã chuỗi đã được mã hóa bởi [encrypt]
  String decrypt(String cipherText) {
    final bytes = base64Url.decode(cipherText);
    final iv = enc.IV(Uint8List.fromList(bytes.take(16).toList()));
    final cipherBytes = Uint8List.fromList(bytes.skip(16).toList());
    final encrypter = enc.Encrypter(enc.AES(_aesKey, mode: enc.AESMode.cbc));
    return encrypter.decrypt(enc.Encrypted(cipherBytes), iv: iv);
  }

  /// Tạo HMAC-SHA256 signature để verify tính toàn vẹn của payload
  String sign(String data) {
    final key = utf8.encode('STEM_HMAC_SECRET_2024');
    final hmac = Hmac(sha256, key);
    final digest = hmac.convert(utf8.encode(data));
    return digest.toString();
  }

  /// Kiểm tra signature có khớp không
  bool verify(String data, String signature) {
    final expected = sign(data);
    return expected == signature;
  }

  /// Tạo nonce ngẫu nhiên (hex string)
  String generateNonce() {
    final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
