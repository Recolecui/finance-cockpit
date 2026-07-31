"""PostgreSQL 数据模型 — 德航智能经营驾驶舱"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.database import Base


class SalesOutstock(Base):
    """销售出库单（金蝶 SAL_OUTSTOCK）"""
    __tablename__ = "sales_outstock"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_no = Column(String(64), nullable=False, index=True)          # 单据编号
    bill_date = Column(Date, nullable=False, index=True)               # 日期
    bill_type = Column(String(64))                                     # 单据类型（标准销售出库单/售后维修领料单）
    doc_status = Column(String(16))                                    # 单据状态（C=已审核）

    customer_name = Column(String(256), nullable=False, index=True)    # 客户名称
    customer_number = Column(String(64))                                # 客户编码

    material_name = Column(String(256), nullable=False, index=True)    # 物料名称
    material_number = Column(String(64), nullable=False, index=True)   # 物料编码
    product_category = Column(String(64), index=True)                  # 产品大类（从物料主数据分类）
    spec = Column(String(256))                                         # 规格型号

    qty = Column(Float, default=0)                                       # 实发数量
    amount = Column(Float, default=0)                                   # 金额（本位币）
    tax_amount = Column(Float, default=0)                               # 税额
    total_amount = Column(Float, default=0)                             # 价税合计（本位币）
    unit_price = Column(Float, default=0)                               # 含税单价

    sales_org = Column(String(128))                                    # 销售组织
    sales_dept = Column(String(128), index=True)                       # 销售部门
    salesman = Column(String(64), index=True)                          # 业务员
    warehouse = Column(String(128))                                    # 仓库

    region = Column(String(64), index=True)                             # 地域（预留，目前由 province 填充）
    province = Column(String(32), index=True)                          # 省份（优先按客户地址 FAddress 解析，回退客户名关键词）
    is_overseas = Column(Integer, default=0)                            # 是否海外

    note = Column(Text)                                                 # 备注
    entry_note = Column(Text)                                           # 明细备注
    approve_date = Column(DateTime)                                     # 审核日期

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("bill_no", "material_number", name="uq_outstock_bill_material"),
        Index("ix_outstock_date_type", "bill_date", "bill_type"),
        Index("ix_outstock_customer_date", "customer_name", "bill_date"),
    )


class ReceiveBill(Base):
    """收款单（金蝶 AR_RECEIVEBILL）— 回款"""
    __tablename__ = "receive_bill"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_no = Column(String(64), nullable=False, index=True)
    bill_date = Column(Date, nullable=False, index=True)
    bill_type = Column(String(64))

    customer_name = Column(String(256), nullable=False, index=True)
    customer_number = Column(String(64))
    province = Column(String(32), index=True)                          # 省份（同步时按客户地图填充）

    receive_amount = Column(Float, default=0)                          # 收款金额（本位币）
    receive_qty = Column(Float, default=0)                              # 收款数量
    currency = Column(String(16))                                      # 币别
    settle_type = Column(String(64))                                   # 结算方式

    sales_dept = Column(String(128), index=True)
    salesman = Column(String(64), index=True)

    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("bill_no", name="uq_receive_bill_no"),
    )


class Receivable(Base):
    """应收单（金蝶 AR_receivable）"""
    __tablename__ = "receivable"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_no = Column(String(64), nullable=False, index=True)
    bill_date = Column(Date, nullable=False, index=True)
    bill_type = Column(String(64))

    customer_name = Column(String(256), nullable=False, index=True)
    customer_number = Column(String(64))
    province = Column(String(32), index=True)                          # 省份（同步时按客户地图填充）

    amount = Column(Float, default=0)                                   # 应收金额
    received_amount = Column(Float, default=0)                          # 已收金额
    balance_amount = Column(Float, default=0)                           # 未收余额
    overdue_amount = Column(Float, default=0)                           # 逾期金额

    sales_dept = Column(String(128), index=True)
    salesman = Column(String(64), index=True)

    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("bill_no", name="uq_receivable_bill_no"),
    )


class Material(Base):
    """物料主数据（金蝶 BD_MATERIAL）"""
    __tablename__ = "material"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_number = Column(String(64), nullable=False, unique=True, index=True)
    material_name = Column(String(256), nullable=False)
    material_group_code = Column(String(64))                            # 物料分组编码
    material_group_name = Column(String(128))                           # 物料分组名称
    category = Column(String(64), index=True)                           # 类别（原材料/产成品/商品等）
    product_category = Column(String(64), index=True)                  # 产品大类（分类后的）
    spec = Column(String(256))                                          # 规格型号
    erp_cls = Column(Integer)                                           # ERP分类（1=外购 2=自制）
    unit = Column(String(32))                                           # 基本单位

    created_at = Column(DateTime, default=datetime.utcnow)


class SyncLog(Base):
    """数据同步日志"""
    __tablename__ = "sync_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type = Column(String(64), nullable=False)                      # outstock/receive/receivable/material
    start_date = Column(Date)
    end_date = Column(Date)
    rows_fetched = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    duration_sec = Column(Float, default=0)
    status = Column(String(16), default="running")                     # running/success/failed
    error_msg = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
