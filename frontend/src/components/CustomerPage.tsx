'use client';

import { useAPI, fmtMoney } from '@/lib/api';
import type { CustomerData, SalesmanData, Period } from '@/types';
import ReactECharts from 'echarts-for-react';
import { useMemo, useState } from 'react';

export default function CustomerPage({ period, trendMode }: { period: Period; trendMode: 'single' | 'multi' }) {
  const now = new Date();
  const year = period.year;
  const isCurrent = year === now.getFullYear();
  const isMulti = trendMode === 'multi';
  const ym = `year=${year}`;
  const cm = `mode=${trendMode}`;
  const periodLabel = isMulti ? `${year - 2}年-至今(近三年)` : (isCurrent ? `${year}年(1-${now.getMonth() + 1}月)` : `${year}年`);
  const { data } = useAPI<CustomerData>(`/dashboard/customers/top?limit=20&${isMulti ? cm : ym}`);
  const { data: salesmen } = useAPI<SalesmanData>(`/dashboard/salesman?${ym}`);
  const [showSalesman, setShowSalesman] = useState(false);

  const paretoOption = useMemo(() => {
    if (!data) return {};
    const custs = data.customers;
    return {
      grid: { left: 100, right: 60, top: 30, bottom: 60 },
      tooltip: { trigger: 'axis', formatter: (p: any) => {
        const i = p[0].dataIndex;
        return `${custs[i].name}<br>金额: ${fmtMoney(custs[i].amount)}<br>占比: ${custs[i].pct}%<br>累计: ${custs[i].cum_pct}%`;
      }},
      xAxis: { type: 'category', data: custs.map(c => c.name.length > 6 ? c.name.slice(0,5)+'…' : c.name),
        axisLabel: { rotate: 40, fontSize: 10 } },
      yAxis: [
        { type: 'value', name: '金额', axisLabel: { formatter: (v:number) => fmtMoney(v), fontSize: 10 } },
        { type: 'value', name: '累计%', max: 100, axisLabel: { formatter: '{value}%', fontSize: 10 } },
      ],
      series: [
        { type: 'bar', data: custs.map(c => Math.round(c.amount)),
          itemStyle: { color: '#3b82f6', borderRadius: [4,4,0,0] }, barMaxWidth: 28 },
        { type: 'line', yAxisIndex: 1, data: custs.map(c => c.cum_pct), smooth: true,
          itemStyle: { color: '#ef4444' }, lineStyle: { width: 2 } },
      ],
    };
  }, [data]);

  const top20Count = data?.top_customers ?? 0;
  const totalCustomers = data?.total_customers ?? 0;
  const countRatio = totalCustomers > 0 ? (top20Count / totalCustomers) * 100 : 0;

  return (
    <section className="min-h-screen p-6 max-w-7xl mx-auto bg-bg">
      <h2 className="text-lg font-bold mb-4">客户分析</h2>

      {/* TOP20 集中度 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">TOP20 客户集中度 · {periodLabel}</h3>
          <div className="text-sm text-sub">
            共 <b className="text-txt">{totalCustomers}</b> 家客户，TOP20 占客户数量 <b className="text-txt">{countRatio.toFixed(1)}%</b>
          </div>
        </div>
        <ReactECharts option={paretoOption} style={{ height: '360px' }} />
      </div>

      {/* 客户列表 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <h3 className="text-sm font-medium text-sub mb-2">客户排行 TOP20 · {periodLabel}</h3>
          <table className="w-full text-sm">
          <thead><tr className="text-sub border-b border-line">
            <th className="text-left py-2">#</th><th className="text-left">客户</th>
            <th className="text-left">省份</th><th className="text-right">金额</th>
            <th className="text-right">应收(万元)</th><th className="text-right">占比</th><th className="text-right">累计</th>
          </tr></thead>
          <tbody>
            {data?.customers.map((c, i) => (
              <tr key={c.name} className="border-b border-line hover:bg-bg">
                <td className="py-2 text-sub">{i + 1}</td>
                <td className="truncate max-w-[200px]" title={c.name}>{c.name}</td>
                <td className="text-sub">{c.province}</td>
                <td className="text-right font-medium">{fmtMoney(c.amount)}</td>
                <td className="text-right text-down font-medium">{fmtMoney(c.receivable)}</td>
                <td className="text-right">{c.pct}%</td>
                <td className="text-right text-sub">{c.cum_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 业务员分析（悬停展开） */}
      <div className="bg-white rounded-xl border border-line p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">业务员分析</h3>
          <button onClick={() => setShowSalesman(!showSalesman)}
            className="text-xs text-brand hover:underline">
            {showSalesman ? '收起' : '展开'}
          </button>
        </div>
        {showSalesman && (
          <table className="w-full text-sm">
            <thead><tr className="text-sub border-b border-line">
              <th className="text-left py-2">业务员</th><th className="text-left">部门</th>
              <th className="text-right">销售额</th><th className="text-right">应收</th>
            </tr></thead>
            <tbody>
              {salesmen?.items.map(s => (
                <tr key={s.name} className="border-b border-line">
                  <td className="py-1">{s.name}</td>
                  <td className="text-sub">{s.dept}</td>
                  <td className="text-right font-medium">{fmtMoney(s.sales)}</td>
                  <td className="text-right text-down">{fmtMoney(s.receivable)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!showSalesman && <p className="text-sub text-xs">点击「展开」查看业务员销售额和应收明细</p>}
      </div>
    </section>
  );
}
