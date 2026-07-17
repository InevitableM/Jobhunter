import os
import yaml
from adapters import ADAPTERS
from matcher import content_filter, experience_filter, recency_filter, location_filter, keyword_match, llm_match
from collections import defaultdict
from storage import init_db, init_csv, is_new, save_match, append_link, init_links_by_platform, write_platform_section

KEYWORD_THRESHOLD = 0.15   # minimum keyword hit-rate to proceed to LLM
LLM_THRESHOLD = 0.65      # minimum LLM score to save as a match


def run_pipeline():
    print("\n=== Job Scraper Pipeline Starting ===\n")

    config = yaml.safe_load(open("urls.yaml"))
    con = init_db()
    init_csv()
    init_links_by_platform()

    total_scraped = 0
    total_matched = 0
    jobs_by_platform = defaultdict(list)

    for source in config["profiles"]:
        adapter_type = source.get("type", "generic")
        adapter = ADAPTERS.get(adapter_type)

        if not adapter:
            print(f"[Pipeline] Unknown adapter type: {adapter_type}")
            continue

        print(f"-> Scraping: {source['name']} ({adapter_type})")
        jobs = adapter.fetch(source)
        total_scraped += len(jobs)

        for job in jobs:
            if not job.url or not job.title:
                continue

            # Skip if already seen
            if not is_new(con, job.url):
                continue

            jobs_by_platform[adapter_type].append(job)

            # Stage 0 - full scraped job post must contain SDE/intern/AI engineer keywords
            if not content_filter(job):
                continue

            # Stage 0b - required experience (if stated) must be <= max_experience_years
            if not experience_filter(job):
                continue

            # Stage 0c - posted within the last N hours (if a post date is known)
            if not recency_filter(job):
                continue

            # Stage 0d - location must be India or Remote (if location is known)
            if not location_filter(job):
                continue

            append_link(job)

            # Stage 1 - fast keyword filter
            kw_score = keyword_match(job)
            if kw_score < KEYWORD_THRESHOLD:
                continue

            # Stage 2 - LLM scoring
            score, reason = llm_match(job)
            if score >= LLM_THRESHOLD:
                save_match(job, score, reason)
                total_matched += 1
                print(f"  MATCH {score:.0%} - {job.title} @ {job.company}")
            else:
                print(f"  skip  {score:.0%} - {job.title} @ {job.company}")

    for platform, jobs in jobs_by_platform.items():
        write_platform_section(platform, jobs)

    print(f"\n=== Done: {total_scraped} scraped, {total_matched} matched ===")
    print(f"    All links saved to all_job_links.txt")
    print(f"    Links by platform saved to job_links_by_platform.txt")
    print(f"    Matches saved to matched_jobs.csv\n")


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not set. LLM matching will fail.")
        print("Set it with: export GEMINI_API_KEY=your_key_here\n")

    run_pipeline()
