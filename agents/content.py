import json
from agents.base import BaseAgent, AgentResult, Tool
from tools.web_research import search_re_news


SYSTEM_PROMPT = """
You are the Content strategist for a real estate SaaS startup targeting RE professionals.
Create valuable, authoritative content. Voice: professional, insightful, data-backed. Never salesy.

For each content request, produce a JSON object with:
{
  "title": "...",
  "platform": "LinkedIn|Twitter|Instagram",
  "content_type": "Market Update|Agent Tip|Product Insight|Industry News|Case Study",
  "body": "...",
  "hashtags": ["..."],
  "suggested_publish_time": "YYYY-MM-DD HH:MM",
  "hook": "First line / opening hook"
}
"""


class ContentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="content",
            system_prompt=SYSTEM_PROMPT,
            model="claude-sonnet-4-6",
            max_tokens=8192,
        )

    def _register_tools(self):
        self._tools = [
            Tool(
                name="get_re_news",
                description="Get latest real estate industry news and trends for content inspiration",
                input_schema={
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": [],
                },
                handler=self._get_news,
            ),
        ]

    def _get_news(self, topic: str = "real estate market trends") -> dict:
        return search_re_news(topic)

    def run(self, task_payload: dict) -> AgentResult:
        try:
            topic = task_payload.get("topic", "")
            platform = task_payload.get("platform", "LinkedIn")
            content_type = task_payload.get("content_type", "Market Update")

            prompt = f"""
Create {content_type} content for {platform}.
Topic: {topic or 'choose a relevant current RE industry topic'}
Research current news first, then write.
Return a single JSON object (no markdown wrapping).
"""
            raw = self._run_loop(prompt)

            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                content_obj = json.loads(raw[start:end]) if start >= 0 else {"body": raw}
            except Exception:
                content_obj = {"body": raw, "platform": platform}

            preview = {
                "title": content_obj.get("title", "Content Draft"),
                "platform": content_obj.get("platform", platform),
                "content_type": content_obj.get("content_type", content_type),
                "body": content_obj.get("body", ""),
                "hook": content_obj.get("hook", ""),
                "hashtags": content_obj.get("hashtags", []),
                "suggested_publish_time": content_obj.get("suggested_publish_time", ""),
                "action": "Schedule to social media via Buffer",
            }

            return AgentResult(
                agent="content",
                action_type="schedule_content",
                output={"content": content_obj},
                requires_approval=True,
                preview=preview,
            )
        except Exception as e:
            return AgentResult(
                agent="content",
                action_type="schedule_content",
                output={},
                requires_approval=False,
                error=str(e),
            )

    def execute_approved(self, action_type: str, preview: dict) -> dict:
        from tools.social_media import schedule_post
        result = schedule_post(
            content=preview.get("body", ""),
            platform=preview.get("platform", "LinkedIn"),
            scheduled_time=preview.get("suggested_publish_time", ""),
        )
        return {"scheduled": True, "platform": preview.get("platform"), "result": result}
