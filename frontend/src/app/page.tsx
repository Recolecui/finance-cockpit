'use client';

import { useEffect, useState } from 'react';
import Dashboard from '@/components/Dashboard';
import CustomerPage from '@/components/CustomerPage';
import ProductPage from '@/components/ProductPage';

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) {
      setToken(t);
      setName(localStorage.getItem('name') || 'admin');
    }
  }, []);

  async function doLogin(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const res = await fetch('/api/auth/login/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (!res.ok) {
        setErr('用户名或密码错误');
        return;
      }
      const data = await res.json();
      localStorage.setItem('token', data.token);
      localStorage.setItem('name', data.name);
      setToken(data.token);
      setName(data.name);
    } catch {
      setErr('登录请求失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('name');
    setToken(null);
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <form onSubmit={doLogin} className="bg-white p-8 rounded-2xl shadow-md w-80 space-y-4">
          <h1 className="text-xl font-semibold text-center text-slate-800">德航智能 · 经营驾驶舱</h1>
          <div>
            <input
              value={u} onChange={(e) => setU(e.target.value)} placeholder="用户名"
              className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500"
              autoFocus
            />
          </div>
          <div>
            <input
              value={p} onChange={(e) => setP(e.target.value)} type="password" placeholder="密码"
              className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500"
            />
          </div>
          {err && <p className="text-sm text-red-500 text-center">{err}</p>}
          <button
            type="submit" disabled={busy}
            className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
          >
            {busy ? '登录中…' : '登录'}
          </button>
          <p className="text-xs text-slate-400 text-center">默认账号 admin / admin123</p>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
        <div className="max-w-7xl mx-auto px-6 h-12 flex items-center justify-between">
          <span className="font-semibold text-slate-700">德航智能 · 经营驾驶舱</span>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <span>{name}</span>
            <button onClick={logout} className="text-blue-600 hover:underline">退出</button>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-10">
        <Dashboard />
        <CustomerPage />
        <ProductPage />
      </main>
    </div>
  );
}
