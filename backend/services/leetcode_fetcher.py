import asyncio
import re
from typing import Dict, Any
import httpx

async def fetch_leetcode_profile(url: str) -> Dict[str, Any]:
    """
    Fetch LeetCode profile data from a URL or username.
    """
    # Extract username from URL
    username = extract_username_from_url(url)
    if not username:
        return {"error": "Invalid LeetCode URL or username"}

    # GraphQL queries
    profile_query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        username
        profile {
          realName
          aboutMe
          country
          skillTags
          reputation
          ranking
        }
        submitStats {
          acSubmissionNum {
            difficulty
            count
            submissions
          }
        }
      }
    }
    """

    contest_query = """
    query getUserContestRanking($username: String!) {
      userContestRanking(username: $username) {
        rating
        globalRanking
        totalParticipants
        topPercentage
      }
    }
    """

    variables = {"username": username}

    async with httpx.AsyncClient() as client:
        try:
            # Run both queries in parallel
            profile_task = client.post(
                "https://leetcode.com/graphql",
                json={"query": profile_query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )
            contest_task = client.post(
                "https://leetcode.com/graphql",
                json={"query": contest_query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )

            profile_response, contest_response = await asyncio.gather(profile_task, contest_task)

            profile_data = profile_response.json()
            contest_data = contest_response.json()

            # Check if user exists
            if not profile_data.get("data", {}).get("matchedUser"):
                return {"error": "LeetCode profile not found"}

            user = profile_data["data"]["matchedUser"]
            profile = user.get("profile", {})
            submit_stats = user.get("submitStats", {}).get("acSubmissionNum", [])

            # Parse problems solved
            problems_solved = {"total": 0, "easy": 0, "medium": 0, "hard": 0}
            for stat in submit_stats:
                difficulty = stat.get("difficulty", "").lower()
                count = stat.get("count", 0)
                if difficulty in problems_solved:
                    problems_solved[difficulty] = count
                problems_solved["total"] += count

            # Contest data
            contest = contest_data.get("data", {}).get("userContestRanking", {})

            return {
                "username": user.get("username"),
                "real_name": profile.get("realName"),
                "country": profile.get("country"),
                "skills": profile.get("skillTags", []),
                "reputation": profile.get("reputation"),
                "global_ranking": profile.get("ranking"),
                "problems_solved": problems_solved,
                "contest_rating": contest.get("rating"),
                "contest_global_ranking": contest.get("globalRanking"),
                "top_percentage": contest.get("topPercentage")
            }

        except Exception as e:
            return {"error": "Failed to fetch LeetCode profile"}

def extract_username_from_url(url: str) -> str:
    """
    Extract username from LeetCode URL or return as-is if plain username.
    """
    # Patterns for LeetCode URLs
    patterns = [
        r"https?://leetcode\.com/u/([^/]+)/?",  # https://leetcode.com/u/username/
        r"https?://leetcode\.com/([^/]+)/?",  # https://leetcode.com/username/
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no URL pattern matches, assume it's a plain username
    return url.strip()