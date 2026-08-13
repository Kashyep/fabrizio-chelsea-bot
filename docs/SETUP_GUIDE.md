# Fabrizio Chelsea Bot

## Complete setup, deployment, operations, and troubleshooting guide

**Version 1.0 - August 2026**
**Repository:** `Kashyep/fabrizio-chelsea-bot`
**Purpose:** Watch Fabrizio Romano's public X timeline and natively repost only posts that mention
Chelsea.

---

## Read this first

This bot uses the official X API v2. It does not scrape X and it does not copy or rewrite Fabrizio
Romano's content. When a source post matches the configured Chelsea terms, the bot performs a native
repost. The original author, text, media, and link remain attached to the original post.

The software is deliberately safe on first use:

- dry-run is the default;
- the first live run records the newest post as a baseline and creates no reposts;
- only newer posts are considered on later runs;
- a persistent checkpoint prevents duplicate processing;
- at most five matches are reposted in one run unless you change the limit;
- the included GitHub Actions schedule stays disabled until `BOT_ENABLED=true`.

You still need to provide X API credentials and decide where the bot will run. X API access is
pay-per-usage, so review the current price shown in your Developer Console before enabling a
schedule. API products, prices, limits, and screens can change.

### What "mentions Chelsea" means

By default, any case-insensitive occurrence of one of these boundary-aware terms matches:

```text
chelsea
chelsea fc
chelseafc
@chelseafc
#chelseafc
```

This includes ordinary text, hashtags, and account mentions. The match is intentionally literal and
transparent; no AI classifier guesses whether a post is about Chelsea. Replies authored by Fabrizio
are included, while Fabrizio's own native reposts are excluded.

### Why the bot uses reposts

X's current Create Post API documentation says `quote_tweet_id` creation requires an Enterprise
plan. The official repost endpoint supports user-context authorization and provides the closest,
most faithful implementation of the request on self-serve API access. Native reposting also avoids
copying someone else's text and preserves media and attribution.

---

## 1. Architecture at a glance

Each run is a short transaction:

```text
X public API
  | resolve @FabrizioRomano and fetch posts newer than since_id
  v
Chelsea matcher
  | non-match ----------------------> record ignored + checkpoint
  | match
  v
X repost endpoint (OAuth 1.0a user context)
  | confirmed response
  v
record reposted + checkpoint in SQLite
```

The read side uses the App Bearer Token. The write side uses the API key/secret plus the bot
account's access token/secret. State is stored in `data/state.db`. The database contains:

- the latest handled source post ID;
- resolved source and bot user IDs;
- an audit row for each observed post: ID, timestamps, SHA-256 text hash, whether it matched, and the
  action taken.

Full source text and credentials are never stored in the database. Logs contain source post IDs and
outcomes, not credentials or full post text.

### Processing guarantees

Posts are sorted by numeric ID and handled oldest first. For a non-match, state advances after the
ignore decision. For a match, the repost API must confirm success before state advances. If a run
fails, newer unhandled posts remain eligible on the next run. A process lock and deployment
concurrency control block overlapping cycles.

If a repost succeeds but the process is terminated before SQLite commits, the next run may ask X to
repost the same post again. The account should still have a single native repost, but this is why
the bot saves state after every item and why an always-on host with a persistent volume is the most
durable deployment.

---

## 2. Accounts and prerequisites

You need:

1. an X account that will act as the bot;
2. access to the X Developer Console at `https://console.x.com`;
3. an X developer App with Read and write permission;
4. prepaid X API credits if required for the endpoints at the time you deploy;
5. one runtime option:
   - GitHub account and repository for the included scheduled workflow, or
   - an always-on computer/server with Python 3.11+, or
   - Docker Engine with Docker Compose.

Recommended account hygiene:

- use a dedicated public X bot account, not your personal account;
- make its profile explain that it automatically reposts Chelsea news from Fabrizio Romano;
- enable strong login security on the account;
- do not share developer credentials in chat, screenshots, issues, commits, or logs;
- keep the project independent and do not imply affiliation with Fabrizio Romano or Chelsea FC.

This code cannot create an X developer account, accept the Developer Agreement, purchase API
credits, or generate your user credentials for you. Those steps require your own account and consent.

---

## 3. Create and configure the X developer App

Screens can move, but the underlying requirements are stable.

### Step 3.1 - Open the Developer Console

