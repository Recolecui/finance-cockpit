"""金蝶云星空 API 客户端 — 复用已验证的认证和查询逻辑"""
import requests
import json
import os
import time
from typing import Optional

K3_BASE_URL = os.getenv("K3_BASE_URL", "https://geshem.ik3cloud.com")
K3_ACCT_ID = os.getenv("K3_ACCT_ID", "1783990801475402752")
K3_USERNAME = os.getenv("K3_USERNAME", "")
K3_PASSWORD = os.getenv("K3_PASSWORD", "")

LOGIN_PATH = "/k3cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc"
QUERY_PATH = "/k3cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.ExecuteBillQuery.common.kdsvc"
PAGE_SIZE = 2000

# 产品分类规则（40开头=外购品，其余按物料分组前缀）
PREFIX_MAP = {
    "1010": "无风扇工控机", "1011": "无风扇工控机",
    "1020": "工业平板电脑",
    "1030": "手持强固平板",
    "1040": "工业显示器",
    "1050": "上架工控机",
    "1060": "壁挂工控机",
    "1080": "充电底座/支架",
    "1090": "加固便携设备",
    "7010": "结构套料", "7020": "外壳套料",
    "5010": "委外加工",
}


def normalize_code(code: str) -> str:
    """老格式编码（带点号）转新格式"""
    code = str(code or "").strip()
    if "." not in code:
        return code
    parts = code.split(".")
    if len(parts) < 2:
        return code.replace(".", "")
    cat = parts[0]
    if cat == "0":
        cat = "1"
    sub = parts[1][:2].zfill(3)
    rest = "".join(parts[2:]) if len(parts) > 2 else ""
    return cat + sub + rest


def classify_product(code: str, category: str = "") -> str:
    """物料编码 -> 产品大类"""
    code = normalize_code(str(code or ""))
    if not code:
        return "未分类"
    if code.startswith("40"):
        return "外购品"
    if category == "原材料":
        return "原材料"
    for prefix, name in PREFIX_MAP.items():
        if code.startswith(prefix):
            return name
    if category in ("产成品", "商品"):
        return "其他成品"
    if code.startswith("20"):
        return "原材料"
    return "未分类"


