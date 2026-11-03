"""Entidade base do KMV."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import APP_VERSION, DOMAIN
from .coordinator import KmvDataUpdateCoordinator


class KmvEntity(CoordinatorEntity[KmvDataUpdateCoordinator]):
    """Base: um único device KMV por conta."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KmvDataUpdateCoordinator) -> None:
        """Inicializa a entidade base."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        user = (coordinator.data or {}).get("user") or {}
        name = user.get("name") or user.get("fullName") or "Km de Vantagens"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Ipiranga",
            model="Km de Vantagens",
            name=name,
            sw_version=APP_VERSION,
        )