1. Sign in to the bot's X account in your browser.
2. Open `https://console.x.com`.
3. Accept the developer terms and complete any requested use-case information.
4. Create a Project/App, or select an existing App dedicated to this bot.
5. Add API credits and a spending limit appropriate to your polling interval.

Describe the use case accurately: the app reads one public user's timeline, filters posts for Chelsea
terms, and reposts matches from the authenticated bot account.

### Step 3.2 - Set user authentication permissions

In the App's user authentication/settings area:

1. enable OAuth 1.0a user context if the Console offers an authentication choice;
2. select **Read and write** App permissions;
3. save the change;
4. if a callback/website field is mandatory for a single-account bot, use a legitimate URL you
   control. The runtime uses pre-generated user tokens and does not run an interactive callback.

Critical: if you change permissions from Read to Read and write, regenerate the Access Token and
Access Token Secret afterward. Tokens created before the permission change may remain read-only.

### Step 3.3 - Generate and store five credentials

Open the App's keys/tokens screen and securely copy:

| Environment variable | Console credential | Used for |
| --- | --- | --- |
| `X_BEARER_TOKEN` | Bearer Token | public user lookup and timeline reads |
| `X_API_KEY` | API Key / Consumer Key | OAuth 1.0a write signing |
| `X_API_SECRET` | API Secret / Consumer Secret | OAuth 1.0a write signing |
| `X_ACCESS_TOKEN` | Access Token for bot user | identifies the posting account |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret | OAuth 1.0a write signing |

Store them in a password manager. X may display some credentials only once. If one is lost, regenerate
it and update every deployment. Regeneration invalidates the old value.

Never use a plain App Bearer Token as `X_ACCESS_TOKEN`; the credentials have different purposes.

---

## 4. Local installation

These instructions let you verify configuration before enabling unattended posting.

### Step 4.1 - Get the repository

```bash
git clone https://github.com/Kashyep/fabrizio-chelsea-bot.git
cd fabrizio-chelsea-bot
```

### Step 4.2 - Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If PowerShell blocks activation for the current process:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Step 4.3 - Create `.env`

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
chmod 600 .env
```

Open `.env` in a text editor and replace only the five `replace_me` values. Do not add quote marks
unless the secret itself contains them. Leave these safety defaults initially:

```dotenv
DRY_RUN=true
BOOTSTRAP_MODE=baseline
MAX_REPOSTS_PER_RUN=5
```

The repository's `.gitignore` excludes `.env`, but always check `git status` before committing.

---

## 5. Validate without posting

### Step 5.1 - Run the credential doctor

```bash
chelsea-bot doctor
```

Expected shape:

```json
{
  "bot_user_id": "123456789",
  "result": "credentials and user lookups succeeded",
  "source_user_id": "987654321",
  "source_username": "FabrizioRomano"
}
```

`doctor` performs both bearer-token and user-context lookups. It never reposts. Confirm the bot user
ID belongs to the intended bot account. If it belongs to your personal account, stop and regenerate
the Access Token/Secret while authenticated as the bot.

### Step 5.2 - Preview the source timeline

```bash
chelsea-bot run --dry-run
```

On an empty state database with baseline mode, the result reports `bootstrapped: true`, but dry-run
does not write the baseline. Logs show the newest ID it would use. No X write occurs and no state is
advanced.

### Step 5.3 - Establish the live baseline

```bash
chelsea-bot run --live
```

The first live run writes the newest visible Fabrizio post ID to SQLite and performs zero reposts.
This is intentional. Check:

```bash
chelsea-bot status
```

You should see a non-null `last_seen_id`. From now on, a live run asks X only for posts newer than
that ID.

### Step 5.4 - Test normal operation

Run again later:

```bash
chelsea-bot run --live
```

The JSON summary reports fetched, matched, reposted, and ignored counts. If no new post exists, all
counts are zero. That is normal.

Do not delete `data/state.db` casually. An empty database makes the next baseline run treat the
current newest source post as the new starting point. Back up the file before moving deployments.

---

## 6. Configure matching behavior

The default terms cover common English renderings. To customize them, edit `CHELSEA_TERMS` in `.env`
or the deployment environment:

```dotenv
CHELSEA_TERMS=chelsea,chelsea fc,chelseafc,@chelseafc,#chelseafc,the blues
```

Rules:

- separate terms with commas;
- matching is Unicode-normalized and case-insensitive;
- each term is literal, not a regular expression;
- word-character boundaries are enforced on both ends;
- punctuation such as `#` and `@` is allowed;
- at least one non-empty term is required.

