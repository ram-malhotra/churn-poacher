"""
Signal Ingestion Source Adapters.
"""

from app.services.sources.datadog_status import DatadogStatusAdapter
from app.services.sources.hackernews import HackerNewsAdapter
from app.services.sources.reddit import RedditAdapter
from app.services.sources.g2_reviews import G2ReviewsAdapter
from app.services.sources.synthetic_generator import SyntheticSignalGenerator

__all__ = [
    "DatadogStatusAdapter",
    "HackerNewsAdapter",
    "RedditAdapter",
    "G2ReviewsAdapter",
    "SyntheticSignalGenerator",
]
