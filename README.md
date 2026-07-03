# faceit-widget

Small worker that keeps a Discord profile widget in sync with your FACEIT CS2
stats. Every `INTERVAL` seconds it pulls your latest match from the FACEIT API
(level, elo, last map, K/D/A, calibration progress) and PATCHes the dynamic
fields of your Discord application profile widget.

No secrets live in the code. Everything is read from environment variables.

## Requirements

- Python 3.9+
- `httpx` (`pip install httpx`)

## Configuration

All values come from environment variables. The script refuses to start if any
required one is missing.

| Variable | Required | What it is |
|----------|----------|------------|
| `FACEIT_API_KEY` | yes | FACEIT server-side API key |
| `FACEIT_NICKNAME` | yes | Your FACEIT nickname (used for lookups and as the widget username) |
| `DISCORD_BOT_TOKEN` | yes | Bot token of the Discord application that owns the widget |
| `APP_ID` | yes | Discord application ID (the app the widget belongs to) |
| `USER_ID` | yes | Your Discord user ID (the profile being updated) |
| `INTERVAL` | no | Seconds between updates, defaults to `120` |

### Where to get each value

**`FACEIT_API_KEY`**
Go to <https://developers.faceit.com>, sign in, open the API Keys section and
create a **server-side** key. Server-side, not client-side — the code sends it
as a `Bearer` token to `open.faceit.com/data/v4`.

**`FACEIT_NICKNAME`**
Your exact FACEIT nickname, the one in your profile URL. It is resolved to a
`player_id` on startup, so it has to match.

**`DISCORD_BOT_TOKEN`**
<https://discord.com/developers/applications> → your application → **Bot** →
Reset Token / Copy Token. This is the app whose profile widget you are driving.

**`APP_ID`**
Same application → **General Information** → Application ID.

**`USER_ID`**
Enable Developer Mode in Discord (Settings → Advanced → Developer Mode), then
right-click your own avatar → Copy User ID.

## Widget fields

The script writes these dynamic fields to
`PATCH /applications/{APP_ID}/users/{USER_ID}/identities/0/profile`. Your widget
template on the Discord side must expose fields with the same names, otherwise
they are ignored:

- Text (`type 1`): `map_name`, `kda`, `elo_change`, `sub_1`, `sub_2`, `sub_3`,
  `status`
- Number (`type 2`): `current`, `max` — the progress bar; these must be numbers
  or the bar will not render
- Image (`type 3`): `map_image`, `level_image`

Level icons are pulled from `evansvl/faceit-levels`, map art from
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

## Running

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