Test any change locally with `--dry-run`. Broad terms such as `blues` can produce false positives.
The simplest reliable policy is to keep the default explicit Chelsea names.

`SOURCE_USERNAME` is configurable for testing, but the intended value is `FabrizioRomano`. The bot
resolves the handle to a stable numeric ID and caches it in state. If you intentionally change the
source, use a separate state database or delete only the cached state after stopping the bot.

---

## 7. Deploy with GitHub Actions

This is the easiest no-server deployment. Scheduled workflows can be delayed during load, and cache
storage is less durable than a real database volume. Use Docker on an always-on host if exact timing
and state durability matter.

The included workflow is `.github/workflows/bot.yml`. It:

- runs at minutes 7, 17, 27, 37, 47, and 57 of every hour (UTC);
- can also be started manually;
- allows only one bot job at a time;
- installs the package;
- restores the newest state cache;
- performs one live cycle;
- saves SQLite state even when a later part of the cycle fails;
- has read-only repository permissions;
- remains scheduled-off until `BOT_ENABLED` is `true`.

### Step 7.1 - Add Actions secrets

In GitHub, open the repository, then:

`Settings -> Secrets and variables -> Actions -> Secrets -> New repository secret`

Create exactly these five repository secrets:

```text
X_BEARER_TOKEN
X_API_KEY
X_API_SECRET
X_ACCESS_TOKEN
X_ACCESS_TOKEN_SECRET
```

Paste one credential into each. Secrets are encrypted and are passed only to the run step that names
them. Do not create them as repository variables; variables are not intended for secrets.

CLI alternative, entered interactively one at a time:

```bash
gh secret set X_BEARER_TOKEN
gh secret set X_API_KEY
gh secret set X_API_SECRET
gh secret set X_ACCESS_TOKEN
gh secret set X_ACCESS_TOKEN_SECRET
```

### Step 7.2 - Establish the GitHub baseline manually

1. Open the repository's **Actions** tab.
2. Select **Chelsea repost bot**.
3. Click **Run workflow** on the default branch.
4. Open the run log and confirm it says the baseline was established and zero posts were reposted.
5. Confirm the **Save bot checkpoint** step completed.

Manual dispatch is allowed even while `BOT_ENABLED` is absent, which makes initial verification
possible without activating the schedule.

### Step 7.3 - Enable the schedule

Go to:

`Settings -> Secrets and variables -> Actions -> Variables -> New repository variable`

Create:

```text
Name: BOT_ENABLED
Value: true
```

Only the exact lowercase string `true` activates scheduled jobs. To pause the bot without editing
code, change the value to `false` or delete the variable. A manually dispatched run still runs, so do
not click it while you intend a full pause.

### Step 7.4 - Monitor Actions

Review the Actions page after enabling. A successful quiet run can legitimately report all zeros.
Look for:

- missing-secret errors;
- HTTP 401 or 403 authentication errors;
- HTTP 402/429 billing or rate-limit errors;
- failed state-cache restore/save steps;
- repeated repost-limit warnings.

GitHub documents that scheduled jobs can be delayed or dropped during heavy load, especially at the
top of an hour. The schedule deliberately uses off-peak minute offsets. It is still polling, not a
real-time stream.

### GitHub state-cache limitations

Each successful run saves a new uniquely keyed cache; the next run restores the most recent key by
prefix. State caches are not a transactional database service and can be evicted. Never store secrets
in a cache. This project stores only IDs, hashes, timestamps, and outcomes.

If the cache disappears, the next run begins with an empty database and baseline mode safely skips
history. It may therefore miss posts between the lost checkpoint and the new baseline, but it will
not replay the visible history automatically. For stronger recovery guarantees, deploy with Docker
and back up the volume.

---

## 8. Deploy with Docker Compose

Docker is the recommended long-running option for a VPS, NAS, home server, or cloud VM.

### Step 8.1 - Prepare and verify

Install current Docker Engine/Desktop with Compose. In the repository directory, create `.env`, fill
credentials, and first validate locally or in a one-off container:

```bash
docker compose run --rm bot doctor
docker compose run --rm bot run --dry-run
docker compose run --rm bot run --live
```

The last command establishes the baseline in the named volume.

### Step 8.2 - Start the daemon

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f bot
```

The container runs as an unprivileged user and polls every 300 seconds. The named volume
`chelsea_bot_state` is mounted at `/app/data` and survives container replacement.

### Step 8.3 - Operate the deployment

```bash
# Show status using the same volume
docker compose exec bot chelsea-bot status

