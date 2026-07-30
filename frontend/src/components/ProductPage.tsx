'use client';

import { useAPI, fmtMoney } from '@/lib/api';
import type { ProductStructureData, GrowthData } from '@/types';
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';

export default function ProductPage() {
  const year = new Date().getFullYear();
  const { data: productYear } = useAPI<ProductStructureData>('/dashboard/product-structure?mode=year');
  const { data: growth } = useAPI<GrowthData>(`/dashboard/growth?year=${year}`);

  // 产品大类趋势（需要后端单独接口，这里先用增长数据代替）
  const trendOption = useMemo(() => {
    if (!growth) return {};
    const items = growth.items;
    return {
      grid: { left: 100, right: 30, top: 20, bottom: 30 },
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'category', data: ['去年', '今年'] },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      series: items.slice(0, 6).map((item, i) => {
        const colors = ['#15803d', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
        return {
          name: item.category, type: 'bar', barMaxWidth: 24,
          data: [item.previous, item.current],
          itemStyle: { color: colors[i] },
        };
      }),
    };
  }, [growth]);

  // 增长/下降分析
  const growthOption = useMemo(() => {
    if (!growth) return {};
    const items = growth.items.filter(i => i.diff !== 0).sort((a, b) => b.diff - a.diff);
    return {
      grid: { left: 100, right: 30, top: 20, bottom: 30 },
      tooltip: { formatter: (p: any) => {
        const i = items[p.dataIndex];
        return `${i.category}<br>变动: ${fmtMoney(i.diff)}<br>今年: ${fmtMoney(i.current)}<br>去年: ${fmtMoney(i.previous)}`;
      }},
      xAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      yAxis: { type: 'category', data: items.map(i => i.category), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: items.map(i => ({
          value: Math.round(i.diff),
          itemStyle: { color: i.diff >= 0 ? '#16a34a' : '#ef4444', borderRadius: i.diff >= 0 ? [0,4,4,0] : [4,0,0,4] },
        })),
        barMaxWidth: 18,
      }],
    };
  }, [growth]);

  // 产品结构环形图
  const structureOption = useMemo(() => {
    if (!productYear) return {};
    return {
      tooltip: { formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['45%', '70%'],
        data: productYear.items.map(i => ({ name: i.category, value: i.amount })),
        label: { fontSize: 11, formatter: '{b}\n{d}%' },
      }],
    };
  }, [productYear]);

  return (
    <section className="min-h-screen p-6 max-w-7xl mx-auto bg-bg">
      <h2 className="text-lg font-bold mb-4">产品分析</h2>

      {/* 产品大类趋势 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品大类趋势 · {year}年 vs 去年</h3>
        <ReactECharts option={trendOption} style={{ height: '300px' }} />
      </div>

      {/* 增长/下降贡献 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品增长 / 下降贡献</h3>
        <ReactECharts option={growthOption} style={{ height: '360px' }} />
      </div>

      {/* 产品结构变化 */}
      <div className="bg-white rounded-xl border border-line p-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品结构 · {year}年累计</h3>
        <ReactECharts option={structureOption} style={{ height: '320px' }} />
      </div>
    </section>
  );
}
