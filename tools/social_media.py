import os
import requests
from dotenv import load_dotenv

load_dotenv()


def schedule_post(content: str, platform: str, scheduled_time: str = "") -> dict:
    token = os.getenv("BUFFER_ACCESS_TOKEN")
    if not token:
        print(f"[Buffer stub] Schedule to {platform}: {content[:80]}...")
        return {"stub": True, "platform": platform, "scheduled": True}

    profile_id = _get_profile_id(platform, token)
    if not profile_id:
        return {"error": f"No Buffer profile found for {platform}"}

    try:
        payload = {"text": content, "profile_ids[]": profile_id}
        if scheduled_time:
            payload["scheduled_at"] = scheduled_time

        resp = requests.post(
            "https://api.bufferapp.com/1/updates/create.json",
            headers={"Authorization": f"Bearer {token}"},
            data=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"scheduled": True, "update_id": data.get("updates", [{}])[0].get("id", "")}
        return {"error": f"Buffer returned {resp.status_code}", "body": resp.text}
    except Exception as e:
        return {"error": str(e)}


def _get_profile_id(platform: str, token: str) -> str:
    platform_map = {
        "LinkedIn": "linkedin",
        "Twitter": "twitter",
        "Instagram": "instagram",
    }
    service = platform_map.get(platform, platform.lower())

    try:
        resp = requests.get(
            "https://api.bufferapp.com/1/profiles.json",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            profiles = resp.json()
            for p in profiles:
                if p.get("service", "").lower() == service:
                    return p["id"]
    except Exception:
        pass
    return ""
