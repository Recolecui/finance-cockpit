"""企业微信 OAuth + JWT 鉴权"""
import requests
import time
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

WECOM_ACCESS_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
WECOM_USER_INFO_URL = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
WECOM_USER_DETAIL_URL = "https://qyapi.weixin.qq.com/cgi-bin/user/get"

# 内存缓存 access_token
_token_cache = {"token": None, "expires": 0}


def get_wecom_access_token() -> str:
    """获取企业微信 access_token（带缓存）"""
    if _token_cache["token"] and time.time() < _token_cache["expires"]:
        return _token_cache["token"]
    resp = requests.get(WECOM_ACCESS_TOKEN_URL, params={
        "corpid": settings.WECOM_CORP_ID,
        "corpsecret": settings.WECOM_SECRET,
    }, timeout=10)
    data = resp.json()
    if data.get("errcode"):
        raise HTTPException(500, f"企业微信获取token失败: {data.get('errmsg')}")
    _token_cache["token"] = data["access_token"]
    _token_cache["expires"] = time.time() + data.get("expires_in", 7200) - 300
    return _token_cache["token"]


def create_jwt(user_id: str, name: str) -> str:
    payload = {
        "sub": user_id,
        "name": name,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "无效的 token")


def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未提供认证信息")
    return verify_jwt(auth[7:])


@router.get("/login")
def login():
    """企业微信 OAuth 登录入口"""
    if not settings.WECOM_CORP_ID:
        # 开发模式：跳过 OAuth，直接返回开发 token
        token = create_jwt("dev-user", "开发者")
        return {"token": token, "name": "开发者", "dev_mode": True}
    url = (
        f"https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={settings.WECOM_CORP_ID}"
        f"&redirect_uri={settings.WECOM_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=snsapi_privateinfo"
        f"&agentid={settings.WECOM_AGENT_ID}"
        f"#wechat_redirect"
    )
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, db: Session = Depends(get_db)):
    """企业微信 OAuth 回调"""
    token = get_wecom_access_token()
    # 用 code 换 userid
    resp = requests.get(WECOM_USER_INFO_URL, params={
        "access_token": token, "code": code,
    }, timeout=10)
    data = resp.json()
    if data.get("errcode"):
        raise HTTPException(400, f"获取用户信息失败: {data.get('errmsg')}")
    user_id = data.get("userid") or data.get("UserId")
    if not user_id:
        raise HTTPException(400, "未获取到用户ID")

    # 获取用户详情
    resp2 = requests.get(WECOM_USER_DETAIL_URL, params={
        "access_token": token, "userid": user_id,
    }, timeout=10)
    detail = resp2.json()
    name = detail.get("name", user_id)

    jwt_token = create_jwt(user_id, name)
    # 重定向到前端，带 token
    frontend_url = settings.CORS_ORIGINS[0].rstrip("/")
    return RedirectResponse(f"{frontend_url}/?token={jwt_token}&name={name}")


@router.get("/verify")
def verify(current_user: dict = Depends(get_current_user)):
    """验证当前 token 是否有效"""
    return {"user_id": current_user["sub"], "name": current_user["name"]}
