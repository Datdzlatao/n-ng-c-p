import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SmartFarmer - Bảng Tin Nông Trại Thông Minh',
  description: 'Hệ thống Quản lý Nông Trại phong cách Facebook Feed với AI Agent Messenger',
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
