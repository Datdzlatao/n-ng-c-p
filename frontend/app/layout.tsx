import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Nông Trại Thông Minh - Hệ Thống Quản Lý Toàn Diện',
  description: 'Hệ thống quản lý chuồng trại, cây trồng, vi khí hậu và chấm công điểm danh nhân viên bằng trí tuệ nhân tạo',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-fb-bg min-h-screen text-fb-text antialiased">
        {children}
      </body>
    </html>
  );
}
