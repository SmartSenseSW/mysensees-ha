from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MySenseesApiClient
from .const import CONF_BASE_URL, CONF_GATEWAY_ID, DEFAULT_BASE_URL, DOMAIN, PLATFORMS
from .coordinator import MySenseesDataUpdateCoordinator

MySenseesConfigEntry = ConfigEntry[MySenseesDataUpdateCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration via YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MySenseesConfigEntry) -> bool:
    """Set up MySensees from a config entry."""
    session = async_get_clientsession(hass)
    client = MySenseesApiClient(
        session=session,
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = MySenseesDataUpdateCoordinator(
        hass=hass,
        client=client,
        gateway_id=entry.data[CONF_GATEWAY_ID],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MySenseesConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok
