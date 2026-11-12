import 'package:flutter/material.dart';

class AdminDashboardPage extends StatelessWidget {
  const AdminDashboardPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Admin Dashboard', style: TextStyle(color: Colors.white)),
        actions: [
          IconButton(icon: const Icon(Icons.logout, color: Colors.white), onPressed: () {})
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          children: [
            _buildActionCard('Quản lý Học sinh', Icons.school, Colors.blue),
            _buildActionCard('Quản lý Giáo viên', Icons.person_outline, Colors.orange),
            _buildActionCard('Báo cáo', Icons.bar_chart, Colors.green),
            _buildActionCard('Đăng ký Khuôn mặt', Icons.face, Colors.purple),
            _buildActionCard('Thống kê', Icons.pie_chart, Colors.teal),
            _buildActionCard('Cài đặt', Icons.settings, Colors.grey),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard(String title, IconData icon, Color color) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [color.withOpacity(0.7), color]),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: Colors.white, size: 40),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
