from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from core.logging import logger
from storage.models import Channel


PROMO_MARKERS = ("#промо", "#реклама", "erid", "инн")


@dataclass(frozen=True)
class ParsedPost:
    text: str
    date: datetime
    url: str


def _to_utc_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _format_message_text(tag) -> str:
    if tag is None:
        return ""

    for span in tag.find_all("span"):
        span.unwrap()
    for br in tag.find_all("br"):
        br.replace_with("\n")
    for anchor in tag.find_all("a"):
        href = anchor.get("href")
        anchor.attrs = {"href": href} if href else {}

    return "".join(str(child) for child in tag.contents).strip()


async def channel_exists(channel_name: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://t.me/s/{channel_name}") as response:
            return response.status == 200


async def fetch_channel_posts(http_session: aiohttp.ClientSession, channel: Channel) -> list[ParsedPost]:
    url = f"https://t.me/s/{channel.name}"
    logger.info("Parsing channel {}", url)
    async with http_session.get(url) as response:
        if response.status != 200:
            logger.warning("Channel parse failed: url={}, status={}", url, response.status)
            return []
        html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    parsed_posts: list[ParsedPost] = []
    for post in soup.find_all(class_="tgme_widget_message"):
        if post.find(class_="tgme_widget_message_forwarded_from_name") is not None:
            continue

        message = _format_message_text(post.find(class_="tgme_widget_message_text"))
        if not message:
            continue

        message_lower = message.lower()
        if any(marker in message_lower for marker in PROMO_MARKERS):
            continue

        data_post = post.get("data-post")
        footer = post.find(class_="tgme_widget_message_footer")
        time_tag = footer.find("time") if footer else None
        if not data_post or not time_tag or not time_tag.get("datetime"):
            continue

        post_id = data_post.split("/")[-1]
        post_url = f"https://t.me/{channel.name}/{post_id}"
        post_date = _to_utc_naive(time_tag["datetime"])
        parsed_posts.append(ParsedPost(text=f"{message}\n{post_url}", date=post_date, url=post_url))

    logger.info("Parsed {} posts from {}", len(parsed_posts), channel.name)
    return parsed_posts
