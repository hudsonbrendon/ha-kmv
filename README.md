# KMV – Km de Vantagens (Ipiranga) para Home Assistant

Integração **não oficial** para o programa de fidelidade **Km de Vantagens / Abastece Aí**
da Ipiranga, feita por engenharia reversa do app `com.gigigo.ipirangaconectcar`
(KMV v6.12.5, React Native + Expo + Hermes).

Traz pra dentro do Home Assistant a economia acumulada, cashback, saldo de
combustível, saldo de pontos (Km), pontos a expirar e a última transação.

## Como funciona (resumo da engenharia reversa)

- **Backend:** `https://api.kmdevantagens.com.br/api/mobile`, com headers fixos
  `client_id` / `client_secret` / `X-App-Version` (extraídos do `app.config` do APK).
- **Login por senha não dá pra automatizar.** O endpoint
  `POST /public/api/v2/transition/login` exige `operationToken` de **reCAPTCHA
  Enterprise** + **QI Tech DeviceScan**, gerados dentro do app; sem eles o
  gateway responde `500` para qualquer requisição.
- **Caminho usado aqui: refresh token.**
  `POST /public/api/login/refresh`
  `{short_refresh_token, username:<CPF>, business_channel:"KMV_APP"}` →
  `{access_token, refresh_token}` — **sem captcha**. A integração troca o refresh
  token por um access token `Bearer` e renova sozinha (o backend roda o refresh
  token a cada uso; a integração persiste o novo no config entry).
- **Leituras** (`Authorization: Bearer`):
  - `/private/api/statement/account-summary` → `totalSavings`, `cashback`, `fuelCash`
  - `/private/api/statement/points/summary` → `expiringPoints`, pontos indisponíveis
  - `/private/api/statement/transactions` → últimas transações por posto
  - `/private/sdui/v2/points-program/home` → saldo de pontos (server-driven UI, best-effort)
  - `/private/api/users/me` → nome do titular

## Instalação

1. Copie `custom_components/kmv` para o seu `config/custom_components/` (ou via HACS, repositório customizado).
2. Reinicie o Home Assistant.
3. **Configurações → Dispositivos e serviços → Adicionar → KMV**.
4. Informe o **CPF** e o **refresh token**.

## Como capturar o refresh token

O refresh token (`short_refresh_token`) é emitido quando você faz login no app.
Para obtê-lo, intercepte o tráfego HTTPS do app uma única vez:

1. Em um Android com root ou emulador, instale o app KMV e um proxy MITM
   (ex.: mitmproxy/HTTP Toolkit) com o certificado confiável no sistema.
2. Faça login no app normalmente.
3. Procure a chamada `POST .../public/api/v2/transition/login` **ou**
   `.../public/api/login/refresh`. O corpo/resposta contém o `refresh_token`
   (e nas chamadas de refresh, o campo `short_refresh_token` enviado).
4. Use esse valor na integração. A partir daí o HA renova sozinho.

> Observação: por ser antifraude forte, o token é ligado ao device/sessão.
> Se o app invalidar a sessão (logout, troca de aparelho), capture de novo.

## Sensores

| Entidade | Fonte |
|---|---|
| `sensor.*_economia_total` | `account-summary.totalSavings` (R$) |
| `sensor.*_cashback` | `account-summary.cashback` (R$) |
| `sensor.*_combustivel_acumulado` | `account-summary.fuelCash` (R$) |
| `sensor.*_saldo_de_pontos` | SDUI points-program/home (Km) |
| `sensor.*_pontos_indisponiveis` | `points/summary.unavailable[]` |
| `sensor.*_ultima_transacao` | `transactions` (posto + valor nos atributos) |
| `binary_sensor.*_pontos_a_expirar` | `points/summary.expiringPoints` |

## Aviso

Projeto independente, sem vínculo com a Ipiranga/Ultra. Use por sua conta e
risco, respeitando os termos de uso do app. As chaves `client_id`/`client_secret`
são as do app público e não dão acesso a nada sem um token válido do usuário.
