"""测试金蝶API字段"""
from app.services.kingdee import KingdeeClient

c = KingdeeClient()
c.login()
print("[登录成功]")

# 测试1: 基础字段
fields_basic = ["FBillNo", "FDate", "FBillTypeID.FName", "FDocumentStatus",
                "FCustomerID.FName", "FCustomerID.FNumber",
                "FMaterialID.FName", "FMaterialID.FNumber"]
rows = c.query("SAL_OUTSTOCK", fields_basic,
               "FDate>='2025-01-01' AND FDate<'2025-02-01' AND FDocumentStatus='C'",
               "", 0, 3)
print(f"\n[基础字段] 返回 {len(rows)} 行")
for r in rows:
    print(f"  len={len(r)}: {r}")

# 测试2: 加更多字段
fields_more = ["FBillNo", "FDate", "FBillTypeID.FName", "FDocumentStatus",
               "FCustomerID.FName", "FCustomerID.FNumber",
               "FMaterialID.FName", "FMaterialID.FNumber", "FMaterialGroup.FNumber",
               "FSpecification", "FRealQty", "FAmount", "FAllAmount",
               "FSaleDeptID.FName", "FSalesmanID.FName"]
rows2 = c.query("SAL_OUTSTOCK", fields_more,
                "FDate>='2025-01-01' AND FDate<'2025-02-01' AND FDocumentStatus='C'",
                "", 0, 3)
print(f"\n[扩展字段] 返回 {len(rows2)} 行")
for r in rows2:
    print(f"  len={len(r)}: {r}")
