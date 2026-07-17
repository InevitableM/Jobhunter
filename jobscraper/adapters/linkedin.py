import time
import random
from datetime import datetime
from .base import BaseAdapter, JobPosting


class LinkedInAdapter(BaseAdapter):
    def fetch(self, config: dict) -> list[JobPosting]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print(
                "[LinkedIn] playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            return []

        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                page.goto(config["url"], wait_until="domcontentloaded", timeout=30000)
                time.sleep(random.uniform(2, 4))

                # Try to find job cards
                page.wait_for_selector(
                    ".job-card-container, .jobs-search__results-list li", timeout=10000
                )
                cards = page.query_selector_all(
                    ".job-card-container, .jobs-search__results-list li"
                )

                for card in cards[:25]:  # cap at 25 per run
                    try:
                        title_el = card.query_selector(".job-card-list__title, h3, h2")
                        link_el = card.query_selector("a[href*='/jobs/']")
                        company_el = card.query_selector(
                            ".job-card-container__company-name, .artdeco-entity-lockup__subtitle"
                        )
                        location_el = card.query_selector(
                            ".job-search-card__location, .job-card-container__metadata-item"
                        )
                        date_el = card.query_selector(
                            ".job-search-card__listdate, time"
                        )

                        title = title_el.inner_text().strip() if title_el else ""
                        company = (
                            company_el.inner_text().strip() if company_el else "Unknown"
                        )
                        location = (
                            location_el.inner_text().strip() if location_el else ""
                        )
                        href = link_el.get_attribute("href") if link_el else ""
                        if href and not href.startswith("http"):
                            href = "https://www.linkedin.com" + href
                        href = (
                            href.split("?")[0] if href else ""
                        )  # strip tracking params

                        date_posted = None
                        date_str = (
                            date_el.get_attribute("datetime") if date_el else None
                        )
                        if date_str:
                            try:
                                date_posted = datetime.fromisoformat(date_str)
                            except ValueError:
                                date_posted = None

                        if title and href:
                            jobs.append(
                                JobPosting(
                                    title=title,
                                    company=company,
                                    url=href,
                                    location=location,
                                    description=self._fetch_full_page(context, href),
                                    date_posted=date_posted,
                                    source="linkedin",
                                )
                            )
                    except Exception:
                        continue

            except Exception as e:
                print(f"[LinkedIn] Scrape failed: {e}")
            finally:
                browser.close()

        print(f"[LinkedIn] {len(jobs)} jobs found")
        return jobs

    def _fetch_full_page(self, context, url: str) -> str:
        try:
            job_page = context.new_page()
            try:
                job_page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(random.uniform(1, 2))
                return job_page.content()
            finally:
                job_page.close()
        except Exception:
            return ""
