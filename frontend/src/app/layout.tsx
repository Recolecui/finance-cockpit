import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '德航智能 · 经营驾驶舱',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
