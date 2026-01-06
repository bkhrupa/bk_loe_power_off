"""LOE Power Off integration."""
import logging
import re
from datetime import timedelta, datetime, date

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LOE Power Off from a config entry."""
    url = entry.data.get("url")
    group = entry.data.get("group")

    coordinator = ScheduleCoordinator(hass, url, group)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.warning("Initial update failed: %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


class ScheduleCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch LOE power off schedule."""

    def __init__(self, hass: HomeAssistant, url: str, group: str):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {group}",
            update_interval=timedelta(minutes=15),
        )
        self._url = url
        self._group = group

    @staticmethod
    def _parse_intervals(text: str):
        matches = re.findall(r"(\d{2}:\d{2})\s*до\s*(\d{2}:\d{2})", text)
        return [list(m) for m in matches]

    @staticmethod
    def _parse_date_from_name(name: str):
        match = re.search(r"(\d{2}:\d{2}) (\d{2}\.\d{2}\.\d{4})", name)
        if not match:
            return None

        time_str, date_str = match.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        except Exception:
            return None

    async def _async_update_data(self):
        updated_at = datetime.now().isoformat()

        async with aiohttp.ClientSession() as session:
            async with session.get(self._url) as resp:
                data = await resp.json()

        menus = [
            m for m in data.get("hydra:member", [])
            if m.get("type") == "photo-grafic"
        ]
        if not menus:
            raise UpdateFailed("No 'photo-grafic' menu found")

        valid_items = []

        for menu in menus:
            for item in menu.get("menuItems", []):
                for child in item.get("children", []):
                    raw_html = child.get("rawMobileHtml") or child.get("rawHtml")
                    if not raw_html:
                        continue

                    dt = self._parse_date_from_name(child.get("name", ""))
                    if not dt:
                        continue

                    valid_items.append({"datetime": dt, "html": raw_html})

        if not valid_items:
            raise UpdateFailed("No valid graph items")

        valid_items.sort(key=lambda x: x["datetime"], reverse=True)
        soup = BeautifulSoup(valid_items[0]["html"], "html.parser")

        # -------------------------------
        # ДАТА ГРАФІКА
        # -------------------------------
        day = None
        day_tag = soup.find(string=lambda t: "Графік погодинних відключень" in t)
        if day_tag:
            m = re.search(r"\d{2}\.\d{2}\.\d{4}", day_tag)
            if m:
                day = m.group()

        # -------------------------------
        # ОНОВЛЕННЯ З САЙТУ
        # -------------------------------
        updated = None
        updated_tag = soup.find(string=lambda t: "Інформація станом на" in t)
        if updated_tag:
            m = re.search(r"(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})", updated_tag)
            if m:
                updated = datetime.strptime(
                    f"{m.group(2)} {m.group(1)}",
                    "%d.%m.%Y %H:%M",
                ).isoformat()

        # -------------------------------
        # ПЕРЕВІРКА АКТУАЛЬНОСТІ
        # -------------------------------
        today = date.today()
        updated_ok = False

        if day:
            try:
                graph_day = datetime.strptime(day, "%d.%m.%Y").date()
                # дозволяємо графік, якщо він не старіший ніж 1 день
                updated_ok = graph_day >= (today - timedelta(days=1))

            except ValueError as err:
                _LOGGER.warning("Invalid graph day format '%s': %s", day, err)

        if not updated_ok:
            _LOGGER.info(
                "Graph is outdated (day=%s, updated=%s). Clearing schedule.",
                day,
                updated,
            )
            return {
                "day": day,
                "updated": updated,
                "updated_at": updated_at,
                "schedule": [],
                "all_groups": {},
            }

        # -------------------------------
        # ПАРСИНГ ГРУП
        # -------------------------------
        schedule = {}
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text.startswith("Група"):
                idx = text.find(".")
                if idx != -1:
                    key = text[:idx + 2].strip()
                    value = text[idx + 2:].strip()
                    schedule[key] = value

        target = self._group.rstrip(".").strip()
        group_text = next(
            (v for k, v in schedule.items() if k.rstrip(".").strip() == target),
            None,
        )

        intervals = self._parse_intervals(group_text) if group_text else []

        return {
            "day": day,
            "updated": updated,
            "updated_at": updated_at,
            "schedule": intervals,
            "all_groups": schedule,
        }
