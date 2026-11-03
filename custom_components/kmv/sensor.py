"""Sensores do KMV (economia, cashback, combustível, pontos, transações)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from .entity import KmvEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import KmvConfigEntry, KmvDataUpdateCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class KmvSensorDescription(SensorEntityDescription):
    """Descrição de um sensor do KMV com extrator de valor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _account(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("account") or {}


def _latest_tx(data: dict[str, Any]) -> dict[str, Any] | None:
    groups = ((data or {}).get("transactions") or {}).get("data") or []
    for group in groups:
        items = group.get("items") or []
        if items:
            tx = dict(items[0])
            tx.setdefault("date", group.get("date"))
            return tx
    return None


def _tx_attrs(data: dict[str, Any]) -> dict[str, Any]:
    tx = _latest_tx(data) or {}
    return {
        "reseller": tx.get("resellerName"),
        "store_id": tx.get("storeId"),
        "total_value": tx.get("totalValue"),
        "status": tx.get("status"),
        "transaction_id": tx.get("transactionId"),
        "date": tx.get("date"),
    }


SENSORS: tuple[KmvSensorDescription, ...] = (
    KmvSensorDescription(
        key="total_savings",
        translation_key="total_savings",
        native_unit_of_measurement="BRL",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _account(d).get("totalSavings"),
    ),
    KmvSensorDescription(
        key="cashback",
        translation_key="cashback",
        native_unit_of_measurement="BRL",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _account(d).get("cashback"),
    ),
    KmvSensorDescription(
        key="fuel_cash",
        translation_key="fuel_cash",
        native_unit_of_measurement="BRL",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _account(d).get("fuelCash"),
    ),
    KmvSensorDescription(
        key="points_balance",
        translation_key="points_balance",
        native_unit_of_measurement="Km",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("points_balance"),
    ),
    KmvSensorDescription(
        key="expiring_unavailable",
        translation_key="expiring_unavailable",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(((d or {}).get("points") or {}).get("unavailable") or []),
    ),
    KmvSensorDescription(
        key="last_transaction",
        translation_key="last_transaction",
        value_fn=lambda d: (_latest_tx(d) or {}).get("resellerName"),
        attrs_fn=_tx_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KmvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Cria os sensores do KMV."""
    coordinator = entry.runtime_data
    async_add_entities(KmvSensor(coordinator, desc) for desc in SENSORS)


class KmvSensor(KmvEntity, SensorEntity):
    """Sensor genérico do KMV baseado em descrição."""

    entity_description: KmvSensorDescription

    def __init__(
        self,
        coordinator: KmvDataUpdateCoordinator,
        description: KmvSensorDescription,
    ) -> None:
        """Inicializa o sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Valor extraído de coordinator.data."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Atributos extras, quando a descrição definir."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data or {})
