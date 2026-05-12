<p align="center">
  <img src="crunchyexporterlogo.png" alt="CrunchyExporter" width="300"/>
</p>

<h1 align="center">CrunchyExporter</h1>

<p align="center">Fetches your Crunchyroll watch history and exports it to <b>AniList</b>, <b>MyAnimeList</b>, and a local <b>MAL-compatible XML</b> file.</p>

Exports include watch progress, series status (watching/completed), and real start/finish dates from your Crunchyroll history.

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

CrunchyExporter authenticates using the `etp_rt` session cookie from your browser. No password is stored or required.

1. Open [crunchyroll.com](https://www.crunchyroll.com) and log in
2. Press `F12` to open DevTools
3. Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
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

> **Note:** The `etp_rt` cookie expires when your browser session ends. If `fetch` starts failing with a 401 error, just grab a fresh cookie from DevTools.

---

## Step 2 — View your history

```bash
python src/main.py status
```

Shows a table with each series, number of episodes watched, and the highest episode number.

---

## Step 3 — Export

### Option A: MAL XML (no account needed, fastest)

```bash
python src/main.py export --target xml
```

Generates `data/animelist.xml`. Import it at:
- MyAnimeList: [myanimelist.net/import.php](https://myanimelist.net/import.php)
- AniList: [anilist.co/settings/import](https://anilist.co/settings/import) — select MAL format
- Kitsu and most other tracking sites

> **Note:** The XML does not include MAL IDs (Crunchyroll doesn't provide them). MAL and AniList resolve entries by title on import.

---

### Option B: AniList API

Syncs progress, status and real completion dates directly via the AniList API.

**1. Create an API client**
- Go to [anilist.co/settings/developer](https://anilist.co/settings/developer)
- Click **Create new client**
- Set **Redirect URL** to exactly: `https://anilist.co/api/v2/oauth/pin`
- Copy the **Client ID**

**2. Add it to `config.yaml`**
```yaml
exporters:
  anilist:
    client_id: "123456"
    access_token: ""
```

**3. Run the export**
```bash
python src/main.py export --target anilist
```

The script prints an authorization URL. Open it, click **Authorize**, and AniList will redirect you to a page showing your `access_token`. Copy it.

**4. Save the token**
```yaml
exporters:
  anilist:
    client_id: "123456"
    access_token: "eyJ..."
```

From now on the export runs without any browser interaction.

---

### Option C: MyAnimeList API

Syncs progress, status, start date and finish date directly via the MAL API.

**1. Create an API client**
- Go to [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig)
- Click **Create ID**
- Fill in the required fields:
  - **App Type**: `web` — required for OAuth. This also gives you a Client Secret.
  - **App Redirect URL**: `http://localhost`
  - **Purpose of Use**: `hobbyist`
- Submit and copy both the **Client ID** and **Client Secret**

**2. Add them to `config.yaml`**
```yaml
exporters:
  mal:
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    access_token: ""
```

**3. Run the export**
```bash
python src/main.py export --target mal
```

The script prints an authorization URL. Open it and click **Allow**. MAL will redirect you to `http://localhost/?code=XXXX` — the page won't load, that's expected. Copy the `code=` value from the browser's address bar and paste it into the terminal.

**4. Save the token**

The script will display the obtained `access_token`. Add it to `config.yaml`:
```yaml
exporters:
  mal:
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    access_token: "the_token_shown_in_terminal"
```

From now on the export runs without any browser interaction.

---

### Export all targets at once

```bash
python src/main.py export
```

---

## Step 4 — Auto-sync (optional)

### One-shot: fetch + export in a single command

```bash
python src/main.py sync                      # fetch + export all targets
python src/main.py sync --target anilist     # fetch + export AniList only
```

Requires `etp_rt` set in `config.yaml` (no interactive prompts).

### Schedule a daily background task

```bash
# Register a daily task at 08:00 (default)
python src/main.py schedule

# Choose a different time
python src/main.py schedule --time 20:00

# Only sync to a specific target
python src/main.py schedule --target anilist --time 09:00

# Remove the scheduled task
python src/main.py schedule --remove
```

On **Windows** this creates a Windows Task Scheduler entry (`schtasks`).  
On **Linux/Mac** it adds an entry to your crontab.

Verify it was created (Windows):
```powershell
schtasks /Query /TN CrunchyExporter
```

Run it manually to test:
```powershell
schtasks /Run /TN CrunchyExporter
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
  client_secret: ""       # Leave blank (public client, no secret needed)

exporters:
  mal_xml:
    path: "data/animelist.xml"

  anilist:
    client_id: ""
    access_token: ""

  mal:
    client_id: ""
    client_secret: ""     # Required for web app type
    access_token: ""
```

---

## Troubleshooting

**`Login failed (400): unsupported_grant_type`**
CR no longer supports email/password login via the API. Use the `etp_rt` cookie method described in Step 1.

**`Login failed (400): missing_required_field`**
The `etp_rt` value is missing or empty. Make sure you copied the full cookie value from DevTools.

**`fetch` returns 401 after working before**
The `etp_rt` cookie expired. Log into Crunchyroll again and copy a fresh value from DevTools.

**`invalid_client` error on AniList**
The `client_id` in `config.yaml` is wrong, or the redirect URL in your AniList app is not exactly `https://anilist.co/api/v2/oauth/pin`.

**MAL authorization page shows 400 Bad Request**
Your MAL app type is set to `other`. Change it to `web` in [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig) — only `web` type supports OAuth authorization code flow.

**MAL token exchange fails with `Failed to verify code_verifier`**
This is a known MAL quirk — their PKCE implementation uses the `plain` method, not S256. This is already handled correctly in the current code.

**Some series not found on AniList or MAL**
Crunchyroll sometimes uses different titles than AniList/MAL. The exporter automatically retries with a normalized title as fallback. If a series still fails, add it manually on the tracking site.

**One Piece or other long-running series matched to a movie**
The exporter prefers TV/ONA/OVA results over movies when searching. If a wrong match still occurs, correct it manually on the tracking site.

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

---

## Contributing

Contributions are welcome. Here's how to get started:

**1. Fork the repo and clone it**
```bash
git clone https://github.com/your-username/CrunchyExporter.git
cd CrunchyExporter
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

**2. Make your changes**

The codebase is straightforward — each exporter lives in `src/exporters/`, CR auth and history fetching in `src/crunchyroll/`, and the CLI commands in `src/main.py`.

**3. Test manually**
```bash
python src/main.py fetch
python src/main.py status
python src/main.py export --target xml
```

**4. Open a pull request** with a clear description of what you changed and why.

### Good areas to contribute

- **New exporters** — Kitsu, Anime-Planet, Shikimori
- **Better title matching** — fuzzy search or manual override mappings
- **Movie detection** — improve handling of films vs series
- **Bug reports** — if a series fails to match or exports incorrectly, open an issue with the series title and the error

### Please avoid

- Breaking the existing CLI interface without discussion
- Adding dependencies that aren't strictly necessary
