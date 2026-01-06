"""LOE Power Off sensor."""
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get("name", "LOE Power Off")
    group = entry.data.get("group")

    async_add_entities([LoePowerOffSensor(coordinator, name, group)])


class LoePowerOffSensor(CoordinatorEntity, Entity):
    """Sensor for LOE power off schedule."""

    def __init__(self, coordinator, name: str, group: str):
        """Initialize sensor."""
        super().__init__(coordinator)
        self._name = name
        self._group = group

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"loe_power_off_{self._group.replace(' ', '_')}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("schedule")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "day": self.coordinator.data.get("day"),
            "updated": self.coordinator.data.get("updated"),
            "updated_at": self.coordinator.data.get("updated_at"),
            "schedule": self.coordinator.data.get("schedule"),
            "all_groups": self.coordinator.data.get("all_groups"),
        }
