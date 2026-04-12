"""
Profile Verification Service
─────────────────────────────
Analyzes GitHub and LeetCode profiles using free public APIs.
Other profile links (LinkedIn, Portfolio, etc.) are classified but not scraped.
"""

import os
import re
import logging
import requests
from typing import Optional
from urllib.parse import urlparse

from services.linkedin_extraction import get_full_candidate_profile

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# URL CLASSIFICATION
# ─────────────────────────────────────────────────────────

PLATFORM_PATTERNS = {
    "github": [
        r"github\.com/([A-Za-z0-9_.-]+)",
    ],
    "leetcode": [
        r"leetcode\.com/u/([A-Za-z0-9_.-]+)",
        r"leetcode\.com/([A-Za-z0-9_.-]+)/?$",
    ],
    "linkedin": [
        r"linkedin\.com/in/([A-Za-z0-9_.-]+)",
    ],
    "twitter": [
        r"twitter\.com/([A-Za-z0-9_]+)",
        r"x\.com/([A-Za-z0-9_]+)",
    ],
    "kaggle": [
        r"kaggle\.com/([A-Za-z0-9_.-]+)",
    ],
}

# Pages on GitHub that are NOT user profiles
GITHUB_RESERVED = {
    "features", "explore", "topics", "trending", "collections",
    "events", "sponsors", "settings", "notifications", "marketplace",
    "pulls", "issues", "codespaces", "orgs", "login", "signup",
    "about", "pricing", "enterprise", "team", "security", "site",
}


def classify_url(url: str) -> dict:
    """Classify a URL by platform and extract the username."""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                username = match.group(1).rstrip("/")

                # Filter out GitHub reserved paths
                if platform == "github" and username.lower() in GITHUB_RESERVED:
                    continue

                return {
                    "platform": platform,
                    "username": username,
                    "url": url,
                }

    return {
        "platform": "other",
        "username": None,
        "url": url,
    }


# ─────────────────────────────────────────────────────────
# GITHUB ANALYSIS (free REST API)
# ─────────────────────────────────────────────────────────

def _github_headers() -> dict:
    """Build headers for GitHub API, optionally with token."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def analyze_github_profile(username: str) -> dict:
    """Fetch and analyze a GitHub profile using the public REST API."""
    base = "https://api.github.com"
    headers = _github_headers()
    result = {"platform": "github", "username": username, "status": "success"}

    try:
        # 1. User info
        user_resp = requests.get(f"{base}/users/{username}", headers=headers, timeout=10)
        if user_resp.status_code == 404:
            return {**result, "status": "not_found", "error": f"GitHub user '{username}' not found"}
        if user_resp.status_code == 403:
            return {**result, "status": "rate_limited", "error": "GitHub API rate limit reached"}
        user_resp.raise_for_status()
        user = user_resp.json()

        result["user"] = {
            "name": user.get("name") or username,
            "bio": user.get("bio") or "",
            "avatar_url": user.get("avatar_url", ""),
            "html_url": user.get("html_url", f"https://github.com/{username}"),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "created_at": user.get("created_at", ""),
            "location": user.get("location") or "",
            "company": user.get("company") or "",
            "blog": user.get("blog") or "",
        }

        # 2. Top repositories (sorted by stars)
        repos_resp = requests.get(
            f"{base}/users/{username}/repos",
            headers=headers,
            params={"sort": "stars", "direction": "desc", "per_page": 30, "type": "owner"},
            timeout=10,
        )
        repos_resp.raise_for_status()
        repos = repos_resp.json()

        # Aggregate stats
        total_stars = 0
        total_forks = 0
        language_stats = {}

        top_repos = []
        for repo in repos[:10]:
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            lang = repo.get("language")
            total_stars += stars
            total_forks += forks

            if lang:
                language_stats[lang] = language_stats.get(lang, 0) + 1

            top_repos.append({
                "name": repo.get("name", ""),
                "description": (repo.get("description") or "")[:120],
                "language": lang or "N/A",
                "stars": stars,
                "forks": forks,
                "html_url": repo.get("html_url", ""),
                "updated_at": repo.get("updated_at", ""),
                "is_fork": repo.get("fork", False),
            })

        # Full language aggregation across all fetched repos
        for repo in repos:
            lang = repo.get("language")
            if lang and repo not in repos[:10]:
                language_stats[lang] = language_stats.get(lang, 0) + 1

        # Sort languages by count
        sorted_langs = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)

        result["repos"] = top_repos
        result["stats"] = {
            "total_stars": total_stars,
            "total_forks": total_forks,
            "total_repos": user.get("public_repos", len(repos)),
        }
        result["languages"] = [{"name": lang, "count": count} for lang, count in sorted_langs]

    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API error for {username}: {e}")
        result["status"] = "error"
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────
# LEETCODE ANALYSIS (public GraphQL API)
# ─────────────────────────────────────────────────────────

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

LEETCODE_PROFILE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      realName
      aboutMe
      ranking
      reputation
      starRating
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    badges {
      name
    }
  }
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
    topPercentage
  }
}
"""


