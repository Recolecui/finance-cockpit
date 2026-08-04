'use client';

import { useAPI, fmtMoney, fmtWan } from '@/lib/api';
import type { KPI, TrendData, RegionDetailData, GrowthData, Period, RegionDetailItem } from '@/types';
import { SERIES_COLORS } from '@/lib/api';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { useState, useMemo, useEffect } from 'react';

// 省份简称 → 地图 GeoJSON 全称（与 datav china.json 的 feature.name 对齐）
const PROV_TO_GEO: Record<string, string> = {
  '北京': '北京市', '天津': '天津市', '上海': '上海市', '重庆': '重庆市',
  '广东': '广东省', '江苏': '江苏省', '浙江': '浙江省', '山东': '山东省',
  '河南': '河南省', '河北': '河北省', '湖南': '湖南省', '湖北': '湖北省',
  '四川': '四川省', '福建': '福建省', '安徽': '安徽省', '江西': '江西省',
  '陕西': '陕西省', '山西': '山西省', '辽宁': '辽宁省', '吉林': '吉林省',
  '黑龙江': '黑龙江省', '云南': '云南省', '贵州': '贵州省', '甘肃': '甘肃省',
  '青海': '青海省', '海南': '海南省', '内蒙古': '内蒙古自治区',
  '广西': '广西壮族自治区', '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
  '西藏': '西藏自治区', '香港': '香港特别行政区', '澳门': '澳门特别行政区',
  '台湾': '台湾省',
};

