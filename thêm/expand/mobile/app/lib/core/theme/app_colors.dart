// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  APP_COLORS.DART — Bảng màu sắc của ứng dụng                            ║
// ║  Design system: Dark mode với accent màu xanh dương-tím (edu theme)     ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';

class AppColors {
  AppColors._(); // Ngăn khởi tạo instance

  // ── Primary Palette — Indigo Blue ──────────────────────────────────────────
  static const Color primary        = Color(0xFF6366F1); // Indigo 500
  static const Color primaryLight   = Color(0xFF818CF8); // Indigo 400
  static const Color primaryDark    = Color(0xFF4F46E5); // Indigo 600
  static const Color primarySurface = Color(0x1A6366F1); // Indigo 10% opacity

  // ── Accent — Cyan (success, face recognition) ──────────────────────────────
  static const Color accent         = Color(0xFF06B6D4); // Cyan 500
  static const Color accentLight    = Color(0xFF22D3EE); // Cyan 400
  static const Color accentSurface  = Color(0x1A06B6D4); // Cyan 10%

  // ── Background (Dark theme layers) ─────────────────────────────────────────
  static const Color background     = Color(0xFF0F0F1A); // Nền sâu nhất
  static const Color surface        = Color(0xFF1A1A2E); // Card/container
  static const Color surfaceVariant = Color(0xFF252540); // Surface nổi hơn
  static const Color surfaceHigh    = Color(0xFF2D2D50); // Surface cao nhất

  // ── Status Colors ──────────────────────────────────────────────────────────
  static const Color success    = Color(0xFF10B981); // Xanh lá — điểm danh OK
  static const Color warning    = Color(0xFFF59E0B); // Vàng — cảnh báo
  static const Color error      = Color(0xFFEF4444); // Đỏ — lỗi / vi phạm
  static const Color info       = Color(0xFF3B82F6); // Xanh — thông tin

  // ── QR Code theme colors ────────────────────────────────────────────────────
  static const Color qrPrimary  = Color(0xFF8B5CF6); // Tím — QR module
  static const Color qrAccent   = Color(0xFFA78BFA); // Tím nhạt

  // ── Face Recognition colors ─────────────────────────────────────────────────
  static const Color faceOk       = Color(0xFF10B981); // Nhận diện thành công
  static const Color faceWarning  = Color(0xFFF59E0B); // Nhận ra nhưng chưa điểm danh
  static const Color faceStranger = Color(0xFFEF4444); // Người lạ

  // ── Dress Code colors ───────────────────────────────────────────────────────
  static const Color dressOk      = Color(0xFF10B981); // Đúng trang phục
  static const Color dressViolate = Color(0xFFEF4444); // Sai trang phục

  // ── Text Colors ────────────────────────────────────────────────────────────
  static const Color textPrimary   = Color(0xFFF1F5F9); // Chữ chính
  static const Color textSecondary = Color(0xFF94A3B8); // Chữ phụ
  static const Color textHint      = Color(0xFF475569);  // Placeholder

  // ── Gradients ──────────────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF6366F1), Color(0xFF06B6D4)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFF0F0F1A), Color(0xFF1A1A2E)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient successGradient = LinearGradient(
    colors: [Color(0xFF10B981), Color(0xFF06B6D4)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient errorGradient = LinearGradient(
    colors: [Color(0xFFEF4444), Color(0xFFEC4899)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ── Glassmorphism effect helper ─────────────────────────────────────────────
  /// Màu nền cho hiệu ứng kính mờ (glassmorphism)
  static Color glassColor(double opacity) =>
      Colors.white.withOpacity(opacity);
}
