from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class JobPosting:
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    date_posted: Optional[datetime] = None
    source: str = ""


class BaseAdapter:
    def fetch(self, config: dict) -> list[JobPosting]:
        raise NotImplementedError
