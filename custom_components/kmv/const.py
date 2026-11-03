"""Constantes da integração KMV (Km de Vantagens / Abastece Aí - Ipiranga)."""

from __future__ import annotations

import logging

DOMAIN = "kmv"
LOGGER = logging.getLogger(__package__)

CONF_CPF = "cpf"
CONF_REFRESH_TOKEN = "refresh_token"

# Extraídos do app.config (Expo extra) do APK com.gigigo.ipirangaconectcar v6.12.5.
API_BASE = "https://api.kmdevantagens.com.br/api/mobile"
CLIENT_ID = "d9d02c8172354bf2bf8249c901996089"
CLIENT_SECRET = "1CCc5bC61f924b78aF71e15Ac554Ced4"
APP_VERSION = "6.12.5"
BUSINESS_CHANNEL = "KMV_APP"

DEFAULT_SCAN_INTERVAL_MINUTES = 60
