"""Binary sensor do KMV: tem pontos a expirar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import KmvEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import KmvConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KmvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Cria o binary sensor de pontos a expirar."""
    async_add_entities([KmvExpiringPointsBinarySensor(entry.runtime_data)])


class KmvExpiringPointsBinarySensor(KmvEntity, BinarySensorEntity):
    """Indica se há pontos prestes a expirar."""

    _attr_translation_key = "expiring_points"

    def __init__(self, coordinator) -> None:
        """Inicializa o binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_expiring_points"

    @property
    def is_on(self) -> bool:
        """True quando expiringPoints do points/summary for verdadeiro."""
        points = (self.coordinator.data or {}).get("points") or {}
        return bool(points.get("expiringPoints"))
