import asyncio
import os
from dotenv import load_dotenv

load_dotenv("d:/parser/.env")

from backend.services.github_fetcher import fetch_github_profile
from backend.services.leetcode_fetcher import fetch_leetcode_profile

async def main():
    try:
        gh = await fetch_github_profile("https://github.com/torvalds")
        print("GitHub SUCCESS")
    except Exception as e:
        print(f"GitHub ERROR: {e}")

    try:
        lc = await fetch_leetcode_profile("https://leetcode.com/u/neal_wu/")
        print("LeetCode SUCCESS")
    except Exception as e:
        print(f"LeetCode ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
