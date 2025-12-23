"""LOE Power Off integration."""
import logging
import re
from datetime import timedelta, datetime

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

    _LOGGER.info(
        "Setting up LOE Power Off entry: %s, Group: %s",
        entry.entry_id,
        group,
    )

    coordinator = ScheduleCoordinator(hass, url, group)

    # Не валимо setup, якщо немає інтернету
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.warning(
            "Initial update failed, will retry later: %s",
            err,
        )

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
            update_interval=timedelta(minutes=20),
        )
        self._url = url
        self._group = group
        self._last_data = None  # кеш останніх валідних даних

    @staticmethod
    def _parse_intervals(text: str):
        """Convert schedule string into list of [start, end] intervals."""
        matches = re.findall(r"(\d{2}:\d{2})\s*до\s*(\d{2}:\d{2})", text)
        return [list(m) for m in matches]

    @staticmethod
    def _parse_date_from_name(name: str):
        """Парсить дату і час з поля name."""
        match = re.search(r"(\d{2}:\d{2}) (\d{2}\.\d{2}\.\d{4})", name)
        if not match:
            return None

        time_str, date_str = match.groups()
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        except Exception:
            return None

    async def _async_update_data(self):
        """Fetch data from LOE API and parse schedule."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self._url) as resp:
                    data = await resp.json()
        except Exception as err:
            _LOGGER.error("Error fetching data from LOE API: %s", err)

            # 🔁 fallback на кеш
            if self._last_data is not None:
                _LOGGER.warning("Using cached LOE data")
                return self._last_data

            raise UpdateFailed(f"Error fetching data: {err}")

        menus = [
            m for m in data.get("hydra:member", [])
            if m.get("type") == "photo-grafic"
        ]
        if not menus:
            raise UpdateFailed("No 'photo-grafic' menu found in API response")

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

                    valid_items.append({
                        "datetime": dt,
                        "html": raw_html,
                    })

        if not valid_items:
            raise UpdateFailed("No valid items with dates and rawHtml found")

        valid_items.sort(key=lambda x: x["datetime"], reverse=True)
        soup = BeautifulSoup(valid_items[0]["html"], "html.parser")

        # Дата графіка
        day = None
        day_tag = soup.find(string=lambda t: "Графік погодинних відключень" in t)
        if day_tag:
            match = re.search(r"\d{2}\.\d{2}\.\d{4}", day_tag)
            if match:
                day = match.group()

        # Час оновлення
        updated_datetime = None
        updated_tag = soup.find(string=lambda t: "Інформація станом на" in t)
        if updated_tag:
            match = re.search(
                r"(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})",
                updated_tag.strip(),
            )
            if match:
                try:
                    updated_datetime = datetime.strptime(
                        f"{match.group(2)} {match.group(1)}",
                        "%d.%m.%Y %H:%M",
                    ).isoformat()
                except Exception as err:
                    _LOGGER.warning("Failed to parse updated datetime: %s", err)

        # Парсимо всі групи
        schedule = {}
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text.startswith("Група"):
                idx = text.find(".")
                if idx != -1:
                    key = text[:idx + 2].strip()
                    value = text[idx + 2:].strip()
                    schedule[key] = value

        # Вибір групи
        group_schedule = None
        target_group = self._group.rstrip(".").strip()
        for key, val in schedule.items():
            if key.rstrip(".").strip() == target_group:
                group_schedule = val
                break

        if not group_schedule:
            _LOGGER.warning("Group '%s' not found in latest graph", self._group)

        parsed_intervals = (
            self._parse_intervals(group_schedule)
            if group_schedule
            else None
        )

        result = {
            "day": day,
            "updated": updated_datetime,
            "schedule": parsed_intervals,
            "all_groups": schedule,
        }

        # save to cache
        self._last_data = result

        return result
