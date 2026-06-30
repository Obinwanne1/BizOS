import requests
from datetime import datetime


def search_re_news(topic: str = "real estate market trends") -> dict:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": f"real estate {topic}",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
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

    return {
        "articles": [
            {
                "title": "US Housing Market Shows Signs of Stabilization",
                "description": "Mortgage rates easing slightly as inventory improves in key metros.",
                "url": "",
                "published": datetime.now().isoformat(),
                "source": "Mock News",
            },
            {
                "title": "Real Estate Agents Adopting AI Tools at Record Rate",
                "description": "Survey shows 67% of RE professionals now use AI for listing descriptions.",
                "url": "",
                "published": datetime.now().isoformat(),
                "source": "Mock News",
            },
        ],
        "stub": True,
    }
