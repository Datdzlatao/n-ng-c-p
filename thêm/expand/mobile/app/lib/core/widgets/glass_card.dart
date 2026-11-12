// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  GLASS_CARD.DART — Glassmorphism card widget                             ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// Card với hiệu ứng kính mờ (glassmorphism) — dùng trong UI premium
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final BorderRadius? borderRadius;
  final double blurSigma;
  final double opacity;
  final Color? borderColor;
  final VoidCallback? onTap;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius,
    this.blurSigma = 12,
    this.opacity = 0.08,
    this.borderColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? BorderRadius.circular(20);

    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: radius,
        child: BackdropFilter(
          // Hiệu ứng blur nền
          filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
          child: Container(
            padding: padding ?? const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(opacity),
              borderRadius: radius,
              border: Border.all(
                color: borderColor ?? Colors.white.withOpacity(0.12),
                width: 1,
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}

/// Card với gradient màu sắc nổi bật
class GradientCard extends StatelessWidget {
  final Widget child;
  final LinearGradient gradient;
  final EdgeInsetsGeometry? padding;
  final BorderRadius? borderRadius;
  final VoidCallback? onTap;
  final List<BoxShadow>? shadows;

  const GradientCard({
    super.key,
    required this.child,
    required this.gradient,
    this.padding,
    this.borderRadius,
    this.onTap,
    this.shadows,
  });

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? BorderRadius.circular(16);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: padding ?? const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: gradient,
          borderRadius: radius,
          boxShadow: shadows ??
              [
                BoxShadow(
                  color: gradient.colors.first.withOpacity(0.30),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
        ),
        child: child,
      ),
    );
  }
}
