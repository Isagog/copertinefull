from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from ..includes.auth import oauth2_scheme
from typing import Callable
import jwt
from ..includes.auth import SECRET_KEY, ALGORITHM

async def auth_middleware(request: Request, call_next: Callable):
    # List of paths that don't require authentication
    public_paths = [
        "/auth/register",
        "/auth/login",
        "/auth/verify-email",
        "/auth/reset-password-request",
        "/auth/reset-password-confirm",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health"
    ]
    
    # Allow OPTIONS requests and public paths without authentication
    if request.method == "OPTIONS" or any(request.url.path.endswith(path) for path in public_paths):
        return await call_next(request)
    
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header.split(" ")[1]
        
        # Verify the token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user_email = payload.get("sub")
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Continue with the request
        response = await call_next(request)
        return response
        
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )
    except Exception as exc:
        print(f"Error in auth middleware: {exc}")  # Add logging
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
