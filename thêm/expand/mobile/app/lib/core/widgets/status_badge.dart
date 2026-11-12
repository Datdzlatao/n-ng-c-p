// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  STATUS_BADGE.DART — Badge hiển thị trạng thái điểm danh               ║
// ╚══════════════════════════════════════════════════════════════════════════╝

import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../../features/attendance/domain/entities/attendance_entity.dart';
import '../../features/dress_code/domain/entities/dress_code_result_entity.dart';

/// Badge hiển thị trạng thái điểm danh
class StatusBadge extends StatelessWidget {
  final AttendanceStatus status;
  final bool showLabel;
  final double fontSize;

  const StatusBadge({
    super.key,
    required this.status,
    this.showLabel = true,
    this.fontSize = 11,
  });

  @override
  Widget build(BuildContext context) {
    final (color, label, icon) = switch (status) {
      AttendanceStatus.present => (AppColors.success, 'Có mặt', Icons.check_circle_rounded),
      AttendanceStatus.late    => (AppColors.warning, 'Trễ',    Icons.schedule_rounded),
      AttendanceStatus.absent  => (AppColors.error,   'Vắng',   Icons.cancel_rounded),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: fontSize + 2),
          if (showLabel) ...[
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: fontSize,
                fontWeight: FontWeight.w600,
                fontFamily: 'Inter',
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Badge hiển thị phương thức điểm danh (QR/Face)
class AttendanceMethodBadge extends StatelessWidget {
  final AttendanceMethod method;

  const AttendanceMethodBadge({super.key, required this.method});

  @override
  Widget build(BuildContext context) {
    final isQr = method == AttendanceMethod.qrCode;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: (isQr ? AppColors.qrPrimary : AppColors.accent).withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isQr ? Icons.qr_code_rounded : Icons.face_rounded,
            color: isQr ? AppColors.qrPrimary : AppColors.accent,
            size: 13,
          ),
          const SizedBox(width: 4),
          Text(
            isQr ? 'QR' : 'Face',
            style: TextStyle(
              color: isQr ? AppColors.qrPrimary : AppColors.accent,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              fontFamily: 'Inter',
            ),
          ),
        ],
      ),
    );
  }
}

/// Badge hiển thị kết quả kiểm tra trang phục
class DressCodeBadge extends StatelessWidget {
  final DressCodeStatus status;

  const DressCodeBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final isOk = status == DressCodeStatus.correct;
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: (isOk ? AppColors.dressOk : AppColors.dressViolate).withOpacity(0.15),
        shape: BoxShape.circle,
        border: Border.all(
          color: (isOk ? AppColors.dressOk : AppColors.dressViolate).withOpacity(0.5),
        ),
      ),
      child: Icon(
        isOk ? Icons.checkroom_rounded : Icons.warning_rounded,
        color: isOk ? AppColors.dressOk : AppColors.dressViolate,
        size: 14,
      ),
    );
  }
}
