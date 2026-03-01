# app/utils/rate_limiter.py
import time
from app.cache import get_redis
from fastapi import Request, HTTPException



class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        """
        max_requests  — how many requests allowed in the window
        window_seconds — how long the window is (e.g. 60 = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if this identifier (IP address) is within the rate limit.

        Returns a tuple:
        - bool: True if request is allowed, False if blocked
        - dict: metadata about current limit status (useful for headers)
        """
        r = get_redis()

        # Key pattern: rate:{identifier}:{current_window}
        # Current window is the current minute/period as a unix timestamp
        # This naturally resets every window_seconds seconds
        current_window = int(time.time() // self.window_seconds)
        key = f"rate:{identifier}:{current_window}"

        # Redis pipeline — executes both commands in one round trip
        # Much faster than two separate Redis calls
        pipe = r.pipeline()
        pipe.incr(key)           # increment counter (creates key at 1 if doesn't exist)
        pipe.expire(key, self.window_seconds * 2)  # set expiry (2x window for safety)
        results = pipe.execute()

        current_count = results[0]   # result of INCR
        remaining = max(0, self.max_requests - current_count)
        is_allowed = current_count <= self.max_requests

        metadata = {
            "limit": self.max_requests,
            "remaining": remaining,
            "current_count": current_count,
            "window_seconds": self.window_seconds,
            "reset_in": self.window_seconds - (int(time.time()) % self.window_seconds)
        }

        return is_allowed, metadata


# Pre-built limiters for each endpoint
# Create them once at module level — no need to recreate on every request
create_url_limiter = RateLimiter(max_requests=10, window_seconds=60)
redirect_limiter = RateLimiter(max_requests=60, window_seconds=60)
analytics_limiter = RateLimiter(max_requests=30, window_seconds=60)

# app/utils/rate_limiter.py  (add this to the bottom of the file)
from fastapi import Request, HTTPException


def check_rate_limit(limiter: RateLimiter):
    """
    Returns a FastAPI dependency function for the given limiter.

    Usage in a route:
    @router.post("/urls", dependencies=[Depends(check_rate_limit(create_url_limiter))])
    """
    def dependency(request: Request):
        # Use IP address as the identifier
        # X-Forwarded-For header contains real IP when behind a proxy/load balancer
        ip = request.headers.get("X-Forwarded-For", request.client.host)

        # X-Forwarded-For can contain multiple IPs — take the first one
        # Format: "client_ip, proxy1_ip, proxy2_ip"
        ip = ip.split(",")[0].strip()

        allowed, metadata = limiter.is_allowed(ip)

        if not allowed:
            raise HTTPException(
                status_code=429,   # 429 Too Many Requests
                detail={
                    "error": "Rate limit exceeded",
                    "limit": metadata["limit"],
                    "window_seconds": metadata["window_seconds"],
                    "reset_in_seconds": metadata["reset_in"],
                    "message": f"Max {metadata['limit']} requests per "
                               f"{metadata['window_seconds']} seconds"
                },
                headers={
                    # Standard rate limit headers — clients can read these
                    # to know when to retry
                    "Retry-After": str(metadata["reset_in"]),
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                }
            )

    return dependency