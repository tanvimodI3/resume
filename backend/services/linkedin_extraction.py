import requests
import os

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "z-real-time-linkedin-scraper-api1.p.rapidapi.com"

headers = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

def _get(url, linkedin_url):
    response = requests.get(
        url,
        headers=headers,
        params={"url": linkedin_url}
    )
    return response.json()


#profile details
def get_profile_detail(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile"
    return _get(url, linkedin_url)

def get_contact_info(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/contact"
    return _get(url, linkedin_url)

#main details needed for matching
def get_educations(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/educations"
    return _get(url, linkedin_url)

def get_experiences(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/experiences"
    return _get(url, linkedin_url)

def get_skills(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/skills"
    return _get(url, linkedin_url)

def get_certifications(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/licenses"

    return _get(url, linkedin_url)

def get_projects(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/profile/projects"
    return _get(url, linkedin_url)


#job details
def get_job_detail(linkedin_url: str):
    url = "https://z-real-time-linkedin-scraper-api1.p.rapidapi.com/api/job/detail"
    return _get(url, linkedin_url)


#all fetch
def get_full_candidate_profile(linkedin_url: str):
    return {
        "profile_detail": get_profile_detail(linkedin_url),
        "contact_info": get_contact_info(linkedin_url),
        "educations": get_educations(linkedin_url),
        "experiences": get_experiences(linkedin_url),
        "skills": get_skills(linkedin_url),
        "certifications": get_certifications(linkedin_url),
        "projects": get_projects(linkedin_url),
        "job_detail": get_job_detail(linkedin_url),
    }