'use client';

import { useAPI, fmtMoney, fmtNum } from '@/lib/api';
import type { KPI, TrendData, RegionData, ProductStructureData, GrowthData } from '@/types';
import ReactECharts from 'echarts-for-react';
import { useState, useMemo } from 'react';

export default function Dashboard() {
  const [period, setPeriod] = useState<{year?: number; month?: number}>({});
  const [regionMetric, setRegionMetric] = useState('sales');
  const [productMode, setProductMode] = useState('month');

  const year = period.year;
  const month = period.month;
  const kpiPath = year ? `/dashboard/kpi?year=${year}${month ? `&month=${month}` : ''}` : '/dashboard/kpi';
  const regionPath = `/dashboard/region?${year ? `year=${year}&` : ''}metric=${regionMetric}`;
  const productPath = `/dashboard/product-structure?mode=${productMode}`;
  const growthPath = `/dashboard/growth?year=${year || new Date().getFullYear()}`;

  const { data: kpi } = useAPI<KPI>(kpiPath);
  const { data: trend } = useAPI<TrendData>('/dashboard/trend?months=36');
  const { data: region } = useAPI<RegionData>(regionPath);
  const { data: product } = useAPI<ProductStructureData>(productPath);
  const { data: growth } = useAPI<GrowthData>(growthPath);

  // 销售趋势图
  const trendOption = useMemo(() => {
    if (!trend) return {};
    const months = trend.months.map(m => m.month);
    return {
      grid: { left: 70, right: 30, top: 40, bottom: 30 },
      tooltip: { trigger: 'axis' },
      legend: { data: ['销售额', '回款'], top: 0 },
      xAxis: { type: 'category', data: months, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      series: [
        { name: '销售额', type: 'line', data: trend.months.map(m => m.sales), smooth: true,
          itemStyle: { color: '#15803d' }, areaStyle: { opacity: 0.08 } },
        { name: '回款', type: 'line', data: trend.months.map(m => m.receive), smooth: true,
          itemStyle: { color: '#3b82f6' } },
      ],
    };
  }, [trend]);

  // 产品环形图
  const productOption = useMemo(() => {
    if (!product) return {};
    return {
      tooltip: { formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['45%', '70%'],
        data: product.items.map(i => ({ name: i.category, value: i.amount })),
        label: { fontSize: 11, formatter: '{b}\n{d}%' },
      }],
    };
  }, [product]);

  // 增长瀑布图
  const growthOption = useMemo(() => {
    if (!growth) return {};
    const items = growth.items.filter(i => i.diff !== 0);
    return {
      grid: { left: 100, right: 30, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis', formatter: (p: any) => {
        const i = items[p[0].dataIndex];
        return `${i.category}<br>当年: ${fmtMoney(i.current)}<br>去年: ${fmtMoney(i.previous)}<br>变动: ${fmtMoney(i.diff)}`;
      }},
      xAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      yAxis: { type: 'category', data: items.map(i => i.category), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: items.map(i => ({
          value: i.diff,
          itemStyle: { color: i.diff >= 0 ? '#16a34a' : '#ef4444' },
        })),
        barMaxWidth: 18,
      }],
    };
  }, [growth]);

  return (
    <section className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* KPI 卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="销售额" value={kpi ? fmtMoney(kpi.sales) : '...'} />
        <KpiCard label="回款" value={kpi ? fmtMoney(kpi.receive) : '...'} />
        <KpiCard label="应收余额" value={kpi ? fmtMoney(kpi.receivable) : '...'} />
        <KpiCard label="出库单数" value={kpi ? fmtNum(kpi.outstock_count) : '...'} />
      </div>

      {/* 销售趋势 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-6">
        <h3 className="text-sm font-medium text-sub mb-2">销售趋势 · 近36个月</h3>
        <ReactECharts option={trendOption} style={{ height: '280px' }} />
      </div>

      {/* 区域地图 + 指标切换 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">区域分布</h3>
          <div className="flex gap-1">
            {['sales', 'receive', 'receivable'].map(m => (
              <button key={m} onClick={() => setRegionMetric(m)}
                className={`px-3 py-1 text-xs rounded ${regionMetric === m ? 'bg-brand text-white' : 'bg-bg text-sub'}`}>
                {m === 'sales' ? '销售额' : m === 'receive' ? '回款' : '应收'}
              </button>
            ))}
          </div>
        </div>
        <RegionTable data={region} metric={regionMetric} />
      </div>

      {/* 产品结构 + 增长分析 */}
      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-line p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-sub">产品结构</h3>
            <div className="flex gap-1">
              {['month', 'year'].map(m => (
                <button key={m} onClick={() => setProductMode(m)}
                  className={`px-3 py-1 text-xs rounded ${productMode === m ? 'bg-brand text-white' : 'bg-bg text-sub'}`}>
                  {m === 'month' ? '当月' : '当年'}
                </button>
              ))}
            </div>
          </div>
          <ReactECharts option={productOption} style={{ height: '300px' }} />
        </div>

        <div className="bg-white rounded-xl border border-line p-4">
          <h3 className="text-sm font-medium text-sub mb-2">增长贡献分析 · {year || new Date().getFullYear()}年 vs 去年</h3>
          <ReactECharts option={growthOption} style={{ height: '300px' }} />
        </div>
      </div>
    </section>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border border-line p-4">
      <div className="text-xs text-sub">{label}</div>
      <div className="text-xl font-bold mt-1">{value}</div>
    </div>
  );
}

function RegionTable({ data, metric }: { data: RegionData | undefined; metric: string }) {
  if (!data) return <div className="text-sub text-sm">加载中...</div>;
  const sorted = [...data.regions].sort((a, b) => b.value - a.value);
  return (
    <table className="w-full text-sm">
      <thead><tr className="text-sub"><th className="text-left py-1">省份</th><th className="text-right py-1">
        {metric === 'sales' ? '销售额' : metric === 'receive' ? '回款' : '应收'}
      </th></tr></thead>
      <tbody>
        {sorted.slice(0, 15).map(r => (
          <tr key={r.province} className="border-t border-line">
            <td className="py-1">{r.province}</td>
            <td className="text-right py-1 font-medium">{fmtMoney(r.value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
