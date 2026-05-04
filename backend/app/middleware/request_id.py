"""Request ID 미들웨어 - 각 요청에 고유 UUID 할당 및 로깅 통합."""

import uuid
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Awaitable, Callable

# 전역 컨텍스트 변수 (비동기 요청 간 공유)
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """현재 요청의 Request ID 조회"""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Request ID 미들웨어

    각 요청에 고유한 UUID를 할당하고, 응답 헤더에도 포함합니다.
    이미 X-Request-ID 헤더가 있으면 그것을 사용합니다.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 기존 Request ID 확인 또는 새 UUID 생성
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # 컨텍스트에 저장 (비동기 요청 간 공유)
        token = request_id_var.set(request_id)

        try:
            response = await call_next(request)

            # 응답 헤더에 Request ID 추가
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            # 컨텍스트 정리
            request_id_var.reset(token)


class LoggingMiddleware(BaseHTTPMiddleware):
    """로깅 미들웨어 - 모든 요청/응답 정보를 로깅합니다."""

    async def dispatch(self, request: Request, call_next) -> Response:
        import time
        from app.logger import get_logger

        logger = get_logger()
        request_id = get_request_id() or "unknown"

        start_time = time.time()

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            # 요청 정보 로깅
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                },
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # 에러 로깅
            logger.error(
                f"{request.method} {request.url.path} ERROR",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True,
            )

            raise
