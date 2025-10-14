"""Glossary web scraper for petroleum engineering terms.

Scrapes definitions from authoritative sources:
- SLB Oilfield Glossary (https://glossary.slb.com)
- SPE PetroWiki (https://petrowiki.spe.org)
- AAPG Wiki (https://wiki.aapg.org)

Features:
- Rate limiting (1 req/s default)
- Exponential backoff retry logic
- Robots.txt compliance
- HTML parsing with BeautifulSoup4
"""

import time
import logging
from typing import Optional, List
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from robotexclusionrulesparser import RobotFileParser
    ROBOTS_PARSER_AVAILABLE = True
except ImportError:
    ROBOTS_PARSER_AVAILABLE = False
    RobotFileParser = None  # type: ignore

from schemas.glossary import Definition, ScraperConfig

logger = logging.getLogger(__name__)


class GlossaryScraper:
    """Web scraper for petroleum engineering glossary terms.

    Attributes:
        config: Scraper configuration (timeout, retries, rate limit, etc.)
        session: Requests session with retry logic
        last_request_time: Timestamp of last request (for rate limiting)
        robots_cache: Cache of robots.txt parsers by domain
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize scraper with configuration.

        Args:
            config: Scraper configuration (defaults if None)
        """
        self.config = config or ScraperConfig()
        self.session = self._create_session()
        self.last_request_time: dict[str, float] = {}  # domain → timestamp
        self.robots_cache: dict[str, Optional[RobotFileParser]] = {}

    def scrape_term(self, term: str, sources: List[str]) -> Optional[Definition]:
        """Scrape definition for a term from specified sources.

        Args:
            term: Technical term to scrape
            sources: List of source identifiers to try in order (e.g., ["slb", "spe", "aapg"])

        Returns:
            Definition if found, None if all sources fail

        Raises:
            ValueError: If term is empty or exceeds 100 characters
        """
        # Validate input
        normalized_term = self._normalize_term(term)
        if not normalized_term:
            raise ValueError("term cannot be empty")
        if len(normalized_term) > 100:
            raise ValueError(f"term too long: {len(normalized_term)} > 100 chars")

        # Try each source in order
        for source in sources:
            try:
                if source == "slb":
                    result = self._scrape_slb(normalized_term)
                elif source == "spe":
                    result = self._scrape_spe(normalized_term)
                elif source == "aapg":
                    result = self._scrape_aapg(normalized_term)
                else:
                    logger.warning(f"Unknown source: {source}")
                    continue

                if result:
                    logger.info(f"Successfully scraped '{term}' from {source}")
                    return result
            except Exception as e:
                logger.warning(f"Failed to scrape '{term}' from {source}: {e}")
                continue

        logger.error(f"All sources failed for term: {term}")
        return None

    def _scrape_slb(self, term: str) -> Optional[Definition]:
        """Scrape SLB Oilfield Glossary.

        Args:
            term: Normalized term

        Returns:
            Definition if successful, None otherwise
        """
        url = f"https://glossary.slb.com/en/terms/{term[0]}/{term}"
        domain = "glossary.slb.com"

        # Check robots.txt
        if self.config.respect_robots_txt and not self._check_robots_allowed(url):
            logger.warning(f"Disallowed by robots.txt: {url}")
            return None

        # Rate limiting
        self._enforce_rate_limit(domain)

        # Make request
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"SLB request failed for '{term}': {e}")
            return None

        # Parse HTML
        soup = BeautifulSoup(response.text, "lxml")
        definition_elem = soup.select_one(".definition") or soup.select_one('[itemprop="description"]')

        if definition_elem:
            definition_text = definition_elem.get_text(strip=True)
            if len(definition_text) >= 10:
                return Definition(
                    term=term,
                    definition=definition_text[:2000],  # Truncate to max length
                    source="slb",
                    source_url=url,
                    timestamp=datetime.utcnow(),
                    cached=False
                )

        logger.debug(f"No definition found for '{term}' on SLB")
        return None

    def _scrape_spe(self, term: str) -> Optional[Definition]:
        """Scrape SPE PetroWiki.

        Args:
            term: Normalized term

        Returns:
            Definition if successful, None otherwise
        """
        # SPE PetroWiki uses title case URLs
        title_case_term = term.replace(" ", "_").title()
        url = f"https://petrowiki.spe.org/{title_case_term}"
        domain = "petrowiki.spe.org"

        if self.config.respect_robots_txt and not self._check_robots_allowed(url):
            logger.warning(f"Disallowed by robots.txt: {url}")
            return None

        self._enforce_rate_limit(domain)

        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"SPE request failed for '{term}': {e}")
            return None

        soup = BeautifulSoup(response.text, "lxml")
        # SPE uses MediaWiki format
        content_elem = soup.select_one(".mw-parser-output") or soup.select_one("#mw-content-text")

        if content_elem:
            # Extract first paragraph
            first_para = content_elem.find("p")
            if first_para:
                definition_text = first_para.get_text(strip=True)
                if len(definition_text) >= 10:
                    return Definition(
                        term=term,
                        definition=definition_text[:2000],
                        source="spe",
                        source_url=url,
                        timestamp=datetime.utcnow(),
                        cached=False
                    )

        logger.debug(f"No definition found for '{term}' on SPE")
        return None

    def _scrape_aapg(self, term: str) -> Optional[Definition]:
        """Scrape AAPG Wiki.

        Args:
            term: Normalized term

        Returns:
            Definition if successful, None otherwise
        """
        title_case_term = term.replace(" ", "_").title()
        url = f"https://wiki.aapg.org/{title_case_term}"
        domain = "wiki.aapg.org"

        if self.config.respect_robots_txt and not self._check_robots_allowed(url):
            logger.warning(f"Disallowed by robots.txt: {url}")
            return None

        self._enforce_rate_limit(domain)

        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"AAPG request failed for '{term}': {e}")
            return None

        soup = BeautifulSoup(response.text, "lxml")
        content_elem = soup.select_one("#mw-content-text") or soup.select_one(".mw-parser-output")

        if content_elem:
            first_para = content_elem.find("p")
            if first_para:
                definition_text = first_para.get_text(strip=True)
                if len(definition_text) >= 10:
                    return Definition(
                        term=term,
                        definition=definition_text[:2000],
                        source="aapg",
                        source_url=url,
                        timestamp=datetime.utcnow(),
                        cached=False
                    )

        logger.debug(f"No definition found for '{term}' on AAPG")
        return None

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy (exponential backoff)
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,  # 1s, 2s, 4s, ...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set User-Agent
        session.headers.update({"User-Agent": self.config.user_agent})

        return session

    def _enforce_rate_limit(self, domain: str) -> None:
        """Enforce rate limit for a domain.

        Args:
            domain: Domain name (e.g., "glossary.slb.com")
        """
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            min_interval = 1.0 / self.config.rate_limit
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        self.last_request_time[domain] = time.time()

    def _check_robots_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed (or if check disabled/fails), False if disallowed
        """
        if not self.config.respect_robots_txt or not ROBOTS_PARSER_AVAILABLE:
            return True

        parsed = urlparse(url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        # Check cache
        if domain not in self.robots_cache:
            try:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[domain] = rp
                logger.debug(f"Loaded robots.txt for {domain}")
            except Exception as e:
                logger.warning(f"Failed to load robots.txt for {domain}: {e}")
                self.robots_cache[domain] = None
                return True  # Allow on failure

        rp = self.robots_cache[domain]
        if rp:
            return rp.can_fetch(self.config.user_agent, url)

        return True

    def _normalize_term(self, term: str) -> str:
        """Normalize term to lowercase and strip whitespace.

        Args:
            term: Raw term

        Returns:
            Normalized term
        """
        return term.strip().lower()