class KingdeeClient:
    def __init__(self):
        self.session: Optional[requests.Session] = None
        self.cookies = None

    def login(self):
        """登录金蝶云星空"""
        if not K3_USERNAME or not K3_PASSWORD:
            raise RuntimeError("K3_USERNAME 和 K3_PASSWORD 环境变量未设置")
        url = K3_BASE_URL + LOGIN_PATH
        resp = requests.post(url, data={
            "acctid": K3_ACCT_ID,
            "username": K3_USERNAME,
            "password": K3_PASSWORD,
            "lcid": 2052,
        }, timeout=30)
        result = resp.json()
        if result.get("LoginResultType") == 1:
            self.cookies = resp.cookies
            return True
        raise RuntimeError(f"金蝶登录失败: {result.get('Message', 'unknown')}")

    def query(self, form_id: str, field_keys: list, filter_string: str,
              order_string: str = "", start_row: int = 0, limit: int = PAGE_SIZE):
        """执行 executeBillQuery，返回 list of lists"""
        if not self.cookies:
            self.login()
        url = K3_BASE_URL + QUERY_PATH
        payload = {
            "data": json.dumps({
                "FormId": form_id,
                "FieldKeys": ",".join(field_keys),
                "FilterString": filter_string,
                "OrderString": order_string,
                "TopRowCount": 0,
                "StartRow": start_row,
                "Limit": limit,
                "SubSystemId": "",
            })
        }
        resp = requests.post(url, data=payload, cookies=self.cookies, timeout=60)
        data = resp.json()
        if isinstance(data, dict) and "Result" in data:
            errors = data["Result"].get("ResponseStatus", {}).get("Errors", [])
            if errors:
                msgs = [e["Message"] for e in errors]
                raise RuntimeError(f"查询失败: {msgs}")
        return data if isinstance(data, list) else []

    def query_all(self, form_id: str, field_keys: list, filter_string: str, order_string: str = ""):
        """分页拉取全部数据"""
        all_rows = []
        start = 0
        while True:
            rows = self.query(form_id, field_keys, filter_string, order_string, start)
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < PAGE_SIZE:
                break
            start += PAGE_SIZE
        return all_rows

    # ============ 销售出库单 SAL_OUTSTOCK ============
    OUTSTOCK_FIELDS = [
        "FBillNo", "FDate", "FBillTypeID.FName", "FDocumentStatus",
        "FCustomerID.FName", "FCustomerID.FNumber",
        "FMaterialID.FName", "FMaterialID.FNumber", "FMaterialID.FSpecification",
        "FRealQty", "FAmount", "FTaxAmount", "FAllAmount", "FTaxPrice",
        "FSaleOrgId.FName", "FSaleDeptID.FName", "FSalesmanID.FName",
        "FStockID.FName",
        "FNote", "FEntryNote", "FApproveDate",
    ]

    def fetch_outstock(self, start_date: str, end_date: str):
        """拉取销售出库单"""
        fields = self.OUTSTOCK_FIELDS
        filter_str = f"FDate>='{start_date}' AND FDate<'{end_date}' AND FDocumentStatus='C'"
        return self.query_all("SAL_OUTSTOCK", fields, filter_str, "FDate ASC")

    # ============ 收款单 AR_RECEIVEBILL ============
    RECEIVE_FIELDS = [
        "FBillNo", "FDate", "FBillTypeID.FName",
        "FCONTACTUNIT.FName", "FCONTACTUNIT.FNumber",
        "FRECTOTALAMOUNTFOR",
        "FCurrencyID.FName", "FSettleTypeID.FName",
        "FSaleDeptID.FName", "FSALEERID.FName",
        "FREMARK",
    ]

    def fetch_receive(self, start_date: str, end_date: str):
        """拉取收款单（回款）"""
        filter_str = f"FDate>='{start_date}' AND FDate<'{end_date}' AND FDocumentStatus='C'"
        return self.query_all("AR_RECEIVEBILL", self.RECEIVE_FIELDS, filter_str, "FDate ASC")

    # ============ 应收单 AR_receivable ============
    RECEIVABLE_FIELDS = [
        "FBillNo", "FDate", "FBillTypeID.FName",
        "FCustomerID.FName", "FCustomerID.FNumber",
        "FALLAMOUNTFOR", "FReceiveAmount",
        "FSaleDeptID.FName", "FSALEERID.FName",
        "FREMARK",
    ]

    def fetch_receivable(self, start_date: str, end_date: str):
        """拉取应收单"""
        filter_str = f"FDate>='{start_date}' AND FDate<'{end_date}' AND FDocumentStatus='C'"
        return self.query_all("AR_receivable", self.RECEIVABLE_FIELDS, filter_str, "FDate ASC")

    # ============ 物料主数据 BD_MATERIAL ============
    MATERIAL_FIELDS = [
        "FNumber", "FName", "FMaterialGroup.FNumber", "FMaterialGroup.FName",
        "FCategoryID.FName", "FErpClsID", "FBaseUnitId.FName", "FSpecification",
    ]

    def fetch_materials(self):
        """拉取全部物料主数据"""
        return self.query_all("BD_MATERIAL", self.MATERIAL_FIELDS, "FNumber <> ''", "FNumber ASC")

    # ============ 客户基础资料 BD_Customer（省份解析） ============
    CUSTOMER_FIELDS = [
        "FNumber", "FName", "FAddress",
    ]

    def fetch_customers(self):
        """拉取全部客户基础资料（含详细地址，用于省份解析）"""
        return self.query_all("BD_Customer", self.CUSTOMER_FIELDS, "FNumber <> ''", "FNumber ASC")

    # ============ 销售订单 SAL_SaleOrder（地域字段） ============
    SALEORDER_FIELDS = [
        "FBillNo", "FDate", "FBillTypeID.FName",
        "FCustomerID.FName", "FCustomerID.FNumber",
        "FMaterialID.FName", "FMaterialID.FNumber",
        "FQty", "FAmount", "FAllAmount",
        "FSaleDeptID.FName", "FSalesmanID.FName",
        "FRegionID.FName", "FRegionID.FNumber",
    ]

    def fetch_saleorders(self, start_date: str, end_date: str):
        """拉取销售订单（含地域字段 FRegionID）"""
        filter_str = f"FDate>='{start_date}' AND FDate<'{end_date}' AND FDocumentStatus='C'"
        return self.query_all("SAL_SaleOrder", self.SALEORDER_FIELDS, filter_str, "FDate ASC")
