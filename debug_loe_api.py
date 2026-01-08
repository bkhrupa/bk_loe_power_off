#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import OrderedDict

API_URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic"
GROUP = "Група 5.1"  # змінити на потрібну групу
MAX_RECORDS = 50  # кількість останніх записів, які беремо (збільшив для кількох днів)

def parse_date_from_name(name: str):
    """Парсить timestamp із назви"""
    match = re.search(r"(\d{2}:\d{2}) (\d{2}\.\d{2}\.\d{4})", name)
    if not match:
        return None
    time_str, date_str = match.groups()
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        return int(dt.timestamp())
    except Exception:
        return None

def group_items_by_day(items):
    """Групує список item по днях, залишає лише найновіший запис на кожен день"""
    grouped = {}
    for item in items:
        soup = BeautifulSoup(item["html"], "html.parser")
        header = soup.find("b", string=re.compile(r"Графік погодинних відключень на"))
        if header:
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", header.text)
            day = m.group() if m else None
        else:
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", item["name"])
            day = m.group() if m else None

        if not day:
            continue

        # залишаємо лише найновіший запис для дня
        if day not in grouped or item["timestamp"] > grouped[day]["timestamp"]:
            grouped[day] = item

    # сортуємо за датою
    return dict(OrderedDict(sorted(grouped.items(), key=lambda x: datetime.strptime(x[0], "%d.%m.%Y"))))

async def fetch_schedule():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as resp:
            data = await resp.json()

    menus = [m for m in data.get("hydra:member", []) if m.get("type") == "photo-grafic"]
    if not menus:
        print("No 'photo-grafic' menu found")
        return

    valid_items = []

    for menu in menus:
        for item in menu.get("menuItems", []):
            for child in item.get("children", []):
                raw_html = child.get("rawMobileHtml") or child.get("rawHtml")
                if not raw_html:
                    continue

                ts = parse_date_from_name(child.get("name", ""))
                if not ts:
                    continue

                valid_items.append({
                    "timestamp": ts,
                    "name": child.get("name", ""),
                    "html": raw_html,
                })

    if not valid_items:
        print("No valid items with dates and rawHtml found")
        return

    # сортуємо по timestamp, новіші перші
    valid_items.sort(key=lambda x: x["timestamp"], reverse=True)
    latest_items = valid_items[:MAX_RECORDS]

    print("\n=== ОСТАННІ ЗАПИСИ ===")
    print(json.dumps(latest_items, ensure_ascii=False, indent=2))

    # -------------------------------
    # ВСІ ЗАПИСИ ПО ДНЯХ (тільки найновіший на день)
    # -------------------------------
    items_by_day = group_items_by_day(latest_items)
    print("\n=== ВСІ ЗАПИСИ ПО ДНЯХ (найновіший на день) ===")
    print(json.dumps(items_by_day, ensure_ascii=False, indent=2))

    # -------------------------------
    # Розбір розкладу для конкретної групи
    # -------------------------------
    schedules_by_day = OrderedDict()
    for day, item in items_by_day.items():
        soup = BeautifulSoup(item["html"], "html.parser")
        groups = {}
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text.startswith("Група"):
                idx = text.find(".")
                if idx != -1:
                    groups[text[:idx + 2].strip()] = text[idx + 2:].strip()

        target = GROUP.rstrip(".").strip()
        group_text = next(
            (v for k, v in groups.items() if k.rstrip(".").strip() == target),
            None,
        )

        intervals = re.findall(r"(\d{2}:\d{2})\s*до\s*(\d{2}:\d{2})", group_text or "")
        schedules_by_day[day] = intervals

    print(f"\n=== Розклад для {GROUP} ===")
    print(json.dumps(schedules_by_day, ensure_ascii=False, indent=2))

    # -------------------------------
    # UPDATED (інформація про час останнього оновлення)
    # -------------------------------
    updated = None
    for item in latest_items:
        soup = BeautifulSoup(item["html"], "html.parser")
        tag = soup.find(string=lambda t: t and "Інформація станом на" in t)
        if tag:
            m = re.search(r"(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})", tag)
            if m:
                updated = datetime.strptime(f"{m.group(2)} {m.group(1)}", "%d.%m.%Y %H:%M").isoformat()
                break
    print("\n=== UPDATED ===")
    print(updated)

if __name__ == "__main__":
    asyncio.run(fetch_schedule())
