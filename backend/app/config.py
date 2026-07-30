"""FastAPI 配置"""
import os

class Settings:
    # 数据库
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/finance_cockpit")

    # 企业微信 OAuth
    WECOM_CORP_ID = os.getenv("WECOM_CORP_ID", "")
    WECOM_AGENT_ID = os.getenv("WECOM_AGENT_ID", "")
    WECOM_SECRET = os.getenv("WECOM_SECRET", "")
    WECOM_REDIRECT_URI = os.getenv("WECOM_REDIRECT_URI", "https://cockpit.geshemsoft.com/api/auth/callback")

    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = 72

    # 金蝶
    K3_BASE_URL = os.getenv("K3_BASE_URL", "https://geshem.ik3cloud.com")
    K3_ACCT_ID = os.getenv("K3_ACCT_ID", "1783990801475402752")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://cockpit.geshemsoft.com").split(",")

settings = Settings()
