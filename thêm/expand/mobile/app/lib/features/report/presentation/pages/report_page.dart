import 'package:flutter/material.dart';
// import 'package:fl_chart/fl_chart.dart';

class ReportPage extends StatelessWidget {
  const ReportPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Báo Cáo Điểm Danh', style: TextStyle(color: Colors.white)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                    child: const Text('Từ: 01/01/2024', style: TextStyle(color: Colors.white)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                    child: const Text('Đến: 31/01/2024', style: TextStyle(color: Colors.white)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Chọn lớp: Lớp 10A1', style: TextStyle(color: Colors.white)),
                  Icon(Icons.arrow_drop_down, color: Colors.white),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const Text('Tổng quan', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            const Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(children: [Text('95%', style: TextStyle(color: Colors.green, fontSize: 24, fontWeight: FontWeight.bold)), Text('Có mặt', style: TextStyle(color: Colors.grey))]),
                Column(children: [Text('3%', style: TextStyle(color: Colors.orange, fontSize: 24, fontWeight: FontWeight.bold)), Text('Đi trễ', style: TextStyle(color: Colors.grey))]),
                Column(children: [Text('2%', style: TextStyle(color: Colors.red, fontSize: 24, fontWeight: FontWeight.bold)), Text('Vắng', style: TextStyle(color: Colors.grey))]),
              ],
            ),
            const SizedBox(height: 32),
            const Text('Biểu đồ (Placeholder)', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Expanded(
              child: Container(
                color: Colors.white.withOpacity(0.05),
                child: const Center(child: Text('BarChart goes here', style: TextStyle(color: Colors.grey))),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.table_chart),
                    label: const Text('Xuất Excel'),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.picture_as_pdf),
                    label: const Text('Xuất PDF'),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}
