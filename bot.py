import json
import os
import re
from pathlib import Path

import requests


DISCORD_API = "https://discord.com/api/v10"
STATE_FILE = Path("state.json")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"필수 환경변수 {name}가 없습니다.")
    return value


BOT_TOKEN = required_env("DISCORD_BOT_TOKEN")
DEEPL_KEY = required_env("DEEPL_API_KEY")
SOURCE_CHANNEL_ID = required_env("SOURCE_CHANNEL_ID")
TARGET_CHANNEL_ID = required_env("TARGET_CHANNEL_ID")
DEEPL_API = (
    "https://api-free.deepl.com/v2/translate"
    if DEEPL_KEY.endswith(":fx")
    else "https://api.deepl.com/v2/translate"
)

discord_headers = {"Authorization": f"Bot {BOT_TOKEN}"}


def discord_request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{DISCORD_API}{path}",
        headers=discord_headers,
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def get_messages(channel_id: str, *, after: str | None = None, limit: int = 100):
    params = {"limit": limit}
    if after:
        params["after"] = after
    return discord_request("GET", f"/channels/{channel_id}/messages", params=params)


def translate(text: str) -> str:
    if not text or not re.search(r"[A-Za-z]", text):
        return text
    response = requests.post(
        DEEPL_API,
        headers={
            "Authorization": f"DeepL-Auth-Key {DEEPL_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "text": [text],
            "source_lang": "EN",
            "target_lang": "KO",
            "preserve_formatting": True,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["translations"][0]["text"]


def clipped(text: str, maximum: int) -> str:
    return text if len(text) <= maximum else text[: maximum - 1] + "…"


def translated_embed(source: dict, message_id: str) -> dict:
    embed = {}
    if source.get("title"):
        embed["title"] = clipped(translate(source["title"]), 256)
    if source.get("description"):
        embed["description"] = clipped(translate(source["description"]), 4096)
    if source.get("url"):
        embed["url"] = source["url"]
    if source.get("color") is not None:
        embed["color"] = source["color"]
    if source.get("thumbnail", {}).get("url"):
        embed["thumbnail"] = {"url": source["thumbnail"]["url"]}
    if source.get("image", {}).get("url"):
        embed["image"] = {"url": source["image"]["url"]}
    if source.get("author", {}).get("name"):
        embed["author"] = {
            "name": clipped(source["author"]["name"], 256),
            **({"url": source["author"]["url"]} if source["author"].get("url") else {}),
            **({"icon_url": source["author"]["icon_url"]} if source["author"].get("icon_url") else {}),
        }
    fields = []
    for field in source.get("fields", [])[:25]:
        fields.append(
            {
                "name": clipped(translate(field.get("name", "")), 256),
                "value": clipped(translate(field.get("value", "")) or "-", 1024),
                "inline": bool(field.get("inline", False)),
            }
        )
    if fields:
        embed["fields"] = fields
    footer_text = source.get("footer", {}).get("text", "")
    marker = f"원문 메시지 ID: {message_id}"
    embed["footer"] = {"text": clipped(f"{footer_text} | {marker}" if footer_text else marker, 2048)}
    if source.get("timestamp"):
        embed["timestamp"] = source["timestamp"]
    return embed


def already_sent_ids() -> set[str]:
    ids = set()
    for message in get_messages(TARGET_CHANNEL_ID, limit=100):
        for embed in message.get("embeds", []):
            footer = embed.get("footer", {}).get("text", "")
            match = re.search(r"원문 메시지 ID: (\d+)", footer)
            if match:
                ids.add(match.group(1))
    return ids


def post_translation(message: dict):
    message_id = message["id"]
    content = translate(message.get("content", ""))
    source_embeds = message.get("embeds", [])
    embeds = [translated_embed(e, message_id) for e in source_embeds[:10]]

    if not embeds:
        embeds = [{"footer": {"text": f"원문 메시지 ID: {message_id}"}}]

    attachment_links = [a.get("url") for a in message.get("attachments", []) if a.get("url")]
    parts = []
    if content:
        parts.append(content)
    if attachment_links:
        parts.append("\n".join(attachment_links))
    if not parts and not source_embeds:
        parts.append("번역할 텍스트가 없는 공지입니다.")

    payload = {
        "content": clipped("\n\n".join(parts), 2000),
        "embeds": embeds,
        "allowed_mentions": {"parse": []},
    }
    discord_request("POST", f"/channels/{TARGET_CHANNEL_ID}/messages", json=payload)


def load_state() -> str | None:
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_message_id")


def save_state(message_id: str):
    STATE_FILE.write_text(
        json.dumps({"last_message_id": message_id}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    last_id = load_state()
    if not last_id:
        latest = get_messages(SOURCE_CHANNEL_ID, limit=1)
        if latest:
            save_state(latest[0]["id"])
            print("첫 실행: 현재 최신 공지를 기준점으로 저장했습니다.")
        else:
            print("첫 실행: 원본 채널에 메시지가 없습니다.")
        return

    messages = get_messages(SOURCE_CHANNEL_ID, after=last_id, limit=100)
    if not messages:
        print("새 공지가 없습니다.")
        return

    sent_ids = already_sent_ids()
    for message in sorted(messages, key=lambda item: int(item["id"])):
        if message["id"] not in sent_ids:
            post_translation(message)
            print(f"번역 완료: {message['id']}")
        save_state(message["id"])


if __name__ == "__main__":
    main()
