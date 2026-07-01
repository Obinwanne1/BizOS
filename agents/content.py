from agents.base import BaseAgent, AgentResult, Tool
from tools.web_research import search_re_news
from utils.json_parser import extract_json
from utils.config_loader import get_model, get_max_tokens, get_persona

_PERSONA = get_persona("content") or (
    "You are the Content strategist for a real estate SaaS startup targeting RE professionals. "
    "Create valuable, authoritative content. Voice: professional, insightful, data-backed. Never salesy."
)

SYSTEM_PROMPT = _PERSONA + """

Produce a JSON object with exactly these keys:
{
  "title": "...",
  "platform": "LinkedIn|Twitter|Instagram",
  "content_type": "Market Update|Agent Tip|Product Insight|Industry News|Case Study",
  "body": "...",
  "hashtags": ["..."],
  "suggested_publish_time": "YYYY-MM-DD HH:MM",
  "hook": "First sentence — the opening hook"
}

Return raw JSON only. No markdown fences, no prose outside the JSON.
"""


class ContentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="content",
            system_prompt=SYSTEM_PROMPT,
            model=get_model("content"),
            max_tokens=get_max_tokens("content"),
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

            prompt = (
                f"Create {content_type} content for {platform}.\n"
                f"Topic: {topic or 'choose the most relevant current RE industry topic'}\n"
                "Use get_re_news first to ground the content in real trends.\n"
                "Return a single JSON object — no markdown, no extra text."
            )
            raw = self._run_loop(prompt)
            content_obj = extract_json(raw, expect="object")

            if not content_obj.get("body"):
                content_obj = {"body": raw, "platform": platform, "title": "Content Draft"}

            hashtags = content_obj.get("hashtags") or []
            if isinstance(hashtags, str):
                hashtags = [h.strip() for h in hashtags.replace(",", " ").split() if h.strip()]

            preview = {
                "title": content_obj.get("title", "Content Draft"),
                "platform": content_obj.get("platform", platform),
                "content_type": content_obj.get("content_type", content_type),
                "body": content_obj.get("body", ""),
                "hook": content_obj.get("hook", ""),
                "hashtags": hashtags,
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
