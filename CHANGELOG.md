# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-12

### Added
- Fetch Crunchyroll watch history via `etp_rt` browser session cookie
- Incremental local JSON cache — re-runs only add new episodes
- Export to **AniList** via GraphQL API with OAuth token
- Export to **MyAnimeList** via REST API with OAuth PKCE flow
- Export to local **MAL-compatible XML** (importable on MAL, AniList, Kitsu)
- Real start and finish dates sent to AniList and MAL from CR history
- Automatic series status: `Completed` when max episode >= total, `Watching` otherwise
- Movie support: entries with no episode number exported as 1 completed episode
- Title normalization fallback for series with different names across platforms
- TV/ONA/OVA preferred over movies when multiple search results match
- `sync` command: fetch + export in one unattended step
- `schedule` command: registers a daily task in Windows Task Scheduler or crontab
- `-h` / `--help` on all commands with usage examples
- `status` command: table view of all series, episode counts and last sync time
