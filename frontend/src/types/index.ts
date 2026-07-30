/** TypeScript 类型定义 */
export interface KPI {
  period: string;
  sales: number;
  receive: number;
  receivable: number;
  outstock_count: number;
}

export interface TrendItem {
  month: string;
  sales: number;
  orders: number;
  receive: number;
}

export interface TrendData { months: TrendItem[]; }

export interface RegionItem { province: string; value: number; }
export interface RegionData { metric: string; regions: RegionItem[]; }

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
  pct: number;
  cum_pct: number;
}
export interface CustomerData { total: number; customers: CustomerItem[]; }

export interface SalesmanItem {
  name: string;
  dept: string;
  sales: number;
  receivable: number;
}
export interface SalesmanData { items: SalesmanItem[]; }
