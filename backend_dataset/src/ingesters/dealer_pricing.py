"""
Dealer Repair Pricing Ingestion

Sources:
- Dealer service pages
- Public service menus
- Dealer APIs
- Public booking platforms (Openbay, RepairPal, etc.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import DealerPrice
from config.settings import load_sources_config


class DealerPricingIngester:
    """Ingest dealer repair pricing from configured sources."""

    def __init__(self, dealer_urls: list[str] | None = None):
        self.config = load_sources_config()["dealer_repair_pricing"]
        self.dealer_urls = dealer_urls or []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; MaintenancePipeline/1.0; +research)"
        })
        self.results: list[DealerPrice] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_url(self, url: str) -> str:
        """Fetch URL with retries."""
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_dealer_page(self, url: str, dealer_name: str) -> list[DealerPrice]:
        """Parse dealer service/price page."""
        items = []
        try:
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, "lxml")

            # Common patterns: service menus, price lists, tables
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        service = cells[0].get_text(strip=True)
                        price_str = cells[1].get_text(strip=True) if len(cells) > 1 else "0"
                        price = self._parse_price(price_str)
                        if price and service:
                            items.append(DealerPrice(
                                dealer_name=dealer_name,
                                service_name=service,
                                labor_cost=price,
                                total_cost=price,
                                source="dealer_service_page",
                                source_url=url,
                            ))

            # Also check lists/divs with common price patterns
            for elem in soup.find_all(["li", "div"], class_=lambda c: c and ("price" in str(c).lower() or "service" in str(c).lower())):
                text = elem.get_text(strip=True)
                price = self._parse_price(text)
                if price:
                    service = text.replace(f"${price}", "").strip()
                    if len(service) > 3:
                        items.append(DealerPrice(
                            dealer_name=dealer_name,
                            service_name=service[:200],
                            labor_cost=price,
                            total_cost=price,
                            source="dealer_service_page",
                            source_url=url,
                        ))

            logger.info(f"Extracted {len(items)} dealer prices from {url}")
        except Exception as e:
            logger.warning(f"Failed to parse dealer page {url}: {e}")

        return items

    def _parse_price(self, s: str) -> float | None:
        """Extract dollar amount from string."""
        import re
        m = re.search(r"\$?([\d,]+\.?\d*)", s.replace(",", ""))
        return float(m.group(1)) if m else None

    def run(self, dealer_urls: list[tuple[str, str]] | None = None) -> list[DealerPrice]:
        """
        Run dealer pricing ingestion.
        dealer_urls: list of (url, dealer_name) tuples.
        """
        logger.info("Starting dealer pricing ingestion")

        urls = dealer_urls or [(u, "Dealer") for u in self.dealer_urls]

        for url, dealer_name in urls:
            self.results.extend(self._parse_dealer_page(url, dealer_name))

        logger.info(f"Dealer pricing: ingested {len(self.results)} items")
        return self.results
