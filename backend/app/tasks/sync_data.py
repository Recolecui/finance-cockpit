"""数据同步任务 — 从金蝶 API 拉取数据写入 PostgreSQL"""
import os
import sys
import time
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine, Base
from app.models import SalesOutstock, ReceiveBill, Receivable, Material, SyncLog
from app.services.kingdee import KingdeeClient, classify_product, normalize_code

# 省份推断关键词（复用 region-sales-app 的逻辑）
import re
CITY2PROV = {}
_kw = {
    "北京": ["北京"], "上海": ["上海"], "天津": ["天津"], "重庆": ["重庆"],
    "广东": ["广东","广州","深圳","东莞","佛山","珠海","中山","惠州","汕头","江门","肇庆","清远","潮州","揭阳","茂名","湛江"],
    "江苏": ["江苏","南京","苏州","无锡","常州","南通","徐州","扬州","镇江","泰州","盐城","淮安","连云港","宿迁","昆山","张家港","常熟","太仓","江阴","宜兴"],
    "浙江": ["浙江","杭州","宁波","温州","嘉兴","湖州","绍兴","金华","义乌","台州","衢州","丽水","舟山","慈溪","余姚","海宁","桐乡","诸暨"],
    "安徽": ["安徽","合肥","芜湖","蚌埠","马鞍山","安庆","滁州","阜阳","宿州","六安","宣城","铜陵","淮南","淮北","黄山"],
    "福建": ["福建","福州","厦门","泉州","漳州","莆田","宁德","龙岩","三明","南平","晋江","石狮"],
    "江西": ["江西","南昌","赣州","九江","上饶","吉安","宜春","抚州","景德镇","萍乡","新余","鹰潭"],
    "山东": ["山东","济南","青岛","烟台","潍坊","淄博","济宁","临沂","威海","泰安","德州","聊城","滨州","东营","日照","菏泽","枣庄"],
    "河南": ["河南","郑州","洛阳","新乡","南阳","许昌","开封","安阳","焦作","平顶山","商丘","信阳","周口","驻马店"],
    "湖北": ["湖北","武汉","宜昌","襄阳","荆州","黄石","十堰","孝感","荆门","鄂州","黄冈","咸宁","随州","恩施"],
    "湖南": ["湖南","长沙","株洲","湘潭","衡阳","岳阳","常德","邵阳","益阳","郴州","永州","怀化","娄底","张家界"],
    "河北": ["河北","石家庄","唐山","保定","邯郸","邢台","沧州","廊坊","衡水","秦皇岛","张家口","承德","雄安"],
    "山西": ["山西","太原","大同","运城","临汾","长治","晋城","晋中","吕梁","忻州","朔州","阳泉"],
    "内蒙古": ["内蒙古","呼和浩特","包头","鄂尔多斯","赤峰","通辽","呼伦贝尔"],
    "辽宁": ["辽宁","沈阳","大连","鞍山","抚顺","锦州","营口","丹东","盘锦","葫芦岛","本溪","辽阳","铁岭","阜新","朝阳"],
    "吉林": ["吉林","长春","延边","四平","通化","松原","白城","辽源","白山"],
    "黑龙江": ["黑龙江","哈尔滨","大庆","齐齐哈尔","牡丹江","佳木斯","绥化","鸡西","鹤岗","黑河","双鸭山","伊春","七台河"],
    "四川": ["四川","成都","绵阳","德阳","宜宾","南充","泸州","乐山","达州","内江","自贡","眉山","遂宁","广安","广元","巴中","雅安","攀枝花","资阳"],
    "贵州": ["贵州","贵阳","遵义","六盘水","安顺","毕节","铜仁","黔南","黔东南","黔西南"],
    "云南": ["云南","昆明","曲靖","玉溪","大理","红河","楚雄","昭通","保山","普洱","丽江","文山","西双版纳","德宏"],
    "陕西": ["陕西","西安","咸阳","宝鸡","渭南","汉中","榆林","延安","安康","商洛","铜川"],
    "甘肃": ["甘肃","兰州","天水","酒泉","张掖","武威","白银","定西","庆阳","平凉","陇南","嘉峪关","金昌","临夏","甘南"],
    "青海": ["青海","西宁","海东","海西","格尔木"],
    "宁夏": ["宁夏","银川","石嘴山","吴忠","中卫","固原"],
    "新疆": ["新疆","乌鲁木齐","克拉玛依","吐鲁番","哈密","昌吉","伊犁","阿克苏","喀什","库尔勒","和田","塔城"],
    "广西": ["广西","南宁","柳州","桂林","梧州","北海","玉林","钦州","百色","贵港","河池","贺州","来宾","崇左","防城港"],
    "海南": ["海南","海口","三亚","儋州","琼海","文昌","万宁"],
    "西藏": ["西藏","拉萨","日喀则","林芝","昌都","山南","那曲"],
    "香港": ["香港"], "澳门": ["澳门"], "台湾": ["台湾","台北","高雄","台中","台南","新竹"],
}
for prov, kws in _kw.items():
    for k in kws:
        CITY2PROV[k] = prov
