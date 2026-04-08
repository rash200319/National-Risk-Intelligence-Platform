"""
Multi-source fallback strategy for resilient data collection.
Attempts to fetch news from multiple sources with automatic fallback logic.
"""
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from urllib.parse import urlparse

from utils.resilience import fetch_url

logger = logging.getLogger(__name__)


class MultiSourceCollector:
    """
    Manages multiple news sources with priority-based fallback strategy.
    Tries primary sources first, then falls back to alternatives if needed.
    """
    
    def __init__(self):
        self.newsapi_queries = [
            'Sri Lanka',
            'Colombo',
            'Sri Lanka economy',
            'Sri Lanka protest',
        ]
        self.gdelt_queries = [
            '"Sri Lanka"',
            'Colombo OR Sri Lankan OR Sri Lanka economy',
        ]
        self.world_bank_country = os.getenv('WORLD_BANK_COUNTRY', 'LKA')
        self.world_bank_indicators = [
            item.strip() for item in os.getenv(
                'WORLD_BANK_INDICATORS',
                'FP.CPI.TOTL.ZG,NY.GDP.MKTP.KD.ZG,SL.UEM.TOTL.ZS'
            ).split(',') if item.strip()
        ]
        self.historical_lookback_days = int(os.getenv('HISTORICAL_LOOKBACK_DAYS', '30'))
        self.gdelt_request_delay_seconds = float(os.getenv('GDELT_REQUEST_DELAY_SECONDS', '2'))
        self.sources = {
            'rss': {
                'priority': 1,
                'name': 'RSS Feeds (Primary)',
                'handler': None  # Will be set by collector
            },
            'newsapi': {
                'priority': 2,
                'name': 'NewsAPI (API-Based)',
                'enabled': bool(os.getenv('NEWS_API_KEY')),
                'api_key': os.getenv('NEWS_API_KEY'),
                'handler': None
            },
            'gdelt': {
                'priority': 3,
                'name': 'GDELT (Global Events)',
                'enabled': True,  # Always available
                'handler': None
            },
            'worldbank': {
                'priority': 4,
                'name': 'World Bank Indicators',
                'enabled': True,
                'handler': None
            }
        }
        self.last_results = {}
        self.fallback_triggered = {}

    def _dedupe_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates using normalized URL first, then title/date fallback."""
        seen = set()
        deduped = []

        for item in items:
            url = (item.get('url') or '').strip().lower()
            title = (item.get('title') or '').strip().lower()
            published = (item.get('published') or '').strip()[:10]

            if url:
                parsed = urlparse(url)
                key = f"url:{parsed.netloc}{parsed.path}" if parsed.netloc else f"url:{url}"
            else:
                key = f"title:{title}|date:{published}"

            if key in seen:
                continue

            seen.add(key)
            deduped.append(item)

        return deduped
    
    def collect_news_with_fallback(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Collect news from configured sources with automatic fallback.
        
        Strategy:
        1. Try NewsAPI first when configured
        2. Fallback to RSS feeds
        3. Fallback to GDELT with throttling
        4. Enrich with World Bank macro indicators
        5. Return aggregated results
        """
        all_news = []

        # Try NewsAPI first when available (Priority 1)
        try:
            if self.sources['newsapi']['enabled']:
                logger.info("🔄 Attempting NewsAPI collection (Primary source)...")
                newsapi_news = self._fetch_from_newsapi(limit)
                all_news.extend(newsapi_news)
                logger.info(f"✓ NewsAPI Success: {len(newsapi_news)} items")
                self.last_results['newsapi'] = {
                    'count': len(newsapi_news),
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"⚠️ NewsAPI collection failed: {e}")
            self.fallback_triggered['newsapi'] = True

        # Fallback to RSS feeds (Priority 2)
        try:
            logger.info("📰 Attempting RSS feed collection (Fallback source)...")
            rss_news = self._fetch_from_rss(limit)
            all_news.extend(rss_news)
            
            success_rate = len(rss_news) / limit if limit > 0 else 0
            logger.info(f"✓ RSS Success: {len(rss_news)} items ({success_rate*100:.0f}%)")
            self.last_results['rss'] = {
                'count': len(rss_news),
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"⚠️ RSS collection failed: {e}")
            self.fallback_triggered['rss'] = True

        # Fallback to GDELT (Priority 3)
        try:
            logger.info("🔄 Final Fallback: Attempting GDELT collection...")
            gdelt_news = self._fetch_from_gdelt(limit - len(all_news))
            all_news.extend(gdelt_news)
            
            logger.info(f"✓ GDELT Success: {len(gdelt_news)} items")
            
            self.last_results['gdelt'] = {
                'count': len(gdelt_news),
                'status': 'final_fallback',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"⚠️ GDELT fallback also failed: {e}")
            self.fallback_triggered['gdelt'] = True

        # Historical enrichment: pull up to 30 days of additional context.
        try:
            logger.info("🕒 Enrichment: Fetching historical 30-day coverage...")
            historical_news = self._fetch_historical_news(self.historical_lookback_days, limit)
            all_news.extend(historical_news)
            if historical_news:
                self.last_results['historical'] = {
                    'count': len(historical_news),
                    'status': 'enrichment',
                    'timestamp': datetime.now().isoformat(),
                    'lookback_days': self.historical_lookback_days,
                }
                logger.info(f"✓ Historical coverage added: {len(historical_news)} items")
        except Exception as e:
            logger.warning(f"⚠️ Historical enrichment failed: {e}")
            self.fallback_triggered['historical'] = True

        # Add macro-economic context from World Bank API (Priority 4)
        try:
            logger.info("🌍 Enrichment: Fetching World Bank indicators...")
            wb_items = self._fetch_from_world_bank(max(1, min(10, limit - len(all_news))))
            all_news.extend(wb_items)

            self.last_results['worldbank'] = {
                'count': len(wb_items),
                'status': 'enrichment',
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"✓ World Bank Success: {len(wb_items)} indicators")
        except Exception as e:
            logger.warning(f"⚠️ World Bank enrichment failed: {e}")
            self.fallback_triggered['worldbank'] = True
        
        if len(all_news) == 0:
            logger.error("❌ All data sources failed to return any data")

        return self._dedupe_items(all_news)[:limit] if all_news else []
    
    def _fetch_from_rss(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch from RSS feeds (primary source)."""
        from modules.news import fetch_news
        return fetch_news(limit_per_source=limit)
    
    def _fetch_from_newsapi(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch from NewsAPI (fallback source)."""
        try:
            api_key = os.getenv('NEWS_API_KEY')
            if not api_key:
                return []
            
            all_articles = []
            
            page_size = max(1, min(limit // max(len(self.newsapi_queries), 1), 20))
            from_date = (datetime.now(timezone.utc) - timedelta(days=self.historical_lookback_days)).date().isoformat()

            for query in self.newsapi_queries:
                try:
                    url = 'https://newsapi.org/v2/everything'
                    params = {
                        'q': query,
                        'from': from_date,
                        'to': datetime.now(timezone.utc).date().isoformat(),
                        'sortBy': 'publishedAt',
                        'language': 'en',
                        'pageSize': page_size,
                        'apiKey': api_key
                    }
                    
                    response = fetch_url(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get('articles'):
                        for article in data['articles']:
                            all_articles.append({
                                'source': 'NewsAPI',
                                'title': article.get('title', ''),
                                'content': article.get('content', ''),
                                'description': article.get('description', ''),
                                'url': article.get('url', ''),
                                'published': article.get('publishedAt', datetime.now().isoformat()),
                                'author': article.get('author', ''),
                                'raw_data': str(article)
                            })
                except Exception as e:
                    logger.debug(f"NewsAPI query '{query}' failed: {e}")
            
            logger.info(f"NewsAPI: Fetched {len(all_articles)} articles")
            return self._dedupe_items(all_articles)[:limit]
        except Exception as e:
            logger.error(f"NewsAPI fetch failed: {e}")
            return []
    
    def _fetch_from_gdelt(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch from GDELT (Global Event Database - always free)."""
        try:
            # GDELT DOC API is public and does not require an API key.
            url = 'https://api.gdeltproject.org/api/v2/doc/doc'
            articles = []
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=self.historical_lookback_days)
            startdatetime = start_dt.strftime('%Y%m%d%H%M%S')
            enddatetime = end_dt.strftime('%Y%m%d%H%M%S')

            for query in self.gdelt_queries:
                time.sleep(self.gdelt_request_delay_seconds)
                params = {
                    'query': query,
                    'mode': 'ArtList',
                    'format': 'json',
                    'sort': 'datedesc',
                    'startdatetime': startdatetime,
                    'enddatetime': enddatetime,
                    'maxrecords': min(limit, 100)
                }

                response = fetch_url(url, params=params)
                response.raise_for_status()

                data = response.json()
                for article in data.get('articles', [])[:limit]:
                    articles.append({
                        'source': 'GDELT',
                        'title': article.get('title', ''),
                        'content': article.get('snippet', '') or article.get('body', ''),
                        'description': article.get('snippet', '') or article.get('body', '')[:200],
                        'url': article.get('url', ''),
                        'published': article.get('seendate', datetime.now().isoformat()),
                        'author': article.get('sourcecountry', ''),
                        'raw_data': str(article)
                    })
            
            logger.info(f"GDELT: Fetched {len(articles)} articles")
            return self._dedupe_items(articles)
        except Exception as e:
            logger.error(f"GDELT fetch failed: {e}")
            return []

    def _fetch_historical_news(self, lookback_days: int, limit: int) -> List[Dict[str, Any]]:
        """Fetch older news coverage from API sources to fill the last two weeks."""
        items: List[Dict[str, Any]] = []

        # Prefer NewsAPI historical coverage if configured.
        if self.sources['newsapi']['enabled']:
            items.extend(self._fetch_from_newsapi(max(1, limit // 2)))

        # Always supplement with GDELT historical coverage.
        items.extend(self._fetch_from_gdelt(max(1, limit // 2)))

        return self._dedupe_items(items)

    def _fetch_from_world_bank(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch macro indicators from World Bank Open Data API."""
        indicator_labels = {
            'FP.CPI.TOTL.ZG': 'Inflation, consumer prices (annual %)',
            'NY.GDP.MKTP.KD.ZG': 'GDP growth (annual %)',
            'SL.UEM.TOTL.ZS': 'Unemployment, total (% of labor force)',
            'GC.DOD.TOTL.GD.ZS': 'Central government debt (% of GDP)',
            'NE.EXP.GNFS.ZS': 'Exports of goods and services (% of GDP)'
        }

        items: List[Dict[str, Any]] = []
        country = self.world_bank_country

        for indicator in self.world_bank_indicators:
            try:
                url = f'https://api.worldbank.org/v2/country/{country}/indicator/{indicator}'
                params = {
                    'format': 'json',
                    'per_page': 50,
                }

                response = fetch_url(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, list) or len(data) < 2 or not data[1]:
                    continue

                point = next((row for row in data[1] if row.get('value') is not None), None)
                if not point:
                    continue

                label = indicator_labels.get(indicator, indicator)
                value = point.get('value')
                year = point.get('date')
                item_url = point.get('indicator', {}).get('id', indicator)
                
                items.append({
                    'source': 'WorldBank',
                    'title': f'World Bank: {label} in {country} = {value} ({year})',
                    'content': f'World Bank indicator {indicator} latest value for {country} is {value} in {year}.',
                    'description': f'{label}: {value} ({year})',
                    'url': f'https://data.worldbank.org/indicator/{item_url}',
                    'published': datetime.now().isoformat(),
                    'author': 'World Bank Open Data API',
                    'raw_data': str(point),
                })

                if len(items) >= limit:
                    break
            except Exception as exc:
                logger.debug(f'World Bank indicator {indicator} failed: {exc}')

        return items
    
    def get_source_status(self) -> Dict[str, Any]:
        """Returns status of all sources for monitoring."""
        return {
            'timestamp': datetime.now().isoformat(),
            'last_results': self.last_results,
            'fallbacks_triggered': self.fallback_triggered,
            'sources_enabled': {
                name: self.sources[key].get('enabled', True)
                for key, name in [('rss', 'RSS'), ('newsapi', 'NewsAPI'), ('gdelt', 'GDELT'), ('worldbank', 'WorldBank')]
            },
            'newsapi_configured': bool(os.getenv('NEWS_API_KEY')),
            'gdelt_ready': True,
            'worldbank_ready': True,
        }


# Global collector instance
multi_source_collector = MultiSourceCollector()
