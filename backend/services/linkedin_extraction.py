import requests
import os

RAPIDAPI_HOST = "z-real-time-linkedin-scraper-api1.p.rapidapi.com"

def _get_headers():                              
    return {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": RAPIDAPI_HOST
    }

def _get(url, linkedin_url):
    response = requests.get(
        url,
        headers=_get_headers(),                 
        params={"url": linkedin_url},
        timeout=10
    )
    if response.status_code != 200:
        return {"error": f"API returned {response.status_code}"}
    return response.json()

def get_profile_detail(linkedin_url: str):
    return _get("https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile", linkedin_url)

def get_educations(linkedin_url: str):
    return _get("https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/educations", linkedin_url)

def get_experiences(linkedin_url: str):
    return _get("https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/experiences", linkedin_url)

def get_skills(linkedin_url: str):
    return _get("https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/skills", linkedin_url)

def get_full_candidate_profile(linkedin_url: str):
    return {
        "profile_detail": get_profile_detail(linkedin_url),
        "educations":     get_educations(linkedin_url),
        "experiences":    get_experiences(linkedin_url),
        "skills":         get_skills(linkedin_url),
    }