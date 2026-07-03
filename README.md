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

This is where you tell Discord which live value goes into which slot. Every
dynamic value is wired the same way: set the component's **Value Type** to
**User Data** and type the **Data Field** name exactly as the script sends it.
A field name that does not match is simply never filled.

Optionally set a **Fallback** per field — shown before the first update lands
(or if a value is missing). A fallback is either a **Custom String** or an
**Application Asset** (an image you upload to the app under Rich Presence → Art
Assets, referenced by its Asset Key).

The layout below is exactly the reference widget. `Custom String` means a fixed
label you type in, not a data field.

**Image** (hero)

| Field | Value Type | Data Field | Fallback |
|-------|-----------|------------|----------|
| Image | User Data | `map_image` | Application Asset, key `mirage` |

**Title**

| Field | Value Type | Content |
|-------|-----------|---------|
| Text | Custom String | `Last Played Match:` |

**Subtitle 1 / 2 / 3** — each has a fixed Label plus a User Data value:

| Component | Label (Custom String) | Value Type | Data Field | Fallback |
|-----------|-----------------------|-----------|------------|----------|
| Subtitle 1 | `Map` | User Data | `map_name` | `Mirage` |
| Subtitle 2 | `K/D/A` | User Data | `kda` | `24/19/12` |
| Subtitle 3 | `Elo Change` | User Data | `elo_change` | `+21` |

**Objective**

| Field | Value Type | Data Field | Fallback |
|-------|-----------|------------|----------|
| Image | User Data | `level_image` | Application Asset, key `lvl9` |
| Name | User Data | `sub_1` | `Level: 9` |
| Description | User Data | `sub_2` | `19 Elo from Level 10` |

**Progress**

| Field | Value Type | Data Field |
|-------|-----------|------------|
| Current Value | User Data | `current` |
| Max Value | User Data | `max` |

`current` and `max` are numbers — the elo progress bar inside the current level.
The script also sends `sub_3` and `status`; the reference widget does not use
them, but they are there if you want to add more slots.

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

All config comes from environment variables. The script refuses to start if any
required one is missing.

| Variable | Required | What it is |
|----------|----------|------------|
| `FACEIT_API_KEY` | yes | FACEIT server-side API key |
| `FACEIT_NICKNAME` | yes | Your FACEIT nickname (lookups + widget username) |
| `DISCORD_BOT_TOKEN` | yes | Bot token of the app that owns the widget |
| `APP_ID` | yes | Discord application ID |
| `USER_ID` | yes | Your Discord user ID |
| `INTERVAL` | no | Seconds between updates, defaults to `120` |
| `SEASON_START` | no | Season start as a unix timestamp, see [Season reset](#season-reset) |

### Using a .env file (easiest)

On startup the script loads a `.env` file sitting next to `faceit.py`, so you do
not have to export anything by hand. Real environment variables still win over
`.env`, so it is safe on a server too. Create `.env`:

```
FACEIT_API_KEY=your-server-side-key
FACEIT_NICKNAME=your-nickname
DISCORD_BOT_TOKEN=your-bot-token
APP_ID=your-application-id
USER_ID=your-discord-user-id
# optional
INTERVAL=120
SEASON_START=1776816000
```

Then just:

```sh
python faceit.py
```

`.env` is gitignored — keep your keys in it, not in the code.

### Or export the variables

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

Map art is not used raw. It runs through wsrv.nl as a single square cover-crop
anchored to the top of the image (`fit=cover&a=top`), so the top of the map is
kept and the widget's rounded top edge sits over clean image rather than an
awkward seam. See `map_widget_image`.

The [D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F) tool also lays a ~17px
transparent strip over the top. That step needs two chained image operations
(crop, then pad) and wsrv.nl refuses to proxy its own output, so it cannot be
reproduced in a single URL. The strip is ~3% of the frame and barely visible; if
you want it exactly, pre-process the map images offline with D.W.I.F and host
them (the same way the fallback Application Assets are prepared).

## Season reset

FACEIT counts 10 placement matches per season for calibration, and its public
Data API does not expose season boundaries (checked: the player object carries
no season or placement data). So the season start is a `SEASON_START` unix
timestamp you provide via the environment, defaulting to Season 8
(`1776816000`, 2026-04-22 UTC). Update it once per season, roughly every four
months — set `SEASON_START` in `.env` and restart, no code change.
