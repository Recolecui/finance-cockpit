"""FastAPI 主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, dashboard
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = FastAPI(title="德航智能经营驾驶舱 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"app": "德航智能经营驾驶舱", "version": "1.0.0", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 定时同步任务（每天凌晨 2 点）
scheduler = BackgroundScheduler()

def scheduled_sync():
    """定时从金蝶同步数据"""
    from app.tasks.sync_data import run_full_sync
    from datetime import date
    try:
        run_full_sync("2021-01-01", date.today().isoformat())
    except Exception as e:
        print(f"[定时同步失败] {e}")

if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
    scheduler.add_job(scheduled_sync, "cron", hour=2, minute=0, id="daily_sync")
    scheduler.start()
    print("[调度器] 定时同步已启用（每天 02:00）")
