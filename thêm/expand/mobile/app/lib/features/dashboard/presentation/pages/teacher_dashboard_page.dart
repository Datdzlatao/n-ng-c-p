import 'package:flutter/material.dart';

class TeacherDashboardPage extends StatelessWidget {
  const TeacherDashboardPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Dashboard Giáo Viên', style: TextStyle(color: Colors.white)),
        actions: [
          IconButton(icon: const Icon(Icons.logout, color: Colors.white), onPressed: () {})
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildStatCard('Tổng hôm nay', '45', Icons.people, Colors.blue),
                const SizedBox(width: 8),
                _buildStatCard('Đúng giờ', '40', Icons.check_circle, Colors.green),
                const SizedBox(width: 8),
                _buildStatCard('Vắng mặt', '5', Icons.cancel, Colors.red),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Tạo Phiên Điểm Danh', style: TextStyle(color: Colors.white, fontSize: 16)),
              ),
            ),
            const SizedBox(height: 24),
            const Text('Danh sách điểm danh trực tiếp', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: 10,
                itemBuilder: (context, index) {
                  return ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.person)),
                    title: const Text('Học sinh A', style: TextStyle(color: Colors.white)),
                    subtitle: const Text('08:05 AM', style: TextStyle(color: Colors.grey)),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Chip(label: Text('QR', style: TextStyle(fontSize: 10)), backgroundColor: Colors.purple),
                        const SizedBox(width: 4),
                        const Icon(Icons.check_circle, color: Colors.green),
                      ],
                    ),
                  );
                },
              ),
            ),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                child: const Text('Kết thúc Phiên', style: TextStyle(color: Colors.white)),
              ),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
        child: Column(
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
            Text(title, style: const TextStyle(color: Colors.grey, fontSize: 12), textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
