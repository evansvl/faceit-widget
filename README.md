# faceit-widget

A worker that keeps a Discord profile widget in sync with your FACEIT CS2 stats.
Every `INTERVAL` seconds it pulls your latest match from the FACEIT API (level,
elo, last map, K/D/A, calibration progress) and PATCHes the dynamic fields of
your Discord application profile widget.

No secrets live in the code. Everything is read from environment variables.

- [Setup](#setup)
- [Running](#running)
- [Deploying](#deploying)
- [Widget fields](#widget-fields)
- [Map image cropping](#map-image-cropping)
- [Season reset](#season-reset)

---

## Setup

There are two sides to get working: the **Discord widget** (a one-time manual
setup in the Developer Portal) and the **credentials** this script needs. Do the
Discord side first, collect the IDs and token as you go, then fill in FACEIT.

### Prerequisites

- Python 3.9+
- `pip install httpx`
- A Discord account and a FACEIT account

### 1. Create the Discord application

1. Go to <https://discord.com/developers/applications>
2. **New Application**, name it (for example `FACEIT Widget`), **Create**
3. On **General Information**, copy the **Application ID** — this is `APP_ID`

### 2. Enable widget / Social SDK access

Profile widgets are part of Discord's Social SDK. In the application, open the
Social SDK / widget access section and complete whatever access form Discord
currently presents, then submit it. Without widget access the app exists but the
editor flow will not work.

### 3. Open the widget editor

Look for the **Widget** section in the application sidebar. If it is not visible,
Discord currently gates the editor behind a DevTools snippet: open DevTools on
the Developer Portal, run the current widget-editor enable snippet, refresh the
page, and the **Widget** section appears.

> The exact portal navigation and the enable snippet are Discord's current flow
> and change from time to time. If the paths below do not match what you see,
> the field names in [Widget fields](#widget-fields) are what matters — wire your
> layout to those names however the editor lets you.

### 4. Build the widget layout

Add fields whose names match exactly what the script sends. A layout that fits
the data this worker produces:

**Hero section (top)**

| Component | Field name | What shows up |
|-----------|------------|---------------|
| Image | `map_image` | Last match map, cropped to sit under the rounded top |
| Title | `username` | Your FACEIT nickname |
| Subtitle 1 | `sub_1` | Level label, e.g. `Level 8` / `Calibration` |
| Subtitle 2 | `sub_2` | e.g. `120 Elo from Level 9` |
| Subtitle 3 | `sub_3` | e.g. `Current Elo: 1830` |
| Progress bar | `current` / `max` | Elo progress inside the level (numbers) |

**Stats / secondary**

| Component | Field name | What shows up |
|-----------|------------|---------------|
| Image | `level_image` | FACEIT level icon |
| Stat | `map_name` | Map name, e.g. `Mirage` |
| Stat | `kda` | Kills/Deaths/Assists of the last match |
| Stat | `elo_change` | `+25` / `-25` |
| Stat | `status` | `Current Elo: 1830` or `Calibration in progress` |

`current` and `max` must be **number** fields or the progress bar will not
render. Everything else is text, except `map_image` / `level_image` which are
images.

### 5. Publish

Save the layout and **Publish**. Confirm.

### 6. Authorize your account

In the app's OAuth2 settings, authorize the application with your own Discord
account using the widget/social scope the current flow requires. This is what
lets the app write to your profile.

### 7. Add the widget to your profile

Add the widget app to your own Discord profile through the widget interface in
the client. Once it is on your profile, this script's PATCH updates it live.

### 8. Create the bot and copy the token

1. Application → **Bot** → **Reset Token**
2. Copy the token — this is `DISCORD_BOT_TOKEN`

### 9. Get your Discord user ID

Enable Developer Mode (Settings → Advanced → Developer Mode), then right-click
your own avatar → **Copy User ID**. This is `USER_ID`.

### 10. FACEIT API key and nickname

1. Go to <https://developers.faceit.com>, sign in, open the API Keys section and
   create a **server-side** key. Server-side, not client-side — the script sends
   it as a `Bearer` token to `open.faceit.com/data/v4`. This is `FACEIT_API_KEY`.
2. `FACEIT_NICKNAME` is your exact FACEIT nickname (the one in your profile URL).
   It is resolved to a `player_id` on startup, so it has to match.

---

## Running

All values come from environment variables. The script refuses to start if any
required one is missing.

| Variable | Required | What it is |
|----------|----------|------------|
| `FACEIT_API_KEY` | yes | FACEIT server-side API key |
| `FACEIT_NICKNAME` | yes | Your FACEIT nickname (lookups + widget username) |
| `DISCORD_BOT_TOKEN` | yes | Bot token of the app that owns the widget |
| `APP_ID` | yes | Discord application ID |
| `USER_ID` | yes | Your Discord user ID |
| `INTERVAL` | no | Seconds between updates, defaults to `120` |

sh / bash:

```sh
export FACEIT_API_KEY=...
export FACEIT_NICKNAME=...
export DISCORD_BOT_TOKEN=...
export APP_ID=...
export USER_ID=...
python faceit.py
```

PowerShell:

```powershell
$env:FACEIT_API_KEY = "..."
$env:FACEIT_NICKNAME = "..."
$env:DISCORD_BOT_TOKEN = "..."
$env:APP_ID = "..."
$env:USER_ID = "..."
python faceit.py
```

It runs an infinite loop, updating every `INTERVAL` seconds. Errors in a single
iteration are logged and swallowed; the loop keeps going.

---

## Deploying

It is a single long-running process. Any way you keep a Python loop alive works.

### systemd

`/etc/systemd/system/faceit-widget.service`:

```ini
[Unit]
Description=FACEIT Discord widget
After=network-online.target

[Service]
WorkingDirectory=/opt/faceit-widget
ExecStart=/usr/bin/python3 faceit.py
EnvironmentFile=/opt/faceit-widget/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`/opt/faceit-widget/.env` (root-only, `chmod 600`):

```
FACEIT_API_KEY=...
FACEIT_NICKNAME=...
DISCORD_BOT_TOKEN=...
APP_ID=...
USER_ID=...
```

```sh
systemctl enable --now faceit-widget
journalctl -u faceit-widget -f
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx
COPY faceit.py .
CMD ["python", "faceit.py"]
```

```sh
docker build -t faceit-widget .
docker run -d --restart unless-stopped \
  -e FACEIT_API_KEY=... \
  -e FACEIT_NICKNAME=... \
  -e DISCORD_BOT_TOKEN=... \
  -e APP_ID=... \
  -e USER_ID=... \
  faceit-widget
```

### Anything else

`nohup python faceit.py &`, a `screen`/`tmux` session, a free-tier worker, a
Raspberry Pi — it only needs Python, `httpx`, the environment variables, and
outbound HTTPS.

---

## Widget fields

The script writes these dynamic fields to
`PATCH /applications/{APP_ID}/users/{USER_ID}/identities/0/profile`. Your widget
template must expose fields with the same names or they are ignored:

- Text (`type 1`): `map_name`, `kda`, `elo_change`, `sub_1`, `sub_2`, `sub_3`,
  `status`
- Number (`type 2`): `current`, `max` — the progress bar
- Image (`type 3`): `map_image`, `level_image`

Level icons come from `evansvl/faceit-levels`, map art from
`ghostcap-gaming/cs2-map-images`.

## Map image cropping

Map art is not used raw. It is passed through wsrv.nl with the crop geometry
ported from [D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F): a small transparent
strip is added on top (17px at a 512x512 reference, scaled by
`sizeFactor^0.678`), the image is shifted down and bottom-cropped so it sits
cleanly under the widget's rounded top edge. See `map_widget_image`.

## Season reset

`SEASON_START` is a hardcoded unix timestamp used to count placement matches for
the calibration state. Update it once per FACEIT season (roughly every four
months).
