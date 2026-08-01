"""仪表盘数据 API — 聚合查询，供前端调用"""
from collections import defaultdict
from datetime import date
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SalesOutstock, ReceiveBill, Receivable
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ── 产品大类 -> 经营驾驶舱标准系列码（金蝶物料组归并）─────────────────
# 用户定义的成品系列：PPC/TPC/PDA/PC/IPC/PDS；外购品独立；其余归「配件」。
#   工控机三类（无风扇/上架/壁挂）合并为 IPC
#   工业显示器 -> PDS，加固便携设备 -> PDA
#   工业平板电脑 -> PPC，手持强固平板 -> TPC
CAT_TO_SERIES = {
    # 工控机系列 -> IPC
    "无风扇工控机": "IPC",
    "上架工控机": "IPC",
    "壁挂工控机": "IPC",
    # 工业计算机 / 平板 / 显示器 / 便携 系列
    "工业平板电脑": "PPC",
    "手持强固平板": "TPC",
    "工业显示器": "PDS",
    "加固便携设备": "PDA",
    # 外购品独立
    "外购品": "外购品",
}
# 成品系列展示顺序（PC 暂不使用，保留备用）
SERIES_ORDER = ["PPC", "TPC", "PDA", "PC", "IPC", "PDS", "配件", "外购品"]


def disp_cat(cat: Optional[str]) -> str:
    """产品大类展示归一化：金蝶物料组 -> 标准系列码；非成品/非外购品 -> 配件。"""
    cat = (cat or "").strip() or "未分类"
    return CAT_TO_SERIES.get(cat, "配件")


def _period_range(year: Optional[int], month: Optional[int] = None) -> Tuple[date, date]:
    """依据 年/月 计算查询区间 [start, end)。

    - 指定 month → 当月（1 号 ~ 次月 1 号）
    - 仅指定 year → 往年取全年；当年取到当前月（按年统计，截至本月）
    - 都不指定   → 默认当年（截至当前月）
    """
    today = date.today()
    y = year or today.year
    if month:
        start = date(y, month, 1)
        end = date(y, month, 1) + relativedelta(months=1)
    else:
        start = date(y, 1, 1)
        if y == today.year:
            end = date(today.year, today.month, 1) + relativedelta(months=1)
        else:
            end = date(y + 1, 1, 1)
    return start, end


def _year_end_month(year: int) -> int:
    """按年统计的截止月份：当年取到当前月，往年取 12 月。"""
    today = date.today()
    return today.month if year == today.year else 12


def _metric_source(metric: str):
    """返回 (模型, 金额列, 客户列) 供地域分布使用。"""
    if metric == "receive":
        return ReceiveBill, ReceiveBill.receive_amount, ReceiveBill.customer_name
    if metric == "receivable":
        return Receivable, Receivable.balance_amount, Receivable.customer_name
    return SalesOutstock, SalesOutstock.amount, SalesOutstock.customer_name


@router.get("/kpi")
def get_kpi(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """KPI: 销售额、回款、应收、出库数"""
    start, end = _period_range(year, month)

    # 销售额（标准出库单，过滤售后）
    sales = db.query(func.sum(SalesOutstock.amount)).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).scalar() or 0

    # 出库数
    outstock_count = db.query(func.count(SalesOutstock.id)).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
    ).scalar() or 0

    # 回款
    receive = db.query(func.sum(ReceiveBill.receive_amount)).filter(
        ReceiveBill.bill_date >= start,
        ReceiveBill.bill_date < end,
    ).scalar() or 0

    # 应收余额：始终显示当前最新总余额，不按所选周期过滤
    receivable = db.query(func.sum(Receivable.balance_amount)).scalar() or 0

    return {
        "period": f"{start.strftime('%Y-%m')}",
        "sales": round(float(sales), 2),
        "receive": round(float(receive), 2),
        "receivable": round(float(receivable), 2),
        "outstock_count": int(outstock_count),
    }


