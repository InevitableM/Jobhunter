from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run_pipeline

scheduler = BlockingScheduler()
scheduler.add_job(run_pipeline, "interval", hours=12, id="job_scraper")

print("Scheduler started. Pipeline will run every 12 hours.")
print("Press Ctrl+C to stop.\n")

run_pipeline()  # run immediately on start
scheduler.start()
