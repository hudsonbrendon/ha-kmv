"""Config flow do KMV (CPF + refresh token capturado do app)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    KmvApiClient,
    KmvApiCommunicationError,
    KmvApiError,
    KmvAuthError,
)
from .const import CONF_CPF, CONF_REFRESH_TOKEN, DOMAIN


class KmvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fluxo de configuração via UI.

    O login por senha é bloqueado por reCAPTCHA + DeviceScan no app, então aqui
    pedimos o CPF e o refresh token (short_refresh_token) capturado de uma
    sessão logada no app — ver README.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pede CPF e refresh token do app KMV."""
        errors: dict[str, str] = {}
        if user_input is not None:
            cpf = "".join(ch for ch in user_input[CONF_CPF] if ch.isdigit())
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()
            try:
                client = KmvApiClient(
                    cpf=cpf,
                    refresh_token=refresh_token,
                    session=async_get_clientsession(self.hass),
                )
                await client.async_login()
            except KmvAuthError:
                errors["base"] = "invalid_auth"
            except KmvApiCommunicationError:
                errors["base"] = "cannot_connect"
            except KmvApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(cpf)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"KMV ({cpf[:3]}***{cpf[-2:]})",
                    data={
                        CONF_CPF: cpf,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CPF): str,
                    vol.Required(CONF_REFRESH_TOKEN): str,
                }
            ),
            errors=errors,
        )