export default function Dashboard({ period, trendMode }: { period: Period; trendMode: 'single' | 'multi' }) {
  const [regionMetric, setRegionMetric] = useState('sales');

  const now = new Date();
  const year = period.year;
  const ym = `year=${year}`;

  const kpiPath = `/dashboard/kpi?${ym}`;
  const regionPath = `/dashboard/region/detail?${ym}&mode=${trendMode}&metric=${regionMetric}`;
  const growthPath = `/dashboard/growth?year=${year}`;
  const trendPath = `/dashboard/trend?${ym}&mode=${trendMode}`;

  const { data: kpi } = useAPI<KPI>(kpiPath);
  const { data: trend } = useAPI<TrendData>(trendPath);
  const { data: region } = useAPI<RegionDetailData>(regionPath);
  const { data: growth } = useAPI<GrowthData>(growthPath);

  const isCurrent = year === now.getFullYear();
  const periodLabel = isCurrent ? `${year}年(1-${now.getMonth() + 1}月)` : `${year}年`;

  // 销售趋势图
  const trendOption = useMemo(() => {
    if (!trend) return {};
    const months = trend.months.map(m => m.month);
    return {
      grid: { left: 70, right: 30, top: 40, bottom: 30 },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#e3e8f0',
        textStyle: { color: '#1a2433', fontSize: 12 },
        formatter: (params: any) => {
          const mo = params[0]?.axisValue;
          const item = trend.months.find(m => m.month === mo);
          let s = `<div style="font-weight:600;margin-bottom:4px">${mo}</div>`;
          for (const p of params) {
            s += `<div>${p.marker}${p.seriesName}: <b>${fmtMoney(p.value)}</b></div>`;
            if (item) {
              const top5 = p.seriesName === '销售额' ? item.sales_top5
                : p.seriesName === '订单额' ? item.order_top5
                : p.seriesName === '回款' ? item.receive_top5
                : p.seriesName === '应收' ? item.receivable_top5 : [];
              if (top5 && top5.length) {
                s += `<div style="margin:3px 0 2px 14px;color:#6b7a90;font-size:11px">TOP5 客户:</div>`;
                top5.forEach((c, i) => {
                  s += `<div style="padding-left:14px;font-size:11px">${i + 1}. ${c.name} · ${fmtWan(c.amount)}</div>`;
                });
              }
            }
          }
          return s;
        },
      },
      legend: { data: ['订单额', '销售额', '回款', '应收'], top: 0 },
      xAxis: { type: 'category', data: months, axisLabel: { fontSize: 10, rotate: months.length > 14 ? 45 : 0 } },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtMoney(v), fontSize: 10 } },
      series: [
        { name: '订单额', type: 'line', data: trend.months.map(m => m.orders), smooth: true,
          itemStyle: { color: '#7c3aed' }, lineStyle: { type: 'dotted' } },
        { name: '销售额', type: 'line', data: trend.months.map(m => m.sales), smooth: true,
          itemStyle: { color: '#15803d' }, areaStyle: { opacity: 0.08 } },
        { name: '回款', type: 'line', data: trend.months.map(m => m.receive), smooth: true,
          itemStyle: { color: '#3b82f6' } },
        { name: '应收', type: 'line', data: trend.months.map(m => m.receivable), smooth: true,
          itemStyle: { color: '#ef4444' }, lineStyle: { type: 'dashed' } },
      ],
    };
  }, [trend]);

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
          label: { show: true, position: i.diff >= 0 ? 'right' : 'left', formatter: (params: any) => fmtMoney(params.value), fontSize: 10, color: '#475569' },
        })),
        barMaxWidth: 18,
      }],
    };
  }, [growth]);

  return (
    <section className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* KPI 卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KpiCard label={`订单额 · ${periodLabel}`} value={kpi ? fmtMoney(kpi.order) : '...'} />
        <KpiCard label={`出货额 · ${periodLabel}`} value={kpi ? fmtMoney(kpi.sales) : '...'} />
        <KpiCard label="回款" value={kpi ? fmtMoney(kpi.receive) : '...'} />
        <KpiCard label="应收余额" value={kpi ? fmtMoney(kpi.receivable) : '...'} />
        <KpiCard label="出库单数" value={kpi ? String(kpi.outstock_count) : '...'} />
      </div>

      {/* 销售趋势 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">
            销售趋势 · {trendMode === 'multi' ? `2024-01 至 ${year}年${now.getMonth() + 1}月` : `${periodLabel}`}
          </h3>
        </div>
        <ReactECharts option={trendOption} style={{ height: '280px' }} />
      </div>

      {/* 区域地图 + 指标切换 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-sub">区域分布 · {periodLabel}</h3>
          <div className="flex gap-1">
            {['order', 'sales', 'receive', 'receivable'].map(m => (
              <button key={m} onClick={() => setRegionMetric(m)}
                className={`px-3 py-1 text-xs rounded ${regionMetric === m ? 'bg-brand text-white' : 'bg-bg text-sub'}`}>
                {m === 'order' ? '订单额' : m === 'sales' ? '出货额' : m === 'receive' ? '回款' : '应收'}
              </button>
            ))}
          </div>
        </div>
        <ChinaRegionMap data={region} metric={regionMetric} mode={trendMode} />
        {region && (
          <p className="text-xs text-sub mt-1">
            统计期间总出货额：<span className="font-semibold text-gray-700">{fmtMoney(region.total_sales_amount)}</span>
          </p>
        )}
        {region && region.overseas_unknown > 0 && (
          <p className="text-xs text-sub mt-1">
            海外 / 未知 地区合计（未计入地图）：{fmtWan(region.overseas_unknown)}
          </p>
        )}
      </div>

      {/* 增长分析 */}
      <div className="bg-white rounded-xl border border-line p-4 mb-6">
        <h3 className="text-sm font-medium text-sub mb-2">增长贡献分析 · {year}年 vs 去年同期（同区间）</h3>
        <ReactECharts option={growthOption} style={{ height: '300px' }} />
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

function ChinaRegionMap({ data, metric, mode }: { data: RegionDetailData | undefined; metric: string; mode: 'single' | 'multi' }) {
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch('/china.json')
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(geo => { if (!cancelled) { echarts.registerMap('china', geo); setReady(true); } })
      .catch(e => { if (!cancelled) setErr(String(e)); });
    return () => { cancelled = true; };
  }, []);

  const option = useMemo(() => {
    if (!data) return {};
    // 阈值：不点按年统计=30万，点按年统计=300万（按所选指标金额判定）
    const TH = mode === 'multi' ? 3000000 : 300000;
    const showQty = metric === 'sales' || metric === 'order';
    const qtyName = metric === 'order' ? '订单数量' : '出货数量';
    const detailByGeo: Record<string, RegionDetailItem> = {};
    const mapData = data.provinces
      .filter(p => PROV_TO_GEO[p.province])
      .map(p => {
        const geo = PROV_TO_GEO[p.province];
        detailByGeo[geo] = p;
        const big = p.value > 10000000;
        return {
          name: geo,
          value: p.value,
          qty: p.qty || 0,
          label: { color: big ? '#ffffff' : '#334155' },
        };
      });
    return {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#e3e8f0',
        textStyle: { color: '#1a2433', fontSize: 12 },
        formatter: (p: any) => {
          const d = detailByGeo[p.name];
          const metricLabel = metric === 'receive' ? '回款额' : metric === 'receivable' ? '应收余额' : metric === 'order' ? '订单额' : '出货额';
          if (!d) return `<div style="font-weight:600">${p.name}</div>无数据`;
          let s = `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>`;
          s += `${metricLabel}(万元): <b>${fmtWan(d.value)}</b>`;
          if (showQty && d.qty) {
            s += `<br/>${qtyName}: <b>${Math.round(d.qty).toLocaleString('zh-CN')}</b>`;
          }
          if (d.top5 && d.top5.length) {
            s += `<div style="margin-top:5px;color:#6b7a90">TOP5 客户:</div>`;
            d.top5.forEach((c, i) => {
              s += `<div>${i + 1}. ${c.name} · ${fmtWan(c.amount)}</div>`;
            });
          }
          return s;
        },
      },
      visualMap: {
        type: 'piecewise',
        orient: 'vertical',
        left: 8,
        top: 'middle',
        pieces: [
          { value: 0, label: '0', color: '#9ca3af' },
          { gt: 0, lte: 300000, label: '30万以下', color: '#fca5a5' },
          { gt: 300000, lte: 800000, label: '30-80万' },
          { gt: 800000, lte: 3000000, label: '80-300万' },
          { gt: 3000000, lte: 5000000, label: '300-500万' },
          { gt: 5000000, lte: 10000000, label: '500-1000万' },
          { gt: 10000000, label: '>1000万' },
        ],
        inRange: { color: metric === 'receivable'
          ? ['#15803d', '#84cc16', '#facc15', '#fb923c', '#f97316', '#dc2626']   // 应收：低绿 → 高红（与销售相反）
          : metric === 'receive'
          ? ['#eff6ff', '#93c5fd', '#60a5fa', '#3b82f6', '#1d4ed8', '#1e3a8a']    // 回款：蓝色系
          : ['#fef08a', '#fb923c', '#facc15', '#84cc16', '#15803d', '#14532d'] }, // 销售/订单：低明黄 → 高墨绿
        textStyle: { color: '#6b7a90', fontSize: 11 },
      },
      series: [{
        type: 'map', map: 'china', roam: 'move', zoom: 1.33, center: [105, 38],
        data: mapData,
        label: {
          show: true,
          fontSize: 10,
          color: '#334155',
          formatter: (p: any) => {
            const d = detailByGeo[p.name];
            if (!d) return '';
            const big = d.value > 10000000;
            // 大于1000万：反白显示省名 + 金额(万元) + 数量(若有)
            if (big) {
              const base = `${p.name}\n${fmtWan(d.value)}万`;
              return (showQty && d.qty)
                ? `${base}\n${Math.round(d.qty).toLocaleString('zh-CN')}`
                : base;
            }
            // 达标数量省份：显示省名 + 出货/订单数量
            if (showQty && d.qty && d.value > TH) {
              return `${p.name}\n${Math.round(d.qty).toLocaleString('zh-CN')}`;
            }
            return '';
          },
        },
        itemStyle: { borderColor: '#ffffff', borderWidth: 0.5 },
        emphasis: {
          label: { show: true, color: '#1a2433' },
          itemStyle: { areaColor: '#fde68a' },
        },
      }],
    };
  }, [data, metric, mode]);

  if (err) return <div className="text-sub text-sm">地图加载失败：{err}</div>;
  if (!ready) return <div className="text-sub text-sm">地图加载中…</div>;
  return (
    <div style={{ height: '690px' }}>
      <ReactECharts option={option} style={{ height: '690px', width: '100%' }} />
    </div>
  );
}