def analyze_leetcode_profile(username: str) -> dict:
    """Fetch and analyze a LeetCode profile using the public GraphQL API."""
    result = {"platform": "leetcode", "username": username, "status": "success"}

    try:
        resp = requests.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": LEETCODE_PROFILE_QUERY, "variables": {"username": username}},
            headers={
                "Content-Type": "application/json",
                "Referer": f"https://leetcode.com/u/{username}/",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

        user = data.get("matchedUser")
        if not user:
            return {**result, "status": "not_found", "error": f"LeetCode user '{username}' not found"}

        profile = user.get("profile", {})

        # Parse submission stats
        submissions = user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
        solved = {"All": 0, "Easy": 0, "Medium": 0, "Hard": 0}
        for s in submissions:
            diff = s.get("difficulty", "All")
            solved[diff] = s.get("count", 0)

        # Contest info
        contest = data.get("userContestRanking") or {}

        result["user"] = {
            "name": profile.get("realName") or username,
            "about": profile.get("aboutMe", ""),
            "ranking": profile.get("ranking", 0),
            "reputation": profile.get("reputation", 0),
            "star_rating": profile.get("starRating", 0),
            "html_url": f"https://leetcode.com/u/{username}/",
        }

        result["solved"] = {
            "total": solved.get("All", 0),
            "easy": solved.get("Easy", 0),
            "medium": solved.get("Medium", 0),
            "hard": solved.get("Hard", 0),
        }

        result["contest"] = {
            "attended": contest.get("attendedContestsCount", 0),
            "rating": round(contest.get("rating", 0), 1) if contest.get("rating") else 0,
            "global_ranking": contest.get("globalRanking", 0),
            "top_percentage": round(contest.get("topPercentage", 0), 2) if contest.get("topPercentage") else 0,
        }

        result["badges"] = [b.get("name", "") for b in user.get("badges", [])]

    except requests.exceptions.RequestException as e:
        logger.error(f"LeetCode API error for {username}: {e}")
        result["status"] = "error"
        result["error"] = str(e)

    return result


# ─────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────

def classify_and_analyze_profiles(urls: list[str]) -> list[dict]:
    """
    Takes a list of profile URLs, classifies each, and runs
    platform-specific analysis for GitHub and LeetCode.
    Other platforms are returned as classified links.
    """
    results = []

    for url in urls:
        if not url or not url.strip():
            continue

        info = classify_url(url)
        platform = info["platform"]
        username = info["username"]

        try:
            if platform == "github" and username:
                analysis = analyze_github_profile(username)
                results.append(analysis)

            elif platform == "leetcode" and username:
                analysis = analyze_leetcode_profile(username)
                results.append(analysis)

            elif platform == "linkedin" and username:
                analysis = get_full_candidate_profile(info["url"])
                results.append({
                    "platform": "linkedin",
                    "username": username,
                    "url": info["url"],
                    "status": "success",
                    "data": analysis
                })

            else:
                # Twitter, Kaggle, Portfolio, etc.
                results.append({
                    "platform": platform,
                    "username": username,
                    "url": info["url"],
                    "status": "link_only",
                })

        except Exception as e:
            logger.error(f"Error analyzing {url}: {e}")
            results.append({
                "platform": platform,
                "username": username,
                "url": info["url"],
                "status": "error",
                "error": str(e),
            })

    return results
