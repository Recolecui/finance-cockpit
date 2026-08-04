'use client';

import { useAPI, fmtMoney } from '@/lib/api';
import type { CustomerData, SalesmanData, SalesmanItem, Period } from '@/types';
import ReactECharts from 'echarts-for-react';
import { useMemo, useState } from 'react';

// 常见姓氏笔画数（用于「姓氏笔画」排序；未收录时退化为字符码，保证稳定有序）
const STROKE: Record<string, number> = {
  李: 7, 陈: 7, 范: 8, 梁: 11, 吴: 7, 荣: 9, 周: 8, 黄: 11, 杨: 7, 张: 7, 胡: 9,
  王: 4, 刘: 6, 赵: 9, 孙: 6, 郑: 8, 冯: 5, 蒋: 12, 沈: 7, 韩: 12, 朱: 6, 秦: 10,
  许: 6, 何: 7, 吕: 6, 施: 9, 孔: 4, 曹: 11, 严: 7, 华: 6, 金: 8, 魏: 17, 陶: 10,
  姜: 9, 谢: 12, 邹: 7, 喻: 12, 柏: 9, 章: 11, 苏: 7, 潘: 15, 葛: 12, 彭: 12, 鲁: 12,
  韦: 4, 马: 3, 苗: 8, 方: 4, 俞: 9, 任: 6, 袁: 10, 柳: 9, 史: 5, 唐: 10, 费: 9,
  薛: 16, 雷: 13, 贺: 9, 倪: 10, 汤: 6, 罗: 8, 毕: 6, 郝: 9, 安: 6, 常: 11, 乐: 5,
  于: 3, 傅: 12, 齐: 6, 康: 11, 伍: 6, 余: 7, 顾: 10, 孟: 8, 平: 5, 和: 8, 萧: 11,
  尹: 4, 姚: 9, 邵: 7, 汪: 7, 毛: 4, 米: 6, 明: 8, 计: 4, 成: 6, 戴: 17, 谈: 10,
  宋: 7, 茅: 8, 庞: 8, 熊: 14, 纪: 6, 舒: 12, 屈: 8, 项: 9, 祝: 9, 董: 12, 杜: 7,
  阮: 6, 林: 8, 钟: 9, 徐: 10, 邱: 7, 骆: 9, 高: 10, 夏: 10, 蔡: 14, 田: 5, 樊: 15,
  凌: 10, 霍: 16, 万: 3, 柯: 9, 管: 14, 卢: 5, 莫: 10, 房: 8, 龚: 11, 程: 12, 邢: 6,
  裴: 14, 陆: 7, 翁: 10, 荀:9, 惠: 12, 甄: 13, 曲: 6, 封: 9, 丁: 2, 邓: 4, 郁: 8,
  单: 8, 洪: 9, 包: 5, 诸: 10, 左: 5, 石: 5, 崔: 11, 吉: 6, 钮: 9, 蓝: 13, 闵: 7,
  席: 10, 季: 8, 麻: 11, 强: 11, 贾: 10, 路: 13, 娄: 9, 江: 6, 童: 12, 颜: 15, 郭: 10,
  梅: 11, 盛: 11, 刁: 2, 谭: 14, 龙: 5, 叶: 5,
};
function surnameStroke(name: string): number {
  if (!name) return 999;
  const c = name.charAt(0);
  return STROKE[c] ?? (name.charCodeAt(0) % 31);
}

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
  const [salesSort, setSalesSort] = useState<'stroke' | 'sales' | 'receivable'>('stroke');
  const [custSort, setCustSort] = useState<'amount' | 'receivable'>('amount');

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

  // 客户排行：可点击「金额 / 应收」排序（默认金额，与后端一致）。
  // 占比/累计列是按金额算的固定值，切到「应收」排序时隐藏，避免误导。
  const sortedCustomers = useMemo(() => {
    if (!data) return [];
    const arr = [...data.customers];
    if (custSort === 'receivable') arr.sort((a, b) => b.receivable - a.receivable);
    else arr.sort((a, b) => b.amount - a.amount);
    return arr;
  }, [data, custSort]);

  // 业务员：按所选维度排序（姓氏笔画 / 销售额 / 回款额），同名按部门聚合
  const sortedSalesmen = useMemo(() => {
    if (!salesmen) return [];
    const agg = new Map<string, SalesmanItem>();
    (salesmen.items || []).forEach(s => {
      const cur = agg.get(s.name) || { name: s.name, dept: s.dept, sales: 0, receivable: 0 };
      cur.sales += s.sales;
      cur.receivable += s.receivable;
      if (s.dept && !cur.dept.includes(s.dept)) cur.dept = cur.dept ? cur.dept + '/' + s.dept : s.dept;
      agg.set(s.name, cur);
    });
    const arr = Array.from(agg.values());
    if (salesSort === 'sales') arr.sort((a, b) => b.sales - a.sales);
    else if (salesSort === 'receivable') arr.sort((a, b) => b.receivable - a.receivable);
    else arr.sort((a, b) => {
      const d = surnameStroke(a.name) - surnameStroke(b.name);
      return d !== 0 ? d : a.name.localeCompare(b.name, 'zh');
    });
    return arr;
  }, [salesmen, salesSort]);

  const barMetric: 'sales' | 'receivable' = salesSort === 'receivable' ? 'receivable' : 'sales';
  const salesmanBarOption = useMemo(() => {
    const items = sortedSalesmen;
    if (!items.length) return {};
    return {
      grid: { left: 72, right: 96, top: 10, bottom: 16 },
      tooltip: {
        formatter: (p: any) => {
          const s = items[p.dataIndex];
          return `${s.name}（${s.dept || '-'}）<br>销售额: ${fmtMoney(s.sales)}<br>应收: ${fmtMoney(s.receivable)}`;
        },
      },
      xAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      yAxis: { type: 'category', data: items.map(i => i.name), axisLabel: { fontSize: 11 }, inverse: true },
      series: [{
        type: 'bar',
        data: items.map(i => Math.round(i[barMetric])),
        barMaxWidth: 16,
        itemStyle: { color: barMetric === 'receivable' ? '#f59e0b' : '#3b82f6', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', formatter: (p: any) => fmtMoney(p.value), fontSize: 10, color: '#475569' },
      }],
    };
  }, [sortedSalesmen, barMetric]);

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
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">客户排行 TOP20 · {periodLabel}</h3>
          <div className="flex gap-1">
            {([['amount', '金额'], ['receivable', '应收']] as const).map(([k, label]) => (
              <button key={k} onClick={() => setCustSort(k)}
                className={`px-3 py-1 text-xs rounded ${custSort === k ? 'bg-brand text-white' : 'bg-bg text-sub'}`}>
                {label}排序
              </button>
            ))}
          </div>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="text-sub border-b border-line">
            <th className="text-left py-2">#</th><th className="text-left">客户</th>
            <th className="text-left">省份</th><th className="text-right">金额</th>
            <th className="text-right">应收(万元)</th>
            {custSort === 'amount' && <><th className="text-right">占比</th><th className="text-right">累计</th></>}
          </tr></thead>
          <tbody>
            {sortedCustomers.map((c, i) => (
              <tr key={c.name} className="border-b border-line hover:bg-bg">
                <td className="py-2 text-sub">{i + 1}</td>
                <td className="truncate max-w-[200px]" title={c.name}>{c.name}</td>
                <td className="text-sub">{c.province}</td>
                <td className="text-right font-medium">{fmtMoney(c.amount)}</td>
                <td className="text-right text-down font-medium">{fmtMoney(c.receivable)}</td>
                {custSort === 'amount' && <><td className="text-right">{c.pct}%</td>
                <td className="text-right text-sub">{c.cum_pct}%</td></>}
              </tr>
            ))}
          </tbody>
        </table>
        {custSort === 'receivable' && (
          <p className="text-xs text-sub mt-2">注：当前按「应收」排序，占比/累计列为按金额统计的固定值，故隐藏。</p>
        )}
      </div>

      {/* 业务员分析（始终展示，置于底部） */}
      <div className="bg-white rounded-xl border border-line p-4">
        <h3 className="text-sm font-medium text-sub mb-2">业务员分析 · 销售额 / 回款对比</h3>
        <div className="flex gap-1 mb-3">
          {([['stroke', '姓氏笔画'], ['sales', '销售额'], ['receivable', '回款额']] as const).map(([k, label]) => (
            <button key={k} onClick={() => setSalesSort(k)}
              className={`px-3 py-1 text-xs rounded ${salesSort === k ? 'bg-brand text-white' : 'bg-bg text-sub'}`}>
              {label}
            </button>
          ))}
        </div>
        <ReactECharts option={salesmanBarOption} style={{ height: `${Math.max(240, sortedSalesmen.length * 28)}px` }} />
      </div>
    </section>
  );
}
