import asyncio
from app.middleware.rate_limit import RateLimiter
from app.db.redis import init_redis

async def main():
    await init_redis()
    rl = RateLimiter()
    for i in range(12):
        res = await rl.is_allowed("test_user_script", "anonymous")
        print(f"Request {i}: allowed={res[0]}, retry_after={res[1]}")

if __name__ == "__main__":
    asyncio.run(main())
