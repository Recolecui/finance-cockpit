/** TypeScript 类型定义 */
export interface Period {
  year: number;
}

export interface KPI {
  period: string;
  sales: number;
  receive: number;
  receivable: number;
  outstock_count: number;
}

export interface TopCustomer { name: string; amount: number; }

export interface TrendItem {
  month: string;
  sales: number;
  orders: number;
  receive: number;
  receivable: number;
  sales_top5: TopCustomer[];
  receive_top5: TopCustomer[];
  receivable_top5: TopCustomer[];
}

export interface TrendData { year: number; mode: 'single' | 'multi'; end_month: number; months: TrendItem[]; }

export interface YearsData { years: number[]; }

export interface RegionItem { province: string; value: number; }
export interface RegionData { metric: string; regions: RegionItem[]; }

export interface RegionTopCustomer { name: string; amount: number; }
export interface RegionDetailItem { province: string; value: number; top5: RegionTopCustomer[]; }
export interface RegionDetailData {
  metric: string;
  provinces: RegionDetailItem[];
  overseas_unknown: number;
}

export interface ProductItem {
  category: string;
  amount: number;
  pct: number;
}
export interface ProductStructureData {
  mode: string;
  total: number;
  items: ProductItem[];
}

export interface ProductStructureYearData {
  years: Record<string, { total: number; items: ProductItem[] }>;
}

export interface GrowthItem {
  category: string;
  current: number;
  previous: number;
  diff: number;
}
export interface GrowthData { year: number; items: GrowthItem[]; }

export interface CustomerItem {
  name: string;
  province: string;
  amount: number;
  receivable: number;
  pct: number;
  cum_pct: number;
}
export interface CustomerData { total: number; total_customers: number; top_customers: number; customers: CustomerItem[]; }

export interface SalesmanItem {
  name: string;
  dept: string;
  sales: number;
  receivable: number;
}
export interface SalesmanData { items: SalesmanItem[]; }
