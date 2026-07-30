"""仪表盘数据 API — 聚合查询，供前端调用"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import date, timedelta
from typing import Optional
from app.database import get_db
from app.models import SalesOutstock, ReceiveBill, Receivable
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpi")
def get_kpi(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """KPI: 销售额、回款、应收、出库数"""
    if year and month:
        start = date(year, month, 1)
        end = date(year + (month // 12), (month % 12) + 1, 1) if month < 12 else date(year + 1, 1, 1)
    else:
        start = date(date.today().year, date.today().month, 1)
        end = date(date.today().year, date.today().month + 1, 1) if date.today().month < 12 else date(date.today().year + 1, 1, 1)

    # 销售额（标准出库单，过滤售后）
    sales = db.query(func.sum(SalesOutstock.total_amount)).filter(
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

    # 应收余额（截至当月末）
    receivable = db.query(func.sum(Receivable.balance_amount)).filter(
        Receivable.bill_date < end,
    ).scalar() or 0

    return {
        "period": f"{start.strftime('%Y-%m')}",
        "sales": round(float(sales), 2),
        "receive": round(float(receive), 2),
        "receivable": round(float(receivable), 2),
        "outstock_count": int(outstock_count),
    }


@router.get("/trend")
def get_trend(
    months: int = Query(36, ge=1, le=120),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """销售+回款月度趋势"""
    end = date.today()
    start = end - timedelta(days=months * 31)

    # 按月聚合销售
    sales_rows = db.execute(text("""
        SELECT to_char(bill_date, 'YYYY-MM') as mo,
               SUM(total_amount) as amount, COUNT(*) as cnt
        FROM sales_outstock
        WHERE bill_date >= :start AND bill_type LIKE '%标准%'
        GROUP BY 1 ORDER BY 1
    """), {"start": start}).fetchall()

    # 按月聚合回款
    receive_rows = db.execute(text("""
        SELECT to_char(bill_date, 'YYYY-MM') as mo,
               SUM(receive_amount) as amount
        FROM receive_bill
        WHERE bill_date >= :start
        GROUP BY 1 ORDER BY 1
    """), {"start": start}).fetchall()

    receive_map = {r[0]: float(r[1] or 0) for r in receive_rows}
    months_data = []
    for r in sales_rows:
        months_data.append({
            "month": r[0],
            "sales": round(float(r[1] or 0), 2),
            "orders": int(r[2]),
            "receive": round(receive_map.get(r[0], 0), 2),
        })
    return {"months": months_data}


@router.get("/region")
def get_region(
    year: Optional[int] = None,
    metric: str = Query("sales", regex="^(sales|receive|receivable)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """区域分布（按省份聚合）"""
    if year:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
    else:
        start = date(date.today().year, 1, 1)
        end = date(date.today().year + 1, 1, 1)

    if metric == "sales":
        rows = db.query(
            SalesOutstock.province,
            func.sum(SalesOutstock.total_amount),
        ).filter(
            SalesOutstock.bill_date >= start,
            SalesOutstock.bill_date < end,
            SalesOutstock.bill_type.like("%标准%"),
        ).group_by(SalesOutstock.province).all()
    elif metric == "receive":
        from app.models import ReceiveBill
        rows = db.query(
            SalesOutstock.province,
            func.sum(ReceiveBill.receive_amount),
        ).join(ReceiveBill, ReceiveBill.customer_name == SalesOutstock.customer_name).filter(
            ReceiveBill.bill_date >= start,
            ReceiveBill.bill_date < end,
        ).group_by(SalesOutstock.province).all()
    else:  # receivable
        rows = db.query(
            SalesOutstock.province,
            func.sum(Receivable.balance_amount),
        ).join(Receivable, Receivable.customer_name == SalesOutstock.customer_name).filter(
            Receivable.bill_date < end,
        ).group_by(SalesOutstock.province).all()

    return {
        "metric": metric,
        "regions": [{"province": r[0] or "未知", "value": round(float(r[1] or 0), 2)} for r in rows],
    }


@router.get("/product-structure")
def get_product_structure(
    mode: str = Query("month", regex="^(month|year)$"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """产品结构（环形图）"""
    if mode == "month":
        start = date(date.today().year, date.today().month, 1)
    else:
        start = date(date.today().year, 1, 1)
    end = date.today() + timedelta(days=1)

    rows = db.query(
        SalesOutstock.product_category,
        func.sum(SalesOutstock.total_amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).group_by(SalesOutstock.product_category).order_by(func.sum(SalesOutstock.total_amount).desc()).all()

    total = sum(float(r[1] or 0) for r in rows)
    return {
        "mode": mode,
        "total": round(total, 2),
        "items": [{"category": r[0] or "未分类", "amount": round(float(r[1] or 0), 2),
                    "pct": round(float(r[1] or 0) / max(total, 1) * 100, 1)} for r in rows],
    }


@router.get("/growth")
def get_growth(
    year: int = Query(default=date.today().year),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """增长分析（按产品大类贡献）"""
    rows = db.execute(text("""
        WITH cur AS (
            SELECT product_category, SUM(total_amount) as amt
            FROM sales_outstock
            WHERE bill_date >= :cur_start AND bill_date < :cur_end AND bill_type LIKE '%标准%'
            GROUP BY 1
        ), prev AS (
            SELECT product_category, SUM(total_amount) as amt
            FROM sales_outstock
            WHERE bill_date >= :prev_start AND bill_date < :prev_end AND bill_type LIKE '%标准%'
            GROUP BY 1
        )
        SELECT COALESCE(c.product_category, p.product_category) as cat,
               COALESCE(c.amt, 0) as cur_amt,
               COALESCE(p.amt, 0) as prev_amt,
               COALESCE(c.amt, 0) - COALESCE(p.amt, 0) as diff
        FROM cur c FULL OUTER JOIN prev p ON c.product_category = p.product_category
        ORDER BY diff DESC
    """), {
        "cur_start": date(year, 1, 1), "cur_end": date(year + 1, 1, 1),
        "prev_start": date(year - 1, 1, 1), "prev_end": date(year, 1, 1),
    }).fetchall()

    return {
        "year": year,
        "items": [{"category": r[0], "current": round(float(r[1]), 2),
                    "previous": round(float(r[2]), 2), "diff": round(float(r[3]), 2)} for r in rows],
    }


@router.get("/customers/top")
def get_top_customers(
    limit: int = Query(15, ge=1, le=100),
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """客户 TOP N + 集中度"""
    if year:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
    else:
        start = date(date.today().year, 1, 1)
        end = date(date.today().year + 1, 1, 1)

    rows = db.query(
        SalesOutstock.customer_name,
        SalesOutstock.province,
        func.sum(SalesOutstock.total_amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).group_by(SalesOutstock.customer_name, SalesOutstock.province).order_by(
        func.sum(SalesOutstock.total_amount).desc()
    ).limit(limit).all()

    total = db.query(func.sum(SalesOutstock.total_amount)).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
    ).scalar() or 0

    cum = 0
    items = []
    for r in rows:
        cum += float(r[2] or 0)
        items.append({
            "name": r[0], "province": r[1] or "未知",
            "amount": round(float(r[2] or 0), 2),
            "pct": round(float(r[2] or 0) / max(float(total), 1) * 100, 1),
            "cum_pct": round(cum / max(float(total), 1) * 100, 1),
        })
    return {"total": round(float(total), 2), "customers": items}


@router.get("/salesman")
def get_salesman(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """业务员分析（悬停展示）"""
    if year:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
    else:
        start = date(date.today().year, 1, 1)
        end = date(date.today().year + 1, 1, 1)

    rows = db.query(
        SalesOutstock.salesman,
        SalesOutstock.sales_dept,
        func.sum(SalesOutstock.total_amount),
    ).filter(
        SalesOutstock.bill_date >= start,
        SalesOutstock.bill_date < end,
        SalesOutstock.bill_type.like("%标准%"),
        SalesOutstock.salesman.isnot(None),
        SalesOutstock.salesman != "",
    ).group_by(SalesOutstock.salesman, SalesOutstock.sales_dept).order_by(
        func.sum(SalesOutstock.total_amount).desc()
    ).all()

    # 应收
    ar_rows = db.query(
        Receivable.salesman,
        func.sum(Receivable.balance_amount),
    ).filter(
        Receivable.bill_date >= start,
        Receivable.bill_date < end,
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
