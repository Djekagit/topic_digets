import httpx
from openai import AsyncOpenAI

from core.logging import logger
from core.settings import settings
from storage.models import DigestGroup, Post
from storage.requests.ai_settings import get_ai_settings


TELEGRAM_MARKDOWN_SYSTEM_PROMPT = (
    "Ты пишешь готовые сообщения для Telegram. Отвечай строго в формате Telegram MarkdownV2. "
    "Верни только финальный дайджест без вступления, без фраз вроде 'Конечно' или "
    "'Вот дайджест', без послесловий, предложений продолжить и горизонтальных разделителей. "
    "Используй кликабельные ссылки в формате [текст](https://example.com). "
    "Не используй HTML, Markdown-таблицы и заголовки через #. "
    "Экранируй спецсимволы MarkdownV2 там, где они не являются частью разметки."
)


def build_prompt(*, default_prompt: str, custom_prompt: str | None, posts_text: str) -> str:
    template = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else default_prompt
    if "{posts}" in template:
        return template.replace("{posts}", posts_text)
    return f"{template}\n\nПосты:\n{posts_text}"


def build_chat_messages(prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": TELEGRAM_MARKDOWN_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


class OpenRouterSummarizer:
    def __init__(self, api_key: str, proxy: str | None = None):
        self.api_key = api_key
        self.proxy = proxy

    async def summarize(self, *, model: str, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        async with httpx.AsyncClient(proxy=self.proxy, timeout=120) as http_client:
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                http_client=http_client,
            )
            response = await client.chat.completions.create(
                model=model,
                messages=build_chat_messages(prompt),
            )
        return response.choices[0].message.content or ""


def format_posts_for_prompt(posts: list[Post]) -> str:
    return "\n\n".join(post.text for post in posts)


async def summarize_group_posts(session, *, group: DigestGroup, posts: list[Post]) -> str:
    ai_settings = await get_ai_settings(session)
    posts_text = format_posts_for_prompt(posts)
    prompt = build_prompt(
        default_prompt=ai_settings.default_prompt,
        custom_prompt=group.custom_prompt,
        posts_text=posts_text,
    )
    logger.info(
        "Generating digest via OpenRouter: group_id={}, posts={}, model={}",
        group.id,
        len(posts),
        ai_settings.model,
    )
    summarizer = OpenRouterSummarizer(settings.openrouter_api_key, settings.proxy)
    return await summarizer.summarize(model=ai_settings.model, prompt=prompt)
