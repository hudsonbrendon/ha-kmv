"""Diagnósticos do KMV (sem credenciais)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import KmvConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KmvConfigEntry
) -> dict[str, Any]:
    """Retorna os dados do coordinator sem o CPF/refresh token."""
    coordinator = entry.runtime_data
    return {
        "data": coordinator.data,
        "last_update_success": coordinator.last_update_success,
    }
