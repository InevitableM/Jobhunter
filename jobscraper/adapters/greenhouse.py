import re
from datetime import datetime
import requests
from .base import BaseAdapter, JobPosting


class GreenhouseAdapter(BaseAdapter):
    def fetch(self, config: dict) -> list[JobPosting]:
        url = config["url"]
        match = re.search(r"greenhouse\.io/(.+?)(?:\?|$)", url)
        if not match:
            print(f"[Greenhouse] Could not parse board token from {url}")
            return []

        token = match.group(1).strip("/")
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Greenhouse] Failed to fetch {api_url}: {e}")
            return []

        jobs = []
        for j in data.get("jobs", []):
            date_posted = None
            first_published = j.get("first_published")
            if first_published:
                try:
                    date_posted = datetime.fromisoformat(first_published)
                except ValueError:
                    date_posted = None

            jobs.append(JobPosting(
                title=j.get("title", ""),
                company=config.get("name", token),
                url=j.get("absolute_url", ""),
                location=j.get("location", {}).get("name", ""),
                description=j.get("content", ""),
                date_posted=date_posted,
                source="greenhouse",
            ))
        print(f"[Greenhouse] {len(jobs)} jobs from {token}")
        return jobs
