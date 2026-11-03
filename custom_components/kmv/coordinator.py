"""Coordinator do KMV: saldo/economia + pontos + transações + perfil."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KmvApiError, KmvAuthError
from .const import CONF_REFRESH_TOKEN, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import KmvApiClient

type KmvConfigEntry = ConfigEntry[KmvDataUpdateCoordinator]


def find_points_balance(obj: Any) -> int | None:
    """Varre a árvore SDUI atrás do saldo de pontos (kmvPoints/points/balance).

    O home de pontos é server-driven UI, então o número vem embutido em algum
    componente. Procuramos chaves conhecidas com valor numérico, sem depender
    do layout exato.
    """
    keys = ("kmvPoints", "userBalance", "totalPoints", "pointsBalance")
    stack = [obj]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key in keys:
                val = node.get(key)
                if isinstance(val, (int, float)):
                    return int(val)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


class KmvDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Puxa resumo da conta, pontos e transações do KMV."""

    def __init__(
        self, hass: HomeAssistant, entry: KmvConfigEntry, client: KmvApiClient
    ) -> None:
        """Inicializa o coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.client = client
        self._entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            account, points, transactions, points_home, user = await asyncio.gather(
                self.client.async_account_summary(),
                self.client.async_points_summary(),
                self.client.async_transactions(),
                self.client.async_points_home(),
                self.client.async_user(),
                return_exceptions=True,
            )
        except KmvAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KmvApiError as err:
            raise UpdateFailed(str(err)) from err

        def ok(val: Any) -> Any:
            if isinstance(val, KmvAuthError):
                raise ConfigEntryAuthFailed(str(val))
            if isinstance(val, Exception):
                LOGGER.debug("leitura KMV indisponível: %s", val)
                return {}
            return val

        self._persist_refresh_token()

        return {
            "account": ok(account),
            "points": ok(points),
            "transactions": ok(transactions),
            "points_balance": find_points_balance(ok(points_home)),
            "user": ok(user),
        }

    def _persist_refresh_token(self) -> None:
        """O backend roda o refresh token; salva o novo no config entry."""
        current = self._entry.data.get(CONF_REFRESH_TOKEN)
        latest = self.client.refresh_token
        if latest and latest != current:
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, CONF_REFRESH_TOKEN: latest},
            )
