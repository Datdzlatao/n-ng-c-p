// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  GRADIENT_BUTTON.DART — Custom button với gradient background            ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// Button với gradient đẹp, dùng xuyên suốt app
/// Hỗ trợ loading state, disabled state, và custom gradient
class GradientButton extends StatefulWidget {
  final String text;
  final VoidCallback? onPressed; // null = disabled
  final bool isLoading;
  final LinearGradient? gradient;
  final double height;
  final double borderRadius;
  final IconData? icon;
  final TextStyle? textStyle;

  const GradientButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.gradient,
    this.height = 52,
    this.borderRadius = 14,
    this.icon,
    this.textStyle,
  });

  @override
  State<GradientButton> createState() => _GradientButtonState();
}

class _GradientButtonState extends State<GradientButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    );
    _scaleAnim = Tween<double>(begin: 1.0, end: 0.97).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDisabled = widget.onPressed == null || widget.isLoading;
    final gradient = widget.gradient ?? AppColors.primaryGradient;

    return GestureDetector(
      onTapDown: isDisabled ? null : (_) => _controller.forward(),
      onTapUp: isDisabled ? null : (_) {
        _controller.reverse();
        widget.onPressed?.call();
      },
      onTapCancel: () => _controller.reverse(),
      child: ScaleTransition(
        scale: _scaleAnim,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: isDisabled ? 0.6 : 1.0,
          child: Container(
            height: widget.height,
            width: double.infinity,
            decoration: BoxDecoration(
              gradient: isDisabled
                  ? null
                  : gradient,
              color: isDisabled ? AppColors.surfaceVariant : null,
              borderRadius: BorderRadius.circular(widget.borderRadius),
              boxShadow: isDisabled
                  ? null
                  : [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.35),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
            ),
            child: Center(
              child: widget.isLoading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: Colors.white,
                      ),
                    )
                  : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (widget.icon != null) ...[
                          Icon(widget.icon, color: Colors.white, size: 20),
                          const SizedBox(width: 8),
                        ],
                        Text(
                          widget.text,
                          style: widget.textStyle ??
                              const TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                                letterSpacing: 0.3,
                              ),
                        ),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
