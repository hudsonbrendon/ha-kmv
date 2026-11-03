"""Cliente da API do KMV (engenharia reversa do app com.gigigo.ipirangaconectcar).

O app "Km de Vantagens / Abastece Aí" (Ipiranga) é React Native + Expo + Hermes,
muito server-driven UI. O backend é `https://api.kmdevantagens.com.br/api/mobile`,
com headers fixos `client_id`/`client_secret`/`X-App-Version`.

**Login por senha não funciona fora do app**: o gateway exige `operationToken`
de reCAPTCHA Enterprise + QI Tech DeviceScan gerados no device (sem eles o
gateway responde 500 p/ qualquer body). O caminho viável para o HA é o
**refresh token**: `POST /public/api/login/refresh`
`{short_refresh_token, username:<CPF>, business_channel:"KMV_APP"}` →
`{access_token, refresh_token}` (sem captcha). O usuário captura o refresh token
uma vez de uma sessão logada no app (ver README) e o HA renova sozinho daí.

As leituras usam `Authorization: Bearer <access_token>` contra `/private/...`.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any

import aiohttp

from .const import (
    API_BASE,
    APP_VERSION,
    BUSINESS_CHANNEL,
    CLIENT_ID,
    CLIENT_SECRET,
    LOGGER,
)

_TIMEOUT = 60  # app usa apiTimeout 60000ms


class KmvApiError(Exception):
    """Erro geral da API."""


class KmvApiCommunicationError(KmvApiError):
    """Falha de comunicação/timeout."""


class KmvAuthError(KmvApiError):
    """Refresh token inválido ou sessão expirada."""


def _base_headers() -> dict[str, str]:
    return {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "X-App-Version": APP_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"okhttp/4.12.0 KMV/{APP_VERSION}",
    }


class KmvApiClient:
    """Cliente autenticado do KMV (refresh token -> Bearer access token)."""

    def __init__(
        self, cpf: str, refresh_token: str, session: aiohttp.ClientSession
    ) -> None:
        """cpf = CPF só dígitos; refresh_token = short_refresh_token do app."""
        self._cpf = "".join(ch for ch in cpf if ch.isdigit())
        self._refresh_token = refresh_token
        self._session = session
        self._access_token: str | None = None

    @property
    def refresh_token(self) -> str:
        """Refresh token atual (roda a cada renovação; persistir no entry)."""
        return self._refresh_token

    # --- auth ---

    async def async_login(self) -> None:
        """Troca o refresh token por um access token (valida as credenciais)."""
        url = f"{API_BASE}/public/api/login/refresh"
        body = {
            "short_refresh_token": self._refresh_token,
            "username": self._cpf,
            "business_channel": BUSINESS_CHANNEL,
        }
        try:
            async with asyncio.timeout(_TIMEOUT):
                resp = await self._session.post(url, headers=_base_headers(), json=body)
                data = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com o KMV: {err}"
            raise KmvApiCommunicationError(msg) from err
        if resp.status in (401, 403):
            msg = "refresh token recusado pelo KMV (401/403) — capture um novo no app"
            raise KmvAuthError(msg)
        if resp.status >= 400:
            msg = f"KMV recusou o refresh ({resp.status}): {str(data)[:200]}"
            raise KmvAuthError(msg)
        access = (data or {}).get("access_token")
        if not access:
            msg = f"resposta de refresh sem access_token: {str(data)[:200]}"
            raise KmvAuthError(msg)
        self._access_token = access
        # o backend roda o refresh token a cada uso
        new_refresh = (data or {}).get("refresh_token")
        if new_refresh:
            self._refresh_token = new_refresh

    async def _token(self) -> str:
        if self._access_token is None:
            await self.async_login()
        return self._access_token  # type: ignore[return-value]

    # --- request genérico (renova 1x em 401) ---

    async def _get(self, path: str, *, retry: bool = True) -> Any:
        token = await self._token()
        url = f"{API_BASE}{path}"
        headers = {**_base_headers(), "Authorization": f"Bearer {token}"}
        try:
            async with asyncio.timeout(_TIMEOUT):
                resp = await self._session.get(url, headers=headers)
                if resp.status in (401, 403) and retry:
                    self._access_token = None
                    await self.async_login()
                    return await self._get(path, retry=False)
                body = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com o KMV: {err}"
            raise KmvApiCommunicationError(msg) from err
        if resp.status in (401, 403):
            msg = "token recusado pelo KMV (401/403)"
            raise KmvAuthError(msg)
        if resp.status >= 400:
            msg = f"KMV respondeu {resp.status} em {path}: {str(body)[:200]}"
            raise KmvApiError(msg)
        return body

    @staticmethod
    def _data(payload: Any) -> Any:
        """A maioria das respostas vem como {meta, data, ...}."""
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    # --- leituras (schemas da RE do bundle Hermes) ---

    async def async_account_summary(self) -> dict[str, Any]:
        """GET /private/api/statement/account-summary.

        data = {totalSavings, cashback, fuelCash, unavailable, staleSince}.
        """
        return self._data(await self._get("/private/api/statement/account-summary")) or {}

    async def async_points_summary(self) -> dict[str, Any]:
        """GET /private/api/statement/points/summary.

        data = {expiringPoints(bool), unavailable[...]}.
        """
        return self._data(await self._get("/private/api/statement/points/summary")) or {}

    async def async_transactions(self) -> dict[str, Any]:
        """GET /private/api/statement/transactions.

        {meta, data:[{date, items:[{transactionId, storeId, resellerName,
        totalValue, balance, status}]}], paging:{page,size,totalElements,totalPages}}.
        """
        return await self._get("/private/api/statement/transactions") or {}

    async def async_points_home(self) -> dict[str, Any]:
        """GET /private/sdui/v2/points-program/home (server-driven UI; best-effort)."""
        return await self._get("/private/sdui/v2/points-program/home") or {}

    async def async_user(self) -> dict[str, Any]:
        """GET /private/api/users/me."""
        return self._data(await self._get("/private/api/users/me")) or {}
