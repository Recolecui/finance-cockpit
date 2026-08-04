'use client';

import { useAPI, fmtMoney, SERIES_COLORS } from '@/lib/api';
import type { ProductStructureYearData, GrowthData, Period } from '@/types';
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';

export default function ProductPage({ period }: { period: Period }) {
  const now = new Date();
  const year = period.year;
  const ym = `year=${year}`;
  const isCurrent = year === now.getFullYear();
  const periodLabel = isCurrent ? `${year}年(1-${now.getMonth() + 1}月)` : `${year}年`;
  // 产品结构固定展示 2024/2025/2026 三年
  const structureYears = '2024,2025,2026';
  const { data: productYears } = useAPI<ProductStructureYearData>(`/dashboard/product-structure/years?years=${structureYears}`);
  const { data: growth } = useAPI<GrowthData>(`/dashboard/growth?year=${year}`);

  // 产品大类趋势（固定 2024/2025/2026 三年分组柱状图，不随年份选择变化）
  const trendOption = useMemo(() => {
    if (!productYears) return {};
    const years = ['2024', '2025', '2026'];
    const cats = new Set<string>();
    years.forEach(y => (productYears.years[y]?.items ?? []).forEach(i => cats.add(i.category)));
    const categories = Array.from(cats);
    return {
      grid: { left: 100, right: 30, top: 30, bottom: 30 },
      tooltip: { trigger: 'axis', formatter: (p: any) => {
        const lines = p.map((s: any) => `${s.seriesName}: ${fmtMoney(s.value)}`);
        return `${p[0].axisValue}<br>` + lines.join('<br>');
      }},
      legend: { top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'category', data: years },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      series: categories.map(cat => ({
        name: cat, type: 'bar', barMaxWidth: 24,
        data: years.map(y => {
          const it = (productYears.years[y]?.items ?? []).find(i => i.category === cat);
          return Math.round(it ? it.amount : 0);
        }),
        itemStyle: { color: SERIES_COLORS[cat] || '#94a3b8' },
        label: { show: true, position: 'top', formatter: (p: any) => fmtMoney(p.value), fontSize: 9, color: '#475569' },
      })),
    };
  }, [productYears]);

  // 增长/下降分析（纵坐标固定顺序：从下到上 PPC→TPC→PDA→PC→IPC→PDS→配件→外购品）
  const growthOption = useMemo(() => {
    if (!growth) return {};
    const SERIES_ORDER = ["PPC", "TPC", "PDA", "PC", "IPC", "PDS", "配件", "外购品"];
    const byCat: Record<string, any> = {};
    growth.items.forEach(i => { byCat[i.category] = i; });
    const data = SERIES_ORDER.map(cat => {
      const i = byCat[cat];
      const diff = i ? i.diff : 0;
      return {
        value: Math.round(diff),
        itemStyle: { color: diff >= 0 ? '#16a34a' : '#ef4444', borderRadius: diff >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] },
        label: { show: true, position: diff >= 0 ? 'right' : 'left', formatter: (params: any) => fmtMoney(params.value), fontSize: 10, color: '#475569' },
      };
    });
    return {
      grid: { left: 100, right: 30, top: 20, bottom: 30 },
      tooltip: { formatter: (p: any) => {
        const i = byCat[SERIES_ORDER[p.dataIndex]];
        if (!i) return `${SERIES_ORDER[p.dataIndex]}<br>变动: ¥0`;
        return `${i.category}<br>变动: ${fmtMoney(i.diff)}<br>今年: ${fmtMoney(i.current)}<br>去年: ${fmtMoney(i.previous)}`;
      }},
      xAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      yAxis: { type: 'category', data: SERIES_ORDER, axisLabel: { fontSize: 11 } },
      series: [{ type: 'bar', data, barMaxWidth: 18 }],
    };
  }, [growth]);

  // 三年产品结构环形图（按年份分别生成 option）
  const structureOptions = useMemo(() => {
    if (!productYears) return {};
    const opts: Record<string, any> = {};
    Object.entries(productYears.years).forEach(([y, d]) => {
      opts[y] = {
        title: { text: `${y}年`, left: 'center', top: 0, textStyle: { fontSize: 13, color: '#475569' } },
        tooltip: { formatter: '{b}: {c} ({d}%)' },
        series: [{
          type: 'pie', radius: ['40%', '65%'], center: ['50%', '55%'],
          data: d.items.map(i => ({
            name: i.category, value: i.amount,
            itemStyle: { color: SERIES_COLORS[i.category] || '#94a3b8' },
          })),
          label: { fontSize: 10, formatter: '{b}\n{d}%' },
        }],
      };
    });
    return opts;
  }, [productYears]);

  return (
    <section className="min-h-screen p-6 max-w-7xl mx-auto bg-bg">
      <h2 className="text-lg font-bold mb-4">产品分析</h2>

      {/* 产品大类趋势 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品大类趋势 · 2024–2026</h3>
        <ReactECharts option={trendOption} style={{ height: '300px' }} />
      </div>

      {/* 增长/下降贡献 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品增长 / 下降贡献</h3>
        <ReactECharts option={growthOption} style={{ height: '360px' }} />
      </div>

      {/* 产品结构变化：三年并列 */}
      <div className="bg-white rounded-xl border border-line p-4">
        <h3 className="text-sm font-medium text-sub mb-2">产品结构</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[2024, 2025, 2026].map(y => {
            const opt = structureOptions[String(y)] || {};
            return (
              <div key={y}>
                <ReactECharts option={opt} style={{ height: '280px' }} />
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