# Restart
docker compose restart bot

# Pull code changes and rebuild
git pull
docker compose up -d --build

# Stop while preserving state
docker compose down
```

Do not run `docker compose down -v` unless you intend to erase the named state volume. Before host
migration, stop the container and back up the volume or copy `/app/data/state.db` to a protected
location.

### Backup example

The safest simple procedure is to stop the service, copy the database out, then restart:

```bash
docker compose stop bot
docker compose run --rm --entrypoint sh bot -c "cp /app/data/state.db /app/data/state.backup.db"
docker compose start bot
```

Then copy the backup from the named volume using your Docker host's approved volume-backup method.
Do not put a state backup in a public repository.

---

## 9. Run directly as a daemon

On an always-on host without Docker:

```bash
chelsea-bot daemon --live --interval 300
```

The minimum interval is 60 seconds. A shorter poll interval usually costs more and does not guarantee
instant delivery. Use a service manager so the process restarts after reboots:

- Linux: systemd with a dedicated unprivileged user and an `EnvironmentFile` outside the repository;
- macOS: launchd;
- Windows: Task Scheduler running `chelsea-bot run --live` periodically, or a managed service wrapper.

Keep only one scheduler active for a given X account and state database. Do not simultaneously run
GitHub Actions, Docker, and a local daemon with separate state: they can all attempt the same actions.

---

## 10. Dry-run, baseline, and history replay

These controls deserve special attention.

### Dry-run

`chelsea-bot run --dry-run` performs reads and filtering but never calls the repost endpoint and never
advances state. It is safe for previews, though API read charges can still apply.

`DRY_RUN=true` is the environment default. The explicit CLI flags override it:

- `--dry-run` always disables writes;
- `--live` always enables writes and requires all OAuth credentials.

### Baseline (default)

With an empty state database, the first live baseline run finds the newest visible source post and
records that ID without processing the retrieved history. This prevents a new account from suddenly
reposting dozens of older Chelsea posts.

### History replay (opt-in)

To process the recent visible timeline on an empty state database:

```bash
chelsea-bot run --live --bootstrap-history
```

Or set `BOOTSTRAP_MODE=replay`. Use this only when you intentionally want older matches. The
`MAX_REPOSTS_PER_RUN` cap stops after the configured number, leaving the next post unprocessed so a
later run can continue. Replaying can create rapid activity and incur additional API charges.

Never switch to replay merely to fix an authentication problem. Fix credentials, preserve state, and
run normally.

---

## 11. Cost planning and rate limits

As of this guide's research date, X documents credit-based pay-per-use pricing, per-resource read
charges, per-request action charges, and 24-hour deduplication for the same resource. Exact endpoint
eligibility and prices may change and the Developer Console is authoritative for your App.

Estimate cost before enabling:

```text
monthly read cost ~= unique source posts returned x current Post Read price
monthly action cost ~= Chelsea matches reposted x current interaction/action price
```

Polling requests that return zero posts may still be subject to the endpoint's current pricing rules.
The bot uses `since_id`, so after a baseline X should return only newer source posts. Increasing poll
frequency improves detection latency but does not create new source posts and may increase request or
infrastructure usage.

At a 10-minute interval, the schedule attempts 144 polls/day. At five minutes, it attempts 288/day.
Start at 10 minutes, monitor the Console's usage dashboard, and set a budget you are comfortable with.

On HTTP 429, the bot reports the rate-limit reset header when available. GET calls retry a small number
of transient 429/5xx errors with backoff. Write calls are intentionally not blindly retried because an
ambiguous network failure could follow a successful action. A later polling run recovers safely.

---

## 12. Troubleshooting

### `X_BEARER_TOKEN is required`

The `.env` file was not found, the variable is empty, or the deployment secret was not passed. Confirm
you are running from the project directory and the variable name is exact.

### HTTP 401 Unauthorized

Likely causes:

- a copied credential is incomplete or has leading/trailing text;
- the key/token was regenerated but deployment still has the old value;
- an App bearer token was placed in a user-token field;
- OAuth credentials do not all belong to the same developer App.

Regenerate deliberately, update all five values, and rerun `doctor`.

### HTTP 403 Forbidden

Likely causes:

- App permission is Read instead of Read and write;
- user access token was generated before the permission change;
- the endpoint is unavailable to the App's current access/product;
- the authenticated account cannot repost that source post;
- the account or App has a policy restriction.

Set Read and write, save, regenerate Access Token/Secret, update the deployment, and rerun `doctor`.

### HTTP 402 or a credit/billing error

Open the X Developer Console, confirm product access and available credits, and review current endpoint
pricing. The bot cannot bypass a billing gate.

### HTTP 429 Too Many Requests

Reduce poll frequency and allow the rate-limit window to reset. Check for duplicate deployments. One
GitHub workflow plus one Docker daemon doubles polling.

### `Another bot process is using ...lock`

Another process is active, or a previous process is still shutting down. Confirm process/container
status. A lock file existing on disk is not by itself a problem; the operating system lock is what
matters. Do not delete state while another process runs.

### First live run reposted nothing

Expected: it established the safe baseline. Run `chelsea-bot status`, then leave the scheduler active
for future posts.

### New Chelsea post was not reposted

Check, in order:

1. Was the source post authored by the configured source account?
2. Does it literally contain a configured term? Inspect punctuation and spelling.
3. Did a scheduled workflow actually run after the source post?
4. Did the log show an authentication, billing, or rate-limit error?
5. Did the per-run repost cap stop the cycle?
6. Are two deployments using conflicting state?
7. Does `chelsea-bot status` show a checkpoint newer than the post? If so, review whether matching
   terms changed after it was processed.

Changing match terms does not retroactively revisit posts older than the checkpoint.

### GitHub scheduled job did not run

Confirm `BOT_ENABLED` is exactly `true`, the workflow file is on the default branch, Actions are
enabled, and the schedule is not temporarily delayed. Run the workflow manually to distinguish a
schedule issue from a bot issue. GitHub may disable scheduled workflows after prolonged inactivity
in some repository situations; review the Actions UI.

### State cache was lost

Run the workflow manually. Baseline mode will create a new safe checkpoint without replaying history.
Accept that posts between checkpoints may be missed, or restore a known-good database to an always-on
deployment. Do not enable replay unless you intentionally want visible recent history processed.

### Docker container restarts repeatedly

Run `docker compose logs bot`. Common causes are missing `.env`, invalid booleans, unreadable state
volume, or unavailable network/DNS. Confirm the volume is writable by container UID/GID 10001.

---

## 13. Security and privacy checklist

Before production:

- [ ] dedicated bot account is authenticated by the access token;
- [ ] X App has only necessary Read and write permission;
- [ ] all five credentials are stored as secrets, never variables or files in Git;
- [ ] `.env`, `data/`, caches, and logs are absent from `git status`;
- [ ] GitHub workflow permissions are read-only;
- [ ] `BOT_ENABLED` was added only after a successful manual baseline run;
- [ ] one deployment is active;
- [ ] API spend and account behavior are monitored;
- [ ] state backups are protected like operational account data;
- [ ] bot profile discloses automated behavior and does not imply affiliation;
- [ ] credential rotation and incident steps are understood.

If a secret leaks, immediately pause every deployment, regenerate the affected X credentials, replace
deployment secrets, inspect X usage and account activity, and remove the secret from Git history. A
normal follow-up commit does not remove a secret from earlier commits.

The SQLite audit stores hashed text rather than full post text. A hash is still a stable derived value,
so keep state private. It is not needed in the public GitHub repository.

---

## 14. Maintenance and upgrades

### Routine weekly check

- confirm recent scheduled runs succeed;
- check X API credit usage and rate-limit events;
- inspect the bot account for correct repost selection;
- verify only one deployment is active.

### Monthly check

- review X API and automation policy changes;
- apply dependency/security updates;
- run `ruff check .` and `pytest`;
- test `doctor` after credential rotation;
- verify a state backup can be located and restored.

### Upgrade procedure

1. pause the schedule or stop the container;
2. back up `data/state.db` or the Docker volume;
3. pull the new code;
4. install/rebuild;
5. run tests and `doctor`;
6. run one live cycle manually;
7. resume the scheduler.

Do not replace a working state database with the empty `data/` directory from source control.

### Rotate credentials

1. pause the bot;
2. regenerate credentials in the X Developer Console;
3. update `.env` or all GitHub Actions secrets;
4. run `doctor`;
5. resume and monitor the next cycle.

Preserving the SQLite database during credential rotation prevents a new baseline or missed interval.

---

## 15. Development and test guide

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
ruff check .
pytest --cov=chelsea_bot --cov-report=term-missing
```

