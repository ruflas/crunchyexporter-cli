# CrunchyExporter

Fetches your Crunchyroll watch history and exports it to **AniList**, **MyAnimeList**, and a local **MAL-compatible XML** file.

## Requirements

- Python 3.11+
- A Crunchyroll account (active browser session required for auth)

## Setup

```bash
pip install -r requirements.txt
```

On Windows (PowerShell):
```powershell
Copy-Item config.example.yaml config.yaml
```

On Mac/Linux:
```bash
cp config.example.yaml config.yaml
```

---

## Step 1 — Get your Crunchyroll session cookie

CrunchyExporter authenticates using the `etp_rt` session cookie from your browser. No password is stored.

1. Open [crunchyroll.com](https://www.crunchyroll.com) and log in
2. Press `F12` to open DevTools
3. Go to **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
4. In the left panel expand **Cookies → https://www.crunchyroll.com**
5. Find the row named `etp_rt` and copy its **Value**

Then fetch your history:

```bash
python src/main.py fetch --etp-rt "paste-your-etp-rt-value-here"
```

Or save it in `config.yaml` to avoid typing it each time:

```yaml
crunchyroll:
  etp_rt: "paste-your-etp-rt-value-here"
```

```bash
python src/main.py fetch
```

On success you'll see something like:
```
Logged in. Account ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Sync complete. 1513 new episodes added. Total: 1513 episodes across 28 series.
```

History is saved to `data/history.json`. Re-running `fetch` only adds new episodes — it never duplicates.

---

## Step 2 — View your history

```bash
python src/main.py status
```

Shows a table with each series, how many episodes were watched, and the highest episode number seen.

---

## Step 3 — Export

### Option A: MAL XML (no account needed, fastest)

```bash
python src/main.py export --target xml
```

Generates `data/animelist.xml`. Import it at:
- MyAnimeList: [myanimelist.net/import.php](https://myanimelist.net/import.php)
- AniList: [anilist.co/settings/import](https://anilist.co/settings/import) → select MAL format
- Kitsu and most other tracking sites

### Option B: AniList API (recommended, most accurate)

1. Go to [anilist.co/settings/developer](https://anilist.co/settings/developer) and click **Create new client**
2. Fill in any name and set **Redirect URL** to exactly: `https://anilist.co/api/v2/oauth/pin`
3. Copy the **Client ID** and add it to `config.yaml`:

```yaml
exporters:
  anilist:
    client_id: "123456"
    access_token: ""
```

4. Run the export — it will print an authorization URL:

```bash
python src/main.py export --target anilist
```

5. Open the URL, authorize the app, and copy the `access_token` from the redirect URL
6. Paste it into `config.yaml`:

```yaml
exporters:
  anilist:
    client_id: "123456"
    access_token: "eyJ..."
```

7. Run the export again — from now on it will update directly without asking for the URL

### Option C: MyAnimeList API

1. Go to [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig) and create a new app
2. Set the redirect URI to `http://localhost`
3. Add your `client_id` to `config.yaml`:

```yaml
exporters:
  mal:
    client_id: "your_mal_client_id"
    access_token: ""
```

4. Run the export — it will walk you through the OAuth flow automatically:

```bash
python src/main.py export --target mal
```

5. Open the printed URL, authorize, paste the code back into the terminal
6. Save the resulting `access_token` in `config.yaml` to skip the flow next time

### Export all targets at once

```bash
python src/main.py export
```

---

## Config reference

```yaml
locale: "en-US"           # Language for series titles from CR

storage:
  path: "data/history.json"

crunchyroll:
  etp_rt: ""              # Session cookie from browser (see Step 1)
  client_id: ""           # Leave blank to use built-in default
  client_secret: ""       # Leave blank (public client, no secret)

exporters:
  mal_xml:
    path: "data/animelist.xml"

  anilist:
    client_id: ""
    access_token: ""

  mal:
    client_id: ""
    access_token: ""
```

---

## Troubleshooting

**`Login failed (400): unsupported_grant_type`**
CR no longer supports email/password login via the API. Use the `etp_rt` cookie method described in Step 1.

**`Login failed (400): missing_required_field`**
The `etp_rt` value is missing or empty. Make sure you copied the full cookie value.

**`Login failed (400): invalid_client` on AniList**
The `client_id` in `config.yaml` is missing or wrong. Create the app at [anilist.co/settings/developer](https://anilist.co/settings/developer) and make sure the redirect URL is exactly `https://anilist.co/api/v2/oauth/pin`.

**History fetch returns 403**
The content API base URL must be `beta-api.crunchyroll.com`, not `www.crunchyroll.com`. This is already correct in the current code.

**History fetch returns `invalid_value` on `page` field**
Pagination starts at page 1, not 0. This is already fixed in the current code.

**Some series not found on AniList/MAL**
Crunchyroll uses different titles than AniList/MAL for some series. The exporter automatically tries a normalized version of the title as a fallback. If a series still fails, check the exact title used on AniList/MAL and create a manual entry.

**`etp_rt` stops working after a few days**
The cookie expires with your browser session. Log into Crunchyroll again and repeat Step 1 to get a fresh value.

---

## Project structure

```
CrunchyExporter/
├── src/
│   ├── crunchyroll/
│   │   ├── auth.py              # CR authentication (etp_rt_cookie grant)
│   │   ├── history.py           # Watch history fetcher (paginated)
│   │   └── models.py            # Data classes
│   ├── exporters/
│   │   ├── anilist.py           # AniList GraphQL exporter
│   │   ├── mal.py               # MyAnimeList REST exporter
│   │   └── mal_xml.py           # Local MAL XML exporter
│   ├── storage/
│   │   └── history_store.py     # JSON persistence
│   └── main.py                  # CLI (click + rich)
├── data/                        # Generated files — gitignored
├── config.example.yaml
└── requirements.txt
```
