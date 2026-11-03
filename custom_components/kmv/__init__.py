"""Integração KMV (Km de Vantagens / Abastece Aí - Ipiranga) para Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KmvApiClient
from .const import CONF_CPF, CONF_REFRESH_TOKEN
from .coordinator import KmvConfigEntry, KmvDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: KmvConfigEntry) -> bool:
    """Configura a integração a partir de um config entry."""
    client = KmvApiClient(
        cpf=entry.data[CONF_CPF],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        session=async_get_clientsession(hass),
    )
    await client.async_login()

    coordinator = KmvDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KmvConfigEntry) -> bool:
    """Descarrega o config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
