import './globals.css';
import type { Metadata } from 'next';
import Dashboard from '@/components/Dashboard';
import CustomerPage from '@/components/CustomerPage';
import ProductPage from '@/components/ProductPage';

export const metadata: Metadata = {
  title: '德航智能 · 经营驾驶舱',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <div className="min-h-screen">
          {/* 页面 1: 首页 Dashboard */}
          <Dashboard />

          {/* 页面 2: 客户分析 */}
          <CustomerPage />

          {/* 页面 3: 产品分析 */}
          <ProductPage />
        </div>
      </body>
    </html>
  );
}
