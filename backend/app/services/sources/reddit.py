"""
Reddit Official API Adapter.
Safely integrates with the Reddit OAuth API if credentials are provided,
or disables itself gracefully when credentials are absent.
"""

from typing import List, Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.agents.listener.schemas import NormalizedSignal
from app.agents.listener.normalizer import SignalNormalizer
from app.agents.listener.classifier import SignalClassifier
from app.agents.listener.config import listener_config


class RedditAdapter:
    NAME = "REDDIT"

    def __init__(
        self,
        client_id: Optional[str] = settings.REDDIT_CLIENT_ID,
        client_secret: Optional[str] = settings.REDDIT_CLIENT_SECRET,
        user_agent: str = settings.REDDIT_USER_AGENT,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._access_token: Optional[str] = None

    def is_configured(self) -> bool:
        """Checks if valid credentials exist for Reddit API."""
        return bool(self.client_id and self.client_secret and self.client_id.strip() and self.client_secret.strip())

    async def is_available(self) -> bool:
        return self.is_configured()

    async def _authenticate(self, client: httpx.AsyncClient) -> bool:
        """Authenticates with Reddit's official OAuth script endpoint."""
        if not self.is_configured():
            return False
            
        try:
            auth_url = "https://www.reddit.com/api/v1/access_token"
            data = {"grant_type": "client_credentials"}
            auth = (self.client_id, self.client_secret)
            headers = {"User-Agent": self.user_agent}

            response = await client.post(auth_url, data=data, auth=auth, headers=headers)
            if response.status_code == 200:
                payload = response.json()
                self._access_token = payload.get("access_token")
                return True
            else:
                logger.warning(f"Reddit OAuth authentication failed with HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error during Reddit authentication: {e}")
            return False

    async def fetch_signals(self, subreddits: Optional[List[str]] = None) -> List[NormalizedSignal]:
        """Fetches recent Datadog-related posts from specified subreddits."""
        meta = await self.fetch_signals_with_meta(subreddits)
        return meta["signals"]

    async def fetch_signals_with_meta(self, subreddits: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetches signals with metadata for telemetry reporting."""
        if not self.is_configured():
            logger.info("Reddit adapter is disabled (no credentials provided in environment).")
            return {
                "signals": [],
                "records_retrieved": 0,
                "errors": ["Reddit API credentials not configured (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET missing)"],
            }

        signals: List[NormalizedSignal] = []
        errors: List[str] = []
        total_records_retrieved = 0
        subreddits = subreddits or listener_config.SUBREDDITS[:2]

        async with httpx.AsyncClient(timeout=listener_config.REQUEST_TIMEOUT_SECONDS) as client:
            if not self._access_token:
                authenticated = await self._authenticate(client)
                if not authenticated:
                    return {
                        "signals": [],
                        "records_retrieved": 0,
                        "errors": ["Failed to authenticate with Reddit OAuth API"],
                    }

            headers = {
                "Authorization": f"bearer {self._access_token}",
                "User-Agent": self.user_agent,
            }

            for sub in subreddits:
                try:
                    search_url = f"https://oauth.reddit.com/r/{sub}/search"
                    params = {
                        "q": "datadog",
                        "sort": "new",
                        "restrict_sr": 1,
                        "limit": 5,
                    }
                    response = await client.get(search_url, params=params, headers=headers)
                    if response.status_code != 200:
                        msg = f"Reddit search on r/{sub} returned HTTP {response.status_code}"
                        logger.warning(msg)
                        errors.append(msg)
                        continue

                    data = response.json()
                    children = data.get("data", {}).get("children", [])
                    total_records_retrieved += len(children)
                    for child in children:
                        post_data = child.get("data", {})
                        normalized = SignalNormalizer.normalize_reddit_post(post_data)
                        classified = SignalClassifier.classify(normalized)
                        signals.append(classified)

                except Exception as e:
                    msg = f"Error querying Reddit r/{sub}: {e}"
                    logger.error(msg)
                    errors.append(msg)
                    continue

        return {
            "signals": signals,
            "records_retrieved": total_records_retrieved,
            "errors": errors,
        }
