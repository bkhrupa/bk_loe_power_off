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

    _LOGGER.info("Setting up LOE Power Off entry: %s, Group: %s", entry.entry_id, group)

    coordinator = ScheduleCoordinator(hass, url, group)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    )

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

    @staticmethod
    def _parse_intervals(text: str):
        """Convert schedule string into list of [start, end] intervals."""
        # Шукаємо всі інтервали виду "08:00 до 12:00"
        matches = re.findall(r"(\d{2}:\d{2})\s*до\s*(\d{2}:\d{2})", text)
        return [list(m) for m in matches]

    async def _async_update_data(self):
        """Fetch data from LOE API and parse schedule."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self._url) as resp:
                    data = await resp.json()
        except Exception as err:
            _LOGGER.error("Error fetching data from LOE API: %s", err)
            raise UpdateFailed(f"Error fetching data: {err}")

        menus = [m for m in data.get("hydra:member", []) if m.get("type") == "photo-grafic"]
        if not menus:
            raise UpdateFailed("No 'photo-grafic' menu found in API response")

        latest_raw_html = None
        for menu in menus:
            for item in menu.get("menuItems", []):
                for child in item.get("children", []):
                    raw_html = child.get("rawMobileHtml") or child.get("rawHtml")
                    if raw_html:
                        latest_raw_html = raw_html

        if not latest_raw_html:
            raise UpdateFailed("No rawHtml found in any menu child")

        soup = BeautifulSoup(latest_raw_html, "html.parser")

        # Дата графіка (тільки дата)
        day_tag = soup.find(string=lambda t: "Графік погодинних відключень" in t)
        day = None
        if day_tag:
            match = re.search(r"\d{2}\.\d{2}\.\d{4}", day_tag)
            if match:
                day = match.group()

        # Час оновлення
        updated_datetime = None
        updated_tag = soup.find(string=lambda t: "Інформація станом на" in t)

        if updated_tag:
            updated_text = updated_tag.strip()
            match = re.search(r"(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})", updated_text)
            if match:
                time_part = match.group(1)
                date_part = match.group(2)
                dt_string = f"{date_part} {time_part}"

                try:
                    dt_obj = datetime.strptime(dt_string, "%d.%m.%Y %H:%M")
                    updated_datetime = dt_obj.isoformat()
                except Exception as e:
                    _LOGGER.warning("Failed to parse updated datetime '%s': %s", dt_string, e)

        # Парсимо всі групи
        schedule = {}
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text.startswith("Група"):
                split_index = text.find(".")
                if split_index != -1:
                    group_key = text[:split_index + 2].strip()
                    group_value = text[split_index + 2:].strip()
                    schedule[group_key] = group_value

        # Вибір групи
        group_schedule = None
        target_group = self._group.rstrip(".").strip()
        for key, val in schedule.items():
            normalized_key = key.rstrip(".").strip()
            if normalized_key == target_group:
                group_schedule = val
                break

        if not group_schedule:
            _LOGGER.warning("Group '%s' not found in latest graph", self._group)

        # конвертуємо текст у масив інтервалів
        parsed_intervals = self._parse_intervals(group_schedule) if group_schedule else None

        return {
            "day": day,
            "updated": updated_datetime,
            "schedule": parsed_intervals, # масив для стейту
            "all_groups": schedule,
        }
