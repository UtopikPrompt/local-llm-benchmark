"""JWT Authentication module.

Provides JWT-based authentication with role-based access control
for the local-llm-benchmark API.
"""

import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Any

import jwt
from jwt import PyJWTError

from local_llm_benchmark.config import Role, TokenConfig


class AuthenticationError(Exception):
    """Base exception for authentication-related errors."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when the JWT token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when the JWT token is invalid."""
    pass


class InsufficientPermissionError(AuthenticationError):
    """Raised when the authenticated user lacks required permissions."""
    pass


class JWTPayload:
    """Payload for JWT tokens."""
    
    def __init__(self, user_id: str, roles: list[str], email: str | None = None):
        self.user_id = user_id
        self.roles = roles
        self.email = email
        self.exp = datetime.utcnow() + TokenConfig.token_expiry
        self.iat = datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert payload to dictionary."""
        return {
            "user_id": self.user_id,
            "roles": self.roles,
            "email": self.email,
            "exp": self.exp.isoformat(),
            "iat": self.iat.isoformat(),
        }


class JWTCoder:
    """JWT token encoder and decoder."""
    
    def __init__(self, secret: str):
        self.secret = secret
    
    def encode(self, payload: JWTPayload) -> str:
        """Encode a payload into a JWT token."""
        token = jwt.encode(
            payload.to_dict(),
            self.secret,
            algorithm="HS256",
            headers={"type": "access_token"}
        )
        return token
    
    def decode(self, token: str) -> JWTPayload:
        """Decode and validate a JWT token."""
        try:
            decoded = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,
                    "verify_iss": False,
                }
            )
            return JWTPayload(
                user_id=decoded["user_id"],
                roles=decoded["roles"],
                email=decoded.get("email"),
            )
        except PyJWTError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}") from e


class UserAuthenticator:
    """User authentication service."""
    
    def __init__(self, secret: str, token_config: TokenConfig):
        self.secret = secret
        self.token_config = token_config
        self.coder = JWTCoder(secret)
    
    def create_token(self, user_id: str, roles: list[str], email: str | None = None) -> str:
        """Create a new JWT token for the given user."""
        payload = JWTPayload(user_id, roles, email)
        return self.coder.encode(payload)
    
    def verify_token(self, token: str) -> JWTPayload:
        """Verify and decode a JWT token."""
        return self.coder.decode(token)
    
    def check_permission(self, user_roles: list[str], required_role: str) -> bool:
        """Check if user has required role."""
        return required_role in user_roles
    
    def is_expired(self, token: str) -> bool:
        """Check if token has expired."""
        try:
            payload = self.verify_token(token)
            return payload.exp < datetime.utcnow()
        except (InvalidTokenError, TokenExpiredError):
            return True
    
    def get_user_info(self, token: str) -> dict[str, Any]:
        """Get user information from token."""
        try:
            payload = self.verify_token(token)
            return {
                "user_id": payload.user_id,
                "roles": payload.roles,
                "email": payload.email,
                "is_authenticated": True,
            }
        except (InvalidTokenError, TokenExpiredError):
            return {
                "user_id": None,
                "roles": [],
                "email": None,
                "is_authenticated": False,
            }
    
    def refresh_token(self, token: str) -> str:
        """Create a new token with extended expiry."""
        try:
            payload = self.verify_token(token)
            new_payload = JWTPayload(
                user_id=payload.user_id,
                roles=payload.roles,
                email=payload.email,
            )
            return self.coder.encode(new_payload)
        except (InvalidTokenError, TokenExpiredError):
            raise TokenExpiredError("Cannot refresh expired token")


def get_current_user(authorization: str | None) -> dict[str, Any]:
    """Extract and validate current user from authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User information dictionary
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    authenticator = UserAuthenticator(
        secret=TokenConfig.secret,
        token_config=TokenConfig,
    )
    payload = authenticator.verify_token(token)
    
    return {
        "user_id": payload.user_id,
        "roles": payload.roles,
        "email": payload.email,
    }


def require_auth(dependency: Any) -> Any:
    """FastAPI dependency for authentication.
    
    Decorator to require authentication on routes.
    """
    async def auth_dependency(request):
        try:
            user = get_current_user(request.headers.get("Authorization"))
            return {"user": user}
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
    
    return dependency


def require_role(role: str, dependency: Any) -> Any:
    """FastAPI dependency for role-based access control.
    
    Decorator to require specific role on authenticated routes.
    """
    async def role_dependency(request):
        try:
            user = get_current_user(request.headers.get("Authorization"))
            if not user["roles"] or role not in user["roles"]:
                raise InsufficientPermissionError(
                    f"User does not have required role: {role}"
                )
            return {"user": user}
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except InsufficientPermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
    
    return role_dependency


def get_token_from_request(request) -> str:
    """Extract JWT token from request headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        JWT token string
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return ""
    return auth_header[7:]


def validate_request_size(request) -> bool:
    """Validate request size against configured limits.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        True if request is within limits
    """
    max_size = TokenConfig.max_request_size
    content_length = request.headers.get("content-length")
    
    if content_length is None:
        return True
    
    try:
        size = int(content_length)
        return size <= max_size
    except ValueError:
        return True


def sanitize_input(value: str) -> str:
    """Sanitize string input to prevent injection attacks.
    
    Args:
        value: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Remove potentially dangerous patterns
    sanitized = value.strip()
    
    # Remove SQL injection patterns
    sanitized = re.sub(r";\s*--", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"'\s*OR\s*'", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"'\s*AND\s*'", "", sanitized, flags=re.IGNORECASE)
    
    # Remove command injection patterns
    sanitized = re.sub(r"\|\s*cat\s", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\|\s*bash\s", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"&&\s*rm\s", "", sanitized, flags=re.IGNORECASE)
    
    # Limit length
    max_length = TokenConfig.max_input_length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_request_data(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize request data.
    
    Args:
        data: Request payload
        
    Returns:
        Validated and sanitized data
    """
    if not isinstance(data, dict):
        raise ValueError("Request data must be a dictionary")
    
    validated = {}
    for key, value in data.items():
        if isinstance(value, str):
            validated[key] = sanitize_input(value)
        elif isinstance(value, (list, dict)):
            validated[key] = validate_request_data(value)
        else:
            validated[key] = value
    
    return validated


def validate_request_size(data: dict[str, Any]) -> bool:
    """Validate request data against size limits.
    
    Args:
        data: Request payload
        
    Returns:
        True if within limits
    """
    max_size = TokenConfig.max_request_size
    
    def calculate_size(obj):
        """Calculate approximate size of data structure."""
        if isinstance(obj, str):
            return len(obj.encode("utf-8"))
        elif isinstance(obj, dict):
            return sum(calculate_size(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(calculate_size(item) for item in obj)
        else:
            return 0
    
    return calculate_size(data) <= max_size
