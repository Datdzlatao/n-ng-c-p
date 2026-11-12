// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  APP_THEME.DART — Material 3 Theme Configuration                         ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppTheme {
  AppTheme._();

  /// Dark theme premium — sử dụng làm theme chính của app
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      fontFamily: 'Inter',

      // ── Color Scheme ────────────────────────────────────────────────────────
      colorScheme: const ColorScheme.dark(
        primary:        AppColors.primary,
        secondary:      AppColors.accent,
        surface:        AppColors.surface,
        error:          AppColors.error,
        onPrimary:      Colors.white,
        onSecondary:    Colors.white,
        onSurface:      AppColors.textPrimary,
        onError:        Colors.white,
      ),

      // ── Scaffold ─────────────────────────────────────────────────────────────
      scaffoldBackgroundColor: AppColors.background,

      // ── AppBar ───────────────────────────────────────────────────────────────
      appBarTheme: const AppBarTheme(
        backgroundColor:    Colors.transparent,
        elevation:          0,
        scrolledUnderElevation: 0,
        iconTheme:          IconThemeData(color: AppColors.textPrimary),
        titleTextStyle: TextStyle(
          fontFamily: 'Inter',
          fontSize:   20,
          fontWeight: FontWeight.w600,
          color:      AppColors.textPrimary,
          letterSpacing: -0.3,
        ),
      ),

      // ── Card ─────────────────────────────────────────────────────────────────
      cardTheme: CardThemeData(
        color:     AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: AppColors.surfaceVariant, width: 1),
        ),
      ),

      // ── ElevatedButton ──────────────────────────────────────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation:       0,
          minimumSize:     const Size(double.infinity, 52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize:   16,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.2,
          ),
        ),
      ),

      // ── OutlinedButton ─────────────────────────────────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary, width: 1.5),
          minimumSize: const Size(double.infinity, 52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize:   16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // ── TextButton ─────────────────────────────────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryLight,
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize:   14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),

      // ── InputDecoration ─────────────────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled:          true,
        fillColor:       AppColors.surfaceVariant,
        hintStyle: const TextStyle(
          color:    AppColors.textHint,
          fontSize: 15,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide:   BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.surfaceHigh, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.error, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),

      // ── Divider ─────────────────────────────────────────────────────────────
      dividerTheme: const DividerThemeData(
        color:     AppColors.surfaceVariant,
        thickness: 1,
      ),

      // ── BottomNavigationBar ─────────────────────────────────────────────────
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor:       AppColors.surface,
        selectedItemColor:     AppColors.primary,
        unselectedItemColor:   AppColors.textHint,
        selectedLabelStyle:    TextStyle(fontFamily: 'Inter', fontWeight: FontWeight.w600, fontSize: 11),
        unselectedLabelStyle:  TextStyle(fontFamily: 'Inter', fontSize: 11),
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),

      // ── Chip ────────────────────────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor:   AppColors.surfaceVariant,
        selectedColor:     AppColors.primarySurface,
        labelStyle: const TextStyle(
          fontFamily: 'Inter',
          fontSize:   13,
          color:      AppColors.textSecondary,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
    );
  }
}