@router.get("/trend")
def get_trend(
    year: int = Query(default=date.today().year),
    mode: str = Query("multi", regex="^(single|multi)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """销售+回款+应收 月度趋势。

    - mode=multi（按年统计）：横轴 = (year-2)年1月 ~ year年当前月，约三年。
    - mode=single（单年）：横轴 = year年1月 ~ year年当前月/12月。
    每个月附带销售额 / 回款额 / 应收余额 TOP5 客户，供悬停 tooltip 展示。
    """
    end_month = _year_end_month(year)
    if mode == "single":
        start_d = date(year, 1, 1)
        end_d = date(year, end_month, 1) + relativedelta(months=1)
    else:
        start_d = date(year - 2, 1, 1)
        end_d = date(year, end_month, 1) + relativedelta(months=1)

    # 生成月份列表
    months_list = []
    cur = start_d
    while cur < end_d:
        months_list.append(cur.strftime("%Y-%m"))
        cur = cur + relativedelta(months=1)
    month_ends = {m: date(int(m[:4]), int(m[5:7]), 1) + relativedelta(months=1) for m in months_list}

    # 一次性取出窗口内明细，按「月-客户」聚合
    sales_rows = db.execute(text("""
        SELECT to_char(bill_date, 'YYYY-MM') AS mo, customer_name, amount
        FROM sales_outstock
        WHERE bill_date >= :start AND bill_date < :end AND bill_type LIKE '%标准%'
    """), {"start": start_d, "end": end_d}).fetchall()

    receive_rows = db.execute(text("""
        SELECT to_char(bill_date, 'YYYY-MM') AS mo, customer_name, receive_amount
        FROM receive_bill
        WHERE bill_date >= :start AND bill_date < :end
    """), {"start": start_d, "end": end_d}).fetchall()

    sales_sum: dict = defaultdict(float)
    sales_cust: dict = defaultdict(lambda: defaultdict(float))
    for mo, cust, amt in sales_rows:
        sales_sum[mo] += float(amt or 0)
        if cust:
            sales_cust[mo][cust] += float(amt or 0)

    recv_sum: dict = defaultdict(float)
    recv_cust: dict = defaultdict(lambda: defaultdict(float))
    for mo, cust, amt in receive_rows:
        recv_sum[mo] += float(amt or 0)
        if cust:
            recv_cust[mo][cust] += float(amt or 0)

    # 应收余额：按「月-客户」累计未收净额（应收生成 − 已收 的滚动累计），
    # 形成真实趋势曲线（每月不同，最终收敛到当前总余额 1.15 亿）。
    ar_month_rows = db.execute(text("""
        SELECT to_char(bill_date, 'YYYY-MM') AS mo, customer_name,
               SUM(amount - COALESCE(received_amount, 0)) AS net
        FROM receivable
        GROUP BY mo, customer_name
    """)).fetchall()
    net_by_mo_cust: dict = defaultdict(lambda: defaultdict(float))
    for mo, cust, net in ar_month_rows:
        net_by_mo_cust[mo][cust or ""] += float(net or 0)

    all_mo = sorted(net_by_mo_cust.keys())
    cum_by_mo: dict = {}
    cust_run: dict = defaultdict(float)
    cust_cum_by_mo: dict = {}
    run = 0.0
    for mo in all_mo:
        run += sum(net_by_mo_cust[mo].values())
        cum_by_mo[mo] = round(run, 2)
        for c, v in net_by_mo_cust[mo].items():
            cust_run[c] += v
        cust_cum_by_mo[mo] = dict(cust_run)

    def top5(d: dict):
        return [{"name": c, "amount": round(a, 2)}
                for c, a in sorted(d.items(), key=lambda x: -x[1])[:5]]

    def ar_top5_at(mo: str):
        return top5(cust_cum_by_mo.get(mo, {}))

    prev = 0.0
    months_data = []
    for m in months_list:
        if m in cum_by_mo:
            prev = cum_by_mo[m]
        months_data.append({
            "month": m,
            "sales": round(sales_sum.get(m, 0), 2),
            "orders": 0,
            "receive": round(recv_sum.get(m, 0), 2),
            "receivable": round(prev, 2),
            "sales_top5": top5(sales_cust.get(m, {})),
            "receive_top5": top5(recv_cust.get(m, {})),
            "receivable_top5": ar_top5_at(m),
        })
    return {"year": year, "mode": mode, "end_month": end_month, "months": months_data}


@router.get("/years")
def get_years(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """销售数据中存在的统计年份（供前端「按年统计」下拉选择）。"""
    rows = db.query(func.extract('year', SalesOutstock.bill_date)).filter(
        SalesOutstock.bill_type.like("%标准%"),
    ).distinct().all()
    years = sorted({int(float(r[0])) for r in rows})
    return {"years": years}


@router.get("/region")
def get_region(
    year: Optional[int] = None,
    month: Optional[int] = None,
    metric: str = Query("sales", regex="^(sales|receive|receivable)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """区域分布（按省份聚合）"""
    start, end = _period_range(year, month)

    Model, val_col, _ = _metric_source(metric)
    q = db.query(Model.province, func.sum(val_col)).filter(
        Model.bill_date >= start, Model.bill_date < end)
    if metric == "sales":
        q = q.filter(Model.bill_type.like("%标准%"))
    rows = q.group_by(Model.province).all()

    return {
        "metric": metric,
        "regions": [{"province": r[0] or "未知", "value": round(float(r[1] or 0), 2)} for r in rows],
    }


@router.get("/region/detail")
def get_region_detail(
    year: Optional[int] = None,
    month: Optional[int] = None,
    mode: str = Query("single", regex="^(single|multi)$"),
    metric: str = Query("sales", regex="^(sales|receive|receivable)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """区域分布明细：各省销售额/回款/应收 + TOP5 客户。

    - mode=single：按 year 参数取当年（当年取到当前月，往年取全年）。
    - mode=multi（按年统计）：取 (year-2)年1月 ~ year年当前月，约三年窗口。
    - metric=receivable：始终显示当前最新应收余额，不按周期过滤。

    返回 provinces: [{province, value, top5:[{name, amount}]}]
    """
    Model, val_col, cust_col = _metric_source(metric)

    if metric == "receivable":
        # 应收：始终取当前最新余额，不按周期过滤
        val_rows = db.query(Model.province, func.sum(val_col)).group_by(Model.province).all()
        cust_rows = db.query(Model.province, cust_col, func.sum(val_col)).group_by(Model.province, cust_col).all()
    else:
        if mode == "multi":
            end_month = _year_end_month(year or date.today().year)
            start = date((year or date.today().year) - 2, 1, 1)
            end = date(year or date.today().year, end_month, 1) + relativedelta(months=1)
        else:
            start, end = _period_range(year, month)

        base_filter = [Model.bill_date >= start, Model.bill_date < end]
        if metric == "sales":
            base_filter.append(Model.bill_type.like("%标准%"))

        val_rows = db.query(Model.province, func.sum(val_col)).filter(
            *base_filter).group_by(Model.province).all()
        cust_rows = db.query(Model.province, cust_col, func.sum(val_col)).filter(
            *base_filter).group_by(Model.province, cust_col).all()

    value_by_prov = {(r[0] or "未知"): float(r[1] or 0) for r in val_rows}

    top_tmp: dict = defaultdict(list)
    for prov, cust, amt in cust_rows:
        top_tmp[prov or "未知"].append((cust, float(amt or 0)))
    top5_by_prov = {
        p: [{"name": c, "amount": round(a, 2)}
            for c, a in sorted(v, key=lambda x: -x[1])[:5]]
        for p, v in top_tmp.items()
    }

    provinces = []
    for p in set(list(value_by_prov.keys()) + list(top5_by_prov.keys())):
        provinces.append({
            "province": p,
            "value": round(value_by_prov.get(p, 0), 2),
            "top5": top5_by_prov.get(p, []),
        })
    provinces.sort(key=lambda x: x["value"], reverse=True)

    # 海外 / 未知 汇总（地图无法展示，单独返回）
    overseas = round(sum(v for k, v in value_by_prov.items() if k in ("海外", "未知")), 2)

    return {"metric": metric, "mode": mode, "provinces": provinces, "overseas_unknown": overseas}


def _product_structure_for_period(start: date, end: date, db: Session):
    """产品结构（环形图）— 成品保留细分，其余归为「配件」。"""
    rows = db.query(
        SalesOutstock.product_category,
        func.sum(SalesOutstock.amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).group_by(SalesOutstock.product_category).all()

    agg: dict = defaultdict(float)
    for cat, amt in rows:
        agg[disp_cat(cat or "未分类")] += float(amt or 0)

    total = sum(agg.values())
    items = sorted(
        [{"category": k, "amount": round(v, 2),
          "pct": round(v / max(total, 1) * 100, 1)} for k, v in agg.items()],
        key=lambda x: (SERIES_ORDER.index(x["category"]) if x["category"] in SERIES_ORDER else 99, -x["amount"]))
    return {"total": round(total, 2), "items": items}


@router.get("/product-structure")
def get_product_structure(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """产品结构（环形图）— 成品保留细分，其余归为「配件」"""
    start, end = _period_range(year, month)
    return {"mode": "period", **_product_structure_for_period(start, end, db)}


@router.get("/product-structure/years")
def get_product_structure_years(
    years: str = Query("2024,2025,2026"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """按多个年份返回产品结构（用于前端同时展示三年饼图）。"""
    result: dict = {}
    for y_str in years.split(","):
        y = int(y_str.strip())
        start, end = _period_range(y)
        result[str(y)] = _product_structure_for_period(start, end, db)
    return {"years": result}


@router.get("/growth")
def get_growth(
    year: int = Query(default=date.today().year),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """增长分析（按产品大类贡献）— 成品保留细分，其余归为「配件」。
    按年统计：当年取到当前月，与去年同期（同区间）对比。"""
    end_month = _year_end_month(year)
    cur_start, cur_end = date(year, 1, 1), date(year, end_month, 1) + relativedelta(months=1)
    prev_start, prev_end = date(year - 1, 1, 1), date(year - 1, end_month, 1) + relativedelta(months=1)

    def _agg(s0, s1) -> dict:
        rows = db.query(
            SalesOutstock.product_category, func.sum(SalesOutstock.amount)
        ).filter(
            SalesOutstock.bill_date >= s0, SalesOutstock.bill_date < s1,
            SalesOutstock.bill_type.like("%标准%"),
        ).group_by(SalesOutstock.product_category).all()
        d: dict = defaultdict(float)
        for cat, amt in rows:
            d[disp_cat(cat or "未分类")] += float(amt or 0)
        return d

    cur = _agg(cur_start, cur_end)
    prev = _agg(prev_start, prev_end)
    cats = set(cur.keys()) | set(prev.keys())
    items = [{
        "category": c,
        "current": round(cur.get(c, 0), 2),
        "previous": round(prev.get(c, 0), 2),
        "diff": round(cur.get(c, 0) - prev.get(c, 0), 2),
    } for c in cats]
    items.sort(key=lambda x: x["diff"], reverse=True)
    return {"year": year, "items": items}


@router.get("/customers/top")
def get_top_customers(
    limit: int = Query(20, ge=1, le=100),
    year: Optional[int] = None,
    month: Optional[int] = None,
    mode: str = Query("single", regex="^(single|multi)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """客户 TOP N + 集中度 + 客户数量占比。

    - mode=single：按 year 当年（当年取到当前月，往年取全年）。
    - mode=multi（按年统计）：取 (year-2)年1月 ~ year年当前月，近三年窗口。
    """
    if mode == "multi":
        y = year or date.today().year
        end_month = _year_end_month(y)
        start = date(y - 2, 1, 1)
        end = date(y, end_month, 1) + relativedelta(months=1)
    else:
        start, end = _period_range(year, month)

    rows = db.query(
        SalesOutstock.customer_name,
        SalesOutstock.province,
        func.sum(SalesOutstock.amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).group_by(SalesOutstock.customer_name, SalesOutstock.province).order_by(
        func.sum(SalesOutstock.amount).desc()
    ).limit(limit).all()

    total = db.query(func.sum(SalesOutstock.amount)).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).scalar() or 0

    # 区间内独立客户总数（按客户名称去重）
    total_customers = db.query(func.count(func.distinct(SalesOutstock.customer_name))).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
        SalesOutstock.customer_name.isnot(None),
        SalesOutstock.customer_name != "",
    ).scalar() or 0

    # 各客户应收余额（当前最新，不按周期过滤）
    ar_rows = db.query(
        Receivable.customer_name,
        func.sum(Receivable.balance_amount),
    ).group_by(Receivable.customer_name).all()
    ar_map = {str(r[0]).strip(): float(r[1] or 0) for r in ar_rows}

    cum = 0
    items = []
    for r in rows:
        name = r[0]
        amt = float(r[2] or 0)
        cum += amt
        items.append({
            "name": name, "province": r[1] or "未知",
            "amount": round(amt, 2),
            "receivable": round(ar_map.get(str(name).strip(), 0), 2),
            "pct": round(amt / max(float(total), 1) * 100, 1),
            "cum_pct": round(cum / max(float(total), 1) * 100, 1),
        })
    return {
        "total": round(float(total), 2),
        "total_customers": int(total_customers),
        "top_customers": min(limit, int(total_customers)),
        "customers": items,
    }


@router.get("/salesman")
def get_salesman(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """业务员分析（悬停展示）"""
    start, end = _period_range(year, month)

    rows = db.query(
        SalesOutstock.salesman,
        SalesOutstock.sales_dept,
        func.sum(SalesOutstock.amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
        SalesOutstock.salesman.isnot(None),
        SalesOutstock.salesman != "",
    ).group_by(SalesOutstock.salesman, SalesOutstock.sales_dept).order_by(
        func.sum(SalesOutstock.amount).desc()
    ).all()

    # 应收（当前最新，不按周期过滤）
    ar_rows = db.query(
        Receivable.salesman,
        func.sum(Receivable.balance_amount),
    ).group_by(Receivable.salesman).all()
    ar_map = {r[0]: float(r[1] or 0) for r in ar_rows}

    return {
        "items": [{"name": r[0], "dept": r[1] or "",
                    "sales": round(float(r[2] or 0), 2),
                    "receivable": round(ar_map.get(r[0], 0), 2)} for r in rows],
    }


@router.get("/sync-status")
def get_sync_status(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """数据同步状态"""
    from app.models import SyncLog
    rows = db.query(SyncLog).order_by(SyncLog.created_at.desc()).limit(10).all()
    return {
        "logs": [{
            "type": r.sync_type, "start": str(r.start_date) if r.start_date else None,
            "end": str(r.end_date) if r.end_date else None,
            "fetched": r.rows_fetched, "inserted": r.rows_inserted,
            "status": r.status, "duration": r.duration_sec,
            "error": r.error_msg, "time": r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
    }
