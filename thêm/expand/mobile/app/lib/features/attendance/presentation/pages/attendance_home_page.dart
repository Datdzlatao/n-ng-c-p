import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../bloc/attendance_bloc.dart';
import '../bloc/attendance_state.dart';

class AttendanceHomePage extends StatelessWidget {
  const AttendanceHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Xin chào, Học sinh!'),
        actions: const [
          Padding(
            padding: EdgeInsets.all(8.0),
            child: CircleAvatar(
              backgroundColor: Color(0xFF6366F1),
              child: Icon(Icons.person, color: Colors.white),
            ),
          )
        ],
      ),
      body: BlocBuilder<AttendanceBloc, AttendanceState>(
        builder: (context, state) {
          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Hôm nay: ${DateTime.now().toString().split(' ')[0]}',
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.warning, color: Colors.amber, size: 32),
                      SizedBox(width: 16),
                      Expanded(
                        child: Text(
                          'Bạn chưa điểm danh hôm nay',
                          style: TextStyle(color: Colors.white, fontSize: 16),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          // Navigate to QR Scanner
                        },
                        child: Container(
                          height: 120,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(colors: [Color(0xFF9333EA), Color(0xFF4F46E5)]),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.qr_code, color: Colors.white, size: 40),
                              SizedBox(height: 8),
                              Text('Quét QR', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          // Navigate to Face ID
                        },
                        child: Container(
                          height: 120,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)]),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.face, color: Colors.white, size: 40),
                              SizedBox(height: 8),
                              Text('Nhận Diện Mặt', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 32),
                const Text('Lịch sử gần đây', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                Expanded(
                  child: ListView.builder(
                    itemCount: 5,
                    itemBuilder: (context, index) {
                      return ListTile(
                        leading: const Icon(Icons.qr_code, color: Colors.grey),
                        title: Text('Điểm danh ngày ${DateTime.now().subtract(Duration(days: index)).toString().split(' ')[0]}', style: const TextStyle(color: Colors.white)),
                        trailing: const Chip(
                          label: Text('Có mặt', style: TextStyle(color: Colors.white)),
                          backgroundColor: Colors.green,
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          );
        },
      ),
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: const Color(0xFF1A1A2E),
        unselectedItemColor: Colors.grey,
        selectedItemColor: const Color(0xFF6366F1),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Trang chủ'),
          BottomNavigationBarItem(icon: Icon(Icons.history), label: 'Lịch sử'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Cá nhân'),
        ],
      ),
    );
  }
}
