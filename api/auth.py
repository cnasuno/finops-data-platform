import os
import secrets

from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader # HTTP 요청 헤더에서 API Key 추출
from fastapi import Depends

load_dotenv()

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


def get_current_role(api_key: str | None = Security(api_key_header)):
							   # 환경변수에서 저장된 키 읽기
    viewer_key = os.getenv("VIEWER_API_KEY")
    admin_key = os.getenv("ADMIN_API_KEY")

		# 서버 인증 설정 누락
    if not viewer_key or not admin_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured"
        )

		# 키 누락/불일치
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API Key is missing"
        )

		#  compare_digest: 일반 문자열 비교보다 타이밍 공격에 안전한 비교
    if secrets.compare_digest(api_key, admin_key):
        return "admin"

    if secrets.compare_digest(api_key, viewer_key):
        return "viewer"

    raise HTTPException(
        status_code=401,
        detail="Invalid API Key"
    )



# require_admin : 관리자 권한이 필요한 API에서 사용
def require_admin(role: str = Depends(get_current_role)):
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )

    return role


def mask_account_id(account_id: str) -> str:
    if len(account_id) <= 4:
        return "*" * len(account_id)

    return "*" * (len(account_id) - 4) + account_id[-4:]