KW_LIST = sorted(CITY2PROV.keys(), key=len, reverse=True)
CJK = re.compile(r"[一-鿿]")

def infer_province(customer_name: str) -> tuple:
    """返回 (省份, 是否海外)"""
    name = str(customer_name or "").strip()
    if not name:
        return "未知", False
    if not CJK.search(name):
        return "海外", True
    for kw in KW_LIST:
        if kw in name:
            return CITY2PROV[kw], False
    return "未知", False


def sync_materials(db: Session, client: KingdeeClient) -> dict:
    """同步物料主数据"""
    log = SyncLog(sync_type="material", status="running")
    db.add(log)
    db.commit()
    t0 = time.time()
    try:
        rows = client.fetch_materials()
        log.rows_fetched = len(rows)
        inserted = 0
        for r in rows:
            code = str(r[0] or "").strip()
            if not code:
                continue
            cat = str(r[4] or "").strip()
            stmt = pg_insert(Material).values(
                material_number=code,
                material_name=str(r[1] or "").strip(),
                material_group_code=str(r[2] or "").strip(),
                material_group_name=str(r[3] or "").strip(),
                category=cat,
                product_category=classify_product(code, cat),
                erp_cls=int(r[5]) if r[5] else None,
                unit=str(r[6] or "").strip(),
                spec=str(r[7] or "").strip(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["material_number"],
                set_=dict(
                    material_name=stmt.excluded.material_name,
                    category=stmt.excluded.category,
                    product_category=stmt.excluded.product_category,
                    material_group_code=stmt.excluded.material_group_code,
                    spec=stmt.excluded.spec,
                ),
            )
            db.execute(stmt)
            inserted += 1
        db.commit()
        log.rows_inserted = inserted
        log.status = "success"
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        return {"fetched": len(rows), "inserted": inserted}
    except Exception as e:
        db.rollback()
        log.status = "failed"
        log.error_msg = str(e)
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        raise


def sync_outstock(db: Session, client: KingdeeClient, start_date: str, end_date: str) -> dict:
    """同步销售出库单"""
    log = SyncLog(sync_type="outstock", start_date=start_date, end_date=end_date, status="running")
    db.add(log)
    db.commit()
    t0 = time.time()
    try:
        rows = client.fetch_outstock(start_date, end_date)
        log.rows_fetched = len(rows)
        # 预加载物料分类映射
        mat_map = {}
        for m in db.query(Material.material_number, Material.product_category).all():
            mat_map[m.material_number] = m.product_category
        inserted = 0
        for r in rows:
            bill_no = str(r[0] or "").strip()
            mat_code = str(r[7] or "").strip()
            if not bill_no or not mat_code:
                continue
            # 产品分类：优先物料主数据，否则按编码前缀
            pcat = mat_map.get(mat_code) or classify_product(mat_code)
            # 省份推断
            cust = str(r[4] or "").strip()
            prov, is_overseas = infer_province(cust)
            # 日期解析
            from datetime import datetime as dt
            d = r[1]
            if isinstance(d, str):
                try:
                    d = dt.strptime(d[:10], "%Y-%m-%d").date()
                except:
                    continue
            elif isinstance(d, dt):
                d = d.date()
            bill_type = str(r[2] or "").strip()
            # 跳过售后维修领料单
            if "售后" in bill_type or "维修" in bill_type:
                continue
            # 审核日期
            ap = r[20]
            approve_dt = None
            if isinstance(ap, str):
                try:
                    approve_dt = dt.strptime(ap[:19], "%Y-%m-%dT%H:%M:%S")
                except:
                    approve_dt = None
            stmt = pg_insert(SalesOutstock).values(
                bill_no=bill_no,
                bill_date=d,
                bill_type=bill_type,
                doc_status=str(r[3] or "").strip(),
                customer_name=cust,
                customer_number=str(r[5] or "").strip(),
                material_name=str(r[6] or "").strip(),
                material_number=mat_code,
                product_category=pcat,
                spec=str(r[8] or "").strip(),
                qty=float(r[9] or 0),
                amount=float(r[10] or 0),
                tax_amount=float(r[11] or 0),
                total_amount=float(r[12] or 0),
                unit_price=float(r[13] or 0),
                sales_org=str(r[14] or "").strip(),
                sales_dept=str(r[15] or "").strip(),
                salesman=str(r[16] or "").strip(),
                warehouse=str(r[17] or "").strip(),
                note=str(r[18] or "").strip(),
                entry_note=str(r[19] or "").strip(),
                approve_date=approve_dt,
                province=prov,
                is_overseas=is_overseas,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_outstock_bill_material",
                set_=dict(
                    qty=stmt.excluded.qty, amount=stmt.excluded.amount,
                    total_amount=stmt.excluded.total_amount, product_category=stmt.excluded.product_category,
                    province=stmt.excluded.province, salesman=stmt.excluded.salesman,
                    approve_date=stmt.excluded.approve_date,
                ),
            )
            db.execute(stmt)
            inserted += 1
        db.commit()
        log.rows_inserted = inserted
        log.status = "success"
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        return {"fetched": len(rows), "inserted": inserted}
    except Exception as e:
        db.rollback()
        log.status = "failed"
        log.error_msg = str(e)
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        raise


def sync_receive(db: Session, client: KingdeeClient, start_date: str, end_date: str) -> dict:
    """同步收款单（回款）"""
    log = SyncLog(sync_type="receive", start_date=start_date, end_date=end_date, status="running")
    db.add(log)
    db.commit()
    t0 = time.time()
    try:
        rows = client.fetch_receive(start_date, end_date)
        log.rows_fetched = len(rows)
        inserted = 0
        for r in rows:
            bill_no = str(r[0] or "").strip()
            if not bill_no:
                continue
            from datetime import datetime as dt
            d = r[1]
            if isinstance(d, str):
                try:
                    d = dt.strptime(d[:10], "%Y-%m-%d").date()
                except:
                    continue
            elif isinstance(d, dt):
                d = d.date()
            stmt = pg_insert(ReceiveBill).values(
                bill_no=bill_no, bill_date=d, bill_type=str(r[2] or "").strip(),
                customer_name=str(r[3] or "").strip(), customer_number=str(r[4] or "").strip(),
                receive_amount=float(r[5] or 0), currency=str(r[6] or "").strip(),
                settle_type=str(r[7] or "").strip(),
                sales_dept=str(r[8] or "").strip(), salesman=str(r[9] or "").strip(),
                remark=str(r[10] or "").strip(),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_receive_bill_no",
                set_=dict(receive_amount=stmt.excluded.receive_amount, customer_name=stmt.excluded.customer_name),
            )
            db.execute(stmt)
            inserted += 1
        db.commit()
        log.rows_inserted = inserted
        log.status = "success"
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        return {"fetched": len(rows), "inserted": inserted}
    except Exception as e:
        db.rollback()
        log.status = "failed"
        log.error_msg = str(e)
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        raise


def sync_receivable(db: Session, client: KingdeeClient, start_date: str, end_date: str) -> dict:
    """同步应收单"""
    log = SyncLog(sync_type="receivable", start_date=start_date, end_date=end_date, status="running")
    db.add(log)
    db.commit()
    t0 = time.time()
    try:
        rows = client.fetch_receivable(start_date, end_date)
        log.rows_fetched = len(rows)
        inserted = 0
        for r in rows:
            bill_no = str(r[0] or "").strip()
            if not bill_no:
                continue
            from datetime import datetime as dt
            d = r[1]
            if isinstance(d, str):
                try:
                    d = dt.strptime(d[:10], "%Y-%m-%d").date()
                except:
                    continue
            elif isinstance(d, dt):
                d = d.date()
            try:
                amt = float(r[5] or 0)
            except:
                amt = 0.0
            try:
                recv = float(r[6] or 0)
            except:
                recv = 0.0
            stmt = pg_insert(Receivable).values(
                bill_no=bill_no, bill_date=d, bill_type=str(r[2] or "").strip(),
                customer_name=str(r[3] or "").strip(), customer_number=str(r[4] or "").strip(),
                amount=amt, received_amount=recv,
                balance_amount=round(amt - recv, 2),
                sales_dept=str(r[7] or "").strip(), salesman=str(r[8] or "").strip(),
                remark=str(r[9] or "").strip(),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_receivable_bill_no",
                set_=dict(amount=stmt.excluded.amount, received_amount=stmt.excluded.received_amount,
                          balance_amount=stmt.excluded.balance_amount),
            )
            db.execute(stmt)
            inserted += 1
        db.commit()
        log.rows_inserted = inserted
        log.status = "success"
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        return {"fetched": len(rows), "inserted": inserted}
    except Exception as e:
        db.rollback()
        log.status = "failed"
        log.error_msg = str(e)
        log.duration_sec = round(time.time() - t0, 1)
        db.commit()
        raise


def run_full_sync(start_date: str = "2021-01-01", end_date: str = None):
    """执行全量同步：物料 → 出库 → 回款 → 应收"""
    if not end_date:
        from dateutil.relativedelta import relativedelta
        end_date = (date.today().replace(day=1) + relativedelta(months=1)).isoformat()

    db = SessionLocal()
    client = KingdeeClient()
    client.login()
    print(f"[同步开始] {start_date} ~ {end_date}")

    results = {}
    # 1. 物料主数据
    print("  [1/4] 物料主数据...")
    results["material"] = sync_materials(db, client)
    print(f"    → {results['material']}")

    # 2. 销售出库
    print("  [2/4] 销售出库单...")
    results["outstock"] = sync_outstock(db, client, start_date, end_date)
    print(f"    → {results['outstock']}")

    # 3. 回款
    print("  [3/4] 收款单（回款）...")
    try:
        results["receive"] = sync_receive(db, client, start_date, end_date)
        print(f"    → {results['receive']}")
    except Exception as e:
        print(f"    ✗ 回款同步失败: {e}")
        results["receive"] = {"error": str(e)}

    # 4. 应收
    print("  [4/4] 应收单...")
    try:
        results["receivable"] = sync_receivable(db, client, start_date, end_date)
        print(f"    → {results['receivable']}")
    except Exception as e:
        print(f"    ✗ 应收同步失败: {e}")
        results["receivable"] = {"error": str(e)}

    db.close()
    print("[同步完成]")
    return results


def init_db():
    """创建数据库表"""
    Base.metadata.create_all(bind=engine)
    print("[数据库] 表已创建")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="金蝶数据同步")
    parser.add_argument("--init", action="store_true", help="创建数据库表")
    parser.add_argument("--start", default="2021-01-01", help="开始日期")
    parser.add_argument("--end", default=None, help="结束日期")
    args = parser.parse_args()

    if args.init:
        init_db()
    else:
        run_full_sync(args.start, args.end)