Tests use fake clients and temporary databases. They verify matching, safe configuration defaults,
baseline behavior, chronological processing, repost caps, no dry-run mutations, state hashing, and
checkpoint monotonicity. They never access X.

Key source files:

```text
src/chelsea_bot/config.py      environment parsing and validation
src/chelsea_bot/filtering.py   deterministic Chelsea matcher
src/chelsea_bot/x_api.py       X API reads, OAuth signing, errors, retries
src/chelsea_bot/state.py       SQLite checkpoint and audit
src/chelsea_bot/service.py     transaction ordering and safeguards
src/chelsea_bot/cli.py         run, daemon, doctor, status commands
```

To change behavior, add or update tests first. Never test write behavior against a personal account.
Use a dedicated protected test account and remain within X developer rules.

---

## 16. Pause, reset, migrate, or uninstall

### Pause

- GitHub: set `BOT_ENABLED=false` or delete the variable.
- Docker: `docker compose stop bot`.
- daemon: stop the service/process.

### Resume

Resume with the same state database. The next run processes posts newer than the last checkpoint,
subject to X timeline availability and configured pagination limits.

### Intentional reset

Stop all bot processes, make a backup, then remove the specific state database/volume. The next live
baseline run will skip visible history and start from the current newest post. Resetting state can
miss posts and should not be a routine fix.

