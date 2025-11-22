import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_NAME
from .const import DOMAIN, CONF_GROUP, CONF_DEFAULT_URL


class BkLoePowerOffConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for LOE Power Off integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=f"LOE Power Off ({user_input[CONF_GROUP]})",
                data=user_input,
            )

        schema = vol.Schema({
            vol.Optional(CONF_URL, default=CONF_DEFAULT_URL): str,
            vol.Required(CONF_GROUP): str,
            vol.Optional(CONF_NAME, default="LOE Power Off",): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema
        )
