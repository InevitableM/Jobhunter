import csv
import hashlib
import os
import sqlite3
from adapters.base import JobPosting

DB_PATH = "jobs.db"
CSV_PATH = "matched_jobs.csv"
LINKS_PATH = "all_job_links.txt"
LINKS_BY_PLATFORM_PATH = "job_links_by_platform.txt"


def init_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            url_hash   TEXT PRIMARY KEY,
            url        TEXT,
            first_seen TEXT DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    return con


def is_new(con: sqlite3.Connection, url: str) -> bool:
    """Returns True if URL is unseen, and marks it as seen."""
    h = hashlib.md5(url.encode()).hexdigest()
    if con.execute("SELECT 1 FROM seen_jobs WHERE url_hash=?", (h,)).fetchone():
        return False
    con.execute("INSERT INTO seen_jobs VALUES (?, ?, datetime('now'))", (h, url))
    con.commit()
    return True


def init_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["url", "title", "company", "location", "score", "reason", "source"])


def save_match(job: JobPosting, score: float, reason: str):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            job.url, job.title, job.company,
            job.location, f"{score:.2f}", reason, job.source
        ])


def append_link(job: JobPosting):
    with open(LINKS_PATH, "a", encoding="utf-8") as f:
        f.write(job.url + "\n")


def init_links_by_platform():
    with open(LINKS_BY_PLATFORM_PATH, "w", encoding="utf-8"):
        pass


def write_platform_section(platform: str, jobs: list[JobPosting]):
    with open(LINKS_BY_PLATFORM_PATH, "a", encoding="utf-8") as f:
        f.write(f"=== {platform} ===\n")
        for job in jobs:
            f.write(job.url + "\n")
        f.write("\n")
