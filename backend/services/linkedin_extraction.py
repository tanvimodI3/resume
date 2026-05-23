import requests
import os

RAPIDAPI_HOST = "linkedin-data-api.p.rapidapi.com"

def _get_headers():
    return {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": RAPIDAPI_HOST
    }

def _get(url, params):
    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.status_code != 200:
            return {"error": f"API returned {response.status_code}"}
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_profile_detail(linkedin_url: str):
    return _get(
        "https://linkedin-data-api.p.rapidapi.com/get-profile-data-by-url",
        {"url": linkedin_url}
    )

def get_experiences(linkedin_url: str):
    return _get(
        "https://linkedin-data-api.p.rapidapi.com/get-profile-positions",
        {"url": linkedin_url}
    )

def get_educations(linkedin_url: str):
    return _get(
        "https://linkedin-data-api.p.rapidapi.com/get-profile-education-experiences",
        {"url": linkedin_url}
    )

def get_skills(linkedin_url: str):
    return _get(
        "https://linkedin-data-api.p.rapidapi.com/get-profile-skills",
        {"url": linkedin_url}
    )

def get_full_candidate_profile(linkedin_url: str):
    return {
        "profile_detail": get_profile_detail(linkedin_url),
        "experiences":    get_experiences(linkedin_url),
        "educations":     get_educations(linkedin_url),
        "skills":         get_skills(linkedin_url),
    }