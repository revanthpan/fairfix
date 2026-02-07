"""
Parts Pricing Ingestion

Sources:
- RockAuto
- AutoZone
- O'Reilly
- Napa
- Amazon Automotive
- OEM parts catalogs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import PartsPrice
from config.settings import load_sources_config


class PartsPricingIngester:
    """Ingest parts pricing from retailer websites."""

    def __init__(self):
        self.config = load_sources_config()["parts_pricing"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
        })
        self.results: list[PartsPrice] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_url(self, url: str) -> str:
        """Fetch URL with retries."""
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_price_element(self, text: str) -> float | None:
        """Extract price from text like $12.99 or 12.99."""
        import re
        m = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
        return float(m.group(1)) if m else None

    def _scrape_parts_page(self, url: str, retailer: str) -> list[PartsPrice]:
        """Generic scrape for parts listing pages."""
        items = []
        try:
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, "lxml")

            # Common patterns: product cards, tables, list items
            for elem in soup.find_all(["div", "li", "tr"], class_=lambda c: c and "product" in str(c).lower() if c else False):
                price_elem = elem.find(string=lambda t: t and "$" in str(t))
                if not price_elem:
                    price_elem = elem.find(class_=lambda c: c and "price" in str(c).lower() if c else False)
                price = self._parse_price_element(price_elem.get_text() if price_elem else "") if price_elem else None

                name_elem = elem.find(["h2", "h3", "a", "span"], class_=lambda c: c and ("name" in str(c).lower() or "title" in str(c).lower()) if c else False)
                name = name_elem.get_text(strip=True)[:200] if name_elem else elem.get_text(strip=True)[:200]

                if price and name and len(name) > 2:
                    items.append(PartsPrice(
                        part_name=name,
                        price=price,
                        retailer=retailer,
                        source_url=url,
                    ))

            # Fallback: look for any price + text combos
            if not items:
                for link in soup.find_all("a", href=True):
                    if "/product" in link.get("href", "") or "/part" in link.get("href", ""):
                        parent = link.parent
                        if parent:
                            text = parent.get_text(strip=True)
                            price = self._parse_price_element(text)
                            name = link.get_text(strip=True)
                            if price and name:
                                items.append(PartsPrice(
                                    part_name=name[:200],
                                    price=price,
                                    retailer=retailer,
                                    source_url=url,
                                ))

            logger.info(f"Extracted {len(items)} parts from {retailer} @ {url}")
        except Exception as e:
            logger.warning(f"Failed to scrape {retailer} {url}: {e}")

        return items

    def run(self, search_queries: list[str] | None = None) -> list[PartsPrice]:
        """
        Run parts pricing ingestion.
        search_queries: optional list of part names to search (drives URLs).
        """
        logger.info("Starting parts pricing ingestion")

        queries = search_queries or ["oil+filter", "brake+pads", "spark+plugs"]
        retailer_urls = {
            "RockAuto": "https://www.rockauto.com/en/catalog/",
            "AutoZone": "https://www.autozone.com/searchresult?searchText=",
            "O'Reilly": "https://www.oreillyauto.com/shop/b/",
            "Napa": "https://www.napaonline.com/en/search?text=",
            "Amazon": "https://www.amazon.com/s?k=",
        }

        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue
            retailer = source.get("name", "").replace("_", " ").title()
            base = source.get("base_url", "")
            if not base:
                continue
            for q in queries[:2]:  # Limit per retailer to avoid hammering
                url = f"{base}{q}" if "=" in base or base.endswith("/") else f"{base}?q={q}"
                self.results.extend(self._scrape_parts_page(url, retailer))

        logger.info(f"Parts pricing: ingested {len(self.results)} items")
        return self.results
