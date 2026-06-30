import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus


def search_re_news(topic: str = "real estate market trends") -> dict:
    """Fetch RE news via Google News RSS (free, no API key) or NewsAPI if key present."""

    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        return _newsapi(topic, news_api_key)

    return _google_rss(topic)


def _google_rss(topic: str) -> dict:
    query = quote_plus(f"real estate {topic}")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:5]
            articles = []
            for item in items:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub = item.findtext("pubDate", "")
                source_el = item.find("{https://news.google.com/rss}source")
                source = source_el.text if source_el is not None else ""
                articles.append({
                    "title": title,
                    "description": desc[:300] if desc else "",
                    "url": link,
                    "published": pub,
                    "source": source,
                })
            if articles:
                return {"articles": articles}
    except Exception:
        pass

    return _stub()


def _newsapi(topic: str, api_key: str) -> dict:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": f"real estate {topic}",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": api_key,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            return {
                "articles": [
                    {
                        "title": a["title"],
                        "description": a.get("description", ""),
                        "url": a["url"],
                        "published": a.get("publishedAt", ""),
                        "source": a.get("source", {}).get("name", ""),
                    }
                    for a in articles
                ]
            }
    except Exception:
        pass

    return _stub()


def _stub() -> dict:
    return {
        "articles": [
            {
                "title": "US Housing Market Shows Signs of Stabilization",
                "description": "Mortgage rates easing slightly as inventory improves in key metros.",
                "url": "",
                "published": datetime.now().isoformat(),
                "source": "Stub",
            },
            {
                "title": "Real Estate Agents Adopting AI Tools at Record Rate",
                "description": "Survey shows 67% of RE professionals now use AI for listing descriptions.",
                "url": "",
                "published": datetime.now().isoformat(),
                "source": "Stub",
            },
        ],
        "stub": True,
    }
