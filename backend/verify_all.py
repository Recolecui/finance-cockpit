import urllib.request, json

BASE = "http://localhost:8080"

def post_login():
    req = urllib.request.Request(
        BASE + "/api/auth/login/password",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read()).get("token", "")

def get(path, tok):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {tok}"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

tok = post_login()
print("TOK_LEN", len(tok))

for path in [
    "/api/dashboard/kpi",
    "/api/dashboard/trend?months=36",
    "/api/dashboard/product-structure?mode=month",
    "/api/dashboard/growth?year=2026",
    "/api/dashboard/region?metric=receivable",
]:
    try:
        d = get(path, tok)
        s = json.dumps(d, ensure_ascii=False)
        print(f"\n### {path}")
        print("  type:", type(d).__name__, "| keys/len:", (list(d.keys()) if isinstance(d, dict) else len(d)))
        print("  sample:", s[:400])
    except Exception as e:
        print(f"\n### {path}  ERROR: {e}")
