"""간단한 JWT 기반 기기 인증.

복잡한 사용자 관리는 두지 않는다(사용자 본인만 사용). 허용된 기기 ID 로
토큰을 발급하고, 요청의 ``Authorization`` 헤더를 검증한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from config_server import ALGORITHM, ALLOWED_DEVICES, SECRET_KEY, TOKEN_EXPIRE


def create_token(device_id: str) -> str:
    """``device_id`` 를 페이로드에 담은 JWT 를 반환한다. 유효기간 TOKEN_EXPIRE(분)."""
    if ALLOWED_DEVICES and device_id not in ALLOWED_DEVICES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="등록되지 않은 기기입니다.",
        )
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE)
    payload = {"sub": device_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    """토큰을 검증하고 ``device_id`` 를 반환한다. 실패 시 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 인증 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_error from exc

    device_id = payload.get("sub")
    if not device_id:
        raise credentials_error
    if ALLOWED_DEVICES and device_id not in ALLOWED_DEVICES:
        raise credentials_error
    return device_id


def get_current_device(request: Request) -> str:
    """``Authorization`` 헤더에서 device_id 를 추출한다.

    FastAPI ``Depends`` 로 사용한다.
    """
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 헤더가 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(token)
