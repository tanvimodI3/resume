import os
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GITHUB_API_BASE = "https://api.github.com"

def extract_github_username(url: str) -> Optional[str]:
    """Extract GitHub username from various GitHub URL formats."""
    if not isinstance(url, str):
        return None
    
    # Check if it's a GitHub URL at all
    if "github.com" not in url.lower():
        return None
    
    # Remove protocol
    url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    
    # Common patterns: github.com/username or www.github.com/username
    match = re.match(r"(?:www\.)?github\.com/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    
    return None

def _get_auth_header() -> Dict[str, str]:
    """Return authorization header with bearer token."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers

async def _fetch_github_api(
    session: aiohttp.ClientSession,
    endpoint: str
) -> Dict[str, Any]:
    """Fetch a single GitHub API endpoint."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = _get_auth_header()
    
    async with session.get(url, headers=headers) as response:
        if response.status == 404:
            raise ValueError("GitHub profile not found (404)")
        elif response.status == 403:
            raise ValueError("Rate limit exceeded (403)")
        elif response.status == 429:
            raise ValueError("Rate limit exceeded (429)")
        elif response.status >= 400:
            raise ValueError(f"GitHub API error: {response.status}")
        
        return await response.json()

async def fetch_github_profile(github_url: str) -> Dict[str, Any]:
    """
    Fetch GitHub profile data from a GitHub URL.
    
    Raises:
        ValueError: If URL is not a GitHub URL, profile not found, or rate limited
    
    Returns:
        Dict with username, name, bio, location, email, company, blog, avatar_url,
        followers, following, public_repos, account_created, last_active,
        top_languages, repos array, and recent_activity
    """
    username = extract_github_username(github_url)
    if not username:
        raise ValueError(f"Invalid GitHub URL: {github_url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch all 3 endpoints in parallel
            user_data, repos_data, events_data = await asyncio.gather(
                _fetch_github_api(session, f"/users/{username}"),
                _fetch_github_api(session, f"/users/{username}/repos?sort=pushed&per_page=20"),
                _fetch_github_api(session, f"/users/{username}/events?per_page=50"),
                return_exceptions=False
            )
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Failed to fetch GitHub profile: {str(e)}")
    
    # Extract top languages from repos
    language_count: Dict[str, int] = {}
    for repo in repos_data:
        lang = repo.get("language")
        if lang:  # Exclude nulls
            language_count[lang] = language_count.get(lang, 0) + 1
    
    top_languages = [
        lang for lang, _ in sorted(
            language_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
    ]
    
    # Get account creation date
    account_created = user_data.get("created_at")
    
    # Find last active date from events
    last_active = None
    if events_data:
        last_active = events_data[0].get("created_at")
    
    # Calculate recent activity (last 30 days)
    commit_count_last_30_days = 0
    active_days_set = set()
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    for event in events_data:
        if event.get("type") == "PushEvent":
            event_date_str = event.get("created_at", "")
            try:
                # Parse ISO 8601 datetime string
                event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                # Make it comparable with utcnow (naive datetime)
                event_date = event_date.replace(tzinfo=None)
                if event_date >= thirty_days_ago:
                    commit_count_last_30_days += event.get("payload", {}).get("size", 0)
                    active_days_set.add(event_date.date())
            except (ValueError, AttributeError):
                pass
    
    active_days = len(active_days_set)
    
    # Build repos array
    repos_array = []
    for repo in repos_data:
        repos_array.append({
            "name": repo.get("name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "url": repo.get("html_url"),
            "last_updated": repo.get("pushed_at")
        })
    
    return {
        "username": username,
        "name": user_data.get("name"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "email": user_data.get("email"),
        "company": user_data.get("company"),
        "blog": user_data.get("blog"),
        "avatar_url": user_data.get("avatar_url"),
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "public_repos": user_data.get("public_repos", 0),
        "account_created": account_created,
        "last_active": last_active,
        "top_languages": top_languages,
        "repos": repos_array,
        "recent_activity": {
            "commit_count_last_30_days": commit_count_last_30_days,
            "active_days": active_days
        }
    }

async def find_and_fetch_github_profile(profiles: List[str]) -> Optional[Dict[str, Any]]:
    """
    Find the first GitHub URL in profiles list and fetch its data.
    Return None if no GitHub URL found or fetch fails.
    """
    for profile_url in profiles:
        if "github.com" in profile_url.lower():
            try:
                return await fetch_github_profile(profile_url)
            except ValueError as e:
                # Log error or return error info - for now skip to next profile
                return {
                    "error": str(e),
                    "original_url": profile_url
                }
    
    return None
