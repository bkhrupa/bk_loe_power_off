#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

API_URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic"
GROUP = "Група 1"  # змінити на потрібну групу


async def fetch_schedule():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as resp:
            data = await resp.json()

    print("=== JSON RESPONSE ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # шукаємо Menu з type "photo-grafic"
    menus = [m for m in data.get("hydra:member", []) if m.get("type") == "photo-grafic"]
    if not menus:
        print("No 'photo-grafic' menu found")
        return

    latest_raw_html = None
    for menu in menus:
        for item in menu.get("menuItems", []):
            for child in item.get("children", []):
                raw_html = child.get("rawMobileHtml") or child.get("rawHtml")
                if raw_html:
                    latest_raw_html = raw_html

    if not latest_raw_html:
        print("No rawHtml found in any menu child")
        return

    soup = BeautifulSoup(latest_raw_html, "html.parser")

    # Дата графіка
    day_tag = soup.find(string=lambda t: "Графік погодинних відключень" in t)
    day = day_tag.strip() if day_tag else None
    print("Графік на:", day)

    # Час оновлення
    updated_tag = soup.find(string=lambda t: "Інформація станом на" in t)
    updated = updated_tag.strip() if updated_tag else None
    print("Оновлено:", updated)

    # Словник груп
    schedule = {}
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text.startswith("Група"):
            name_part, info = text.split(".", 1)
            schedule[name_part.strip()] = info.strip()

    print("=== Розклад по групах ===")
    for k, v in schedule.items():
        print(f"{k}: {v}")

    group_schedule = schedule.get(GROUP)
    print(f"\n=== Розклад для {GROUP} ===")
    print(group_schedule)


if __name__ == "__main__":
    asyncio.run(fetch_schedule())
