import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base import BaseAdapter, JobPosting

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}


class GenericAdapter(BaseAdapter):
    def fetch(self, config: dict) -> list[JobPosting]:
        try:
            resp = requests.get(config["url"], headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Generic] Failed to fetch {config['url']}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        sel = config.get("selectors", {})

        job_list_sel = sel.get("job_list", "li, .job, .position, .opening")
        title_sel = sel.get("title", "h3, h2, h4, a, .title")
        link_sel = sel.get("link", "a")

        jobs = []
        for item in soup.select(job_list_sel)[:50]:
            title_el = item.select_one(title_sel)
            link_el = item.select_one(link_sel)

            title = title_el.get_text(strip=True) if title_el else ""
            href = link_el.get("href", "") if link_el else ""
            if href and not href.startswith("http"):
                href = urljoin(config["url"], href)

            if title and len(title) > 3:
                job_url = href or config["url"]
                jobs.append(
                    JobPosting(
                        title=title,
                        company=config.get("name", ""),
                        url=job_url,
                        description=self._fetch_full_page(job_url),
                        source="generic",
                    )
                )

        print(f"[Generic] {len(jobs)} jobs from {config['name']}")
        return jobs

    def _fetch_full_page(self, url: str) -> str:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return ""