### Migrate

Stop the old deployment, copy `state.db` to the new deployment's configured `STATE_PATH`, copy secrets
through a secure channel, run `status` and `doctor`, start the new deployment, then retire the old one.
Never overlap them.

### Uninstall

1. pause and remove the scheduler/container/service;
2. revoke or regenerate the X App credentials if the App will not be used;
3. delete GitHub Actions secrets;
4. optionally archive/delete the repository;
5. securely delete local `.env` and state backups when no longer needed.

Native reposts already made remain on the bot account. Remove them manually if desired; this project
does not automatically undo reposts during uninstall.

---

## 17. Final go-live checklist

1. [ ] Bot account profile is complete and transparent.
2. [ ] Developer App use case is accurate.
3. [ ] Read and write permission is enabled.
4. [ ] User tokens were regenerated after permission changes.
5. [ ] Five credentials are stored securely.
6. [ ] `chelsea-bot doctor` succeeds and bot user ID is correct.
7. [ ] `chelsea-bot run --dry-run` behaves as expected.
8. [ ] First `--live` run establishes a baseline and creates zero reposts.
9. [ ] `chelsea-bot status` shows a non-null checkpoint.
10. [ ] Only one deployment method is active.
11. [ ] State persistence is configured and understood.
12. [ ] Schedule is enabled only after manual verification.
13. [ ] Current X pricing and a spend limit were reviewed.
14. [ ] Logs and the bot account will be monitored after launch.

---

## References and current-platform notes

Official sources consulted for this guide (accessed August 13, 2026):

1. X Developer Platform overview: `https://docs.x.com/overview`
2. X Developer Console: `https://docs.x.com/fundamentals/developer-portal`
3. X User Timelines: `https://docs.x.com/x-api/posts/timelines/introduction`
4. X Get Posts by User: `https://docs.x.com/x-api/users/get-posts`
5. X User Lookup: `https://docs.x.com/x-api/users/lookup/introduction`
6. X Repost Post: `https://docs.x.com/x-api/users/repost-post`
7. X OAuth 1.0a overview: `https://docs.x.com/fundamentals/authentication/oauth-1-0a/overview`
8. X API Key and Secret: `https://docs.x.com/fundamentals/authentication/oauth-1-0a/api-key-and-secret`
9. X Create or Edit Post (Enterprise quote-post note):
   `https://docs.x.com/x-api/posts/create-post`
10. X API Pricing: `https://docs.x.com/x-api/getting-started/pricing`
11. GitHub Actions workflow syntax:
    `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax`
12. GitHub Actions secrets: `https://docs.github.com/en/actions/concepts/security/secrets`
13. GitHub Actions dependency caching reference:
    `https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching`
14. GitHub workflow troubleshooting (schedule delays):
    `https://docs.github.com/en/actions/how-tos/troubleshoot-workflows`
15. Docker Compose environment variables:
    `https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/`
16. Docker Compose volumes: `https://docs.docker.com/reference/compose-file/volumes/`

Platform documentation and pricing can change. Verify the live pages and your Developer Console at
deployment time.

---

## Disclaimer

This open-source project is independent and is not affiliated with, endorsed by, or operated by
Fabrizio Romano, Chelsea Football Club, or X. You are responsible for the bot account, API charges,
credentials, configuration, content selection, and compliance with X's current Developer Agreement,
automation rules, and applicable law.
