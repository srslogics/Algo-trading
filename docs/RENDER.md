# Deploy OptionLab on Render

The repository contains a Render Blueprint in `render.yaml`. It creates a Docker web service and a persistent PostgreSQL database in Singapore. This is a private, single-operator paper trading workspace. Broker execution remains disabled in code.

## Deploy the repository

1. Put the **contents of the `optionlab` folder** in your GitHub or GitLab repository. `render.yaml`, `Dockerfile`, and `pyproject.toml` should be at the repository root. Do not upload `.env`, `optionlab.db`, `.venv`, or `node_modules`.
2. In Render, choose **New → Blueprint**, connect that repository, and select its branch. Review the two resources and their displayed prices before creating them. The supplied web and database plans are paid plans; no deployment or subscription has been created for you.
3. Deploy the Blueprint. Render builds the Docker image, runs `alembic upgrade head` as the pre-deploy command, then starts the application. The health check is `/healthz`.
4. Open the web service's **Environment** settings and retrieve the generated `OPTIONLAB_API_TOKEN`. Keep it private. Open the service's HTTPS URL and enter this key in the OptionLab sign-in screen.
5. Select **Update sample market → Update sample market**, then **New proposal → Review paper order**. Confirm only a paper order. Check Portfolio and Activity to verify the stored records.
6. Redeploy once and verify the same paper balance, orders, and saved backtest remain. They live in PostgreSQL, independently of the web container.

Render's [Blueprint reference](https://render.com/docs/blueprint-spec) defines the resource, plan, migration, and database-link fields used here. The file was checked against its published JSON schema. Current plan identifiers in the Blueprint are `0.5c-512mb` for the web service and `0.1c-256mb` for PostgreSQL, with 5 GB of database storage.

## What is already configured

| Setting | Behavior |
| --- | --- |
| Start | `python -m optionlab.server`; binds `0.0.0.0` and the supplied `PORT` |
| Database | Internal connection string from the Blueprint database; PostgreSQL driver URL normalized automatically |
| Persistence | All trading records, audit, advisory questions/responses, and replay datasets stored in PostgreSQL |
| Migrations | Pre-deploy Alembic upgrade; a failure stops the new deployment |
| Authentication | Required on Render; generated operator access key; signed HttpOnly, Secure, SameSite=Strict session cookie |
| Session lifetime | Eight hours by default; adjustable with `OPTIONLAB_SESSION_HOURS` (1–24) |
| HTTPS / origin | Canonical `RENDER_EXTERNAL_URL`; same-origin mutation checks, HSTS, explicit host check |
| Scaling | One web instance and one API worker; exit monitor runs within that process |
| Data / AI | Fictional sample data and offline advisory summaries by default |
| Live trading | No live order route or enablement switch |

The start command follows Render's [FastAPI deployment guidance](https://render.com/docs/deploy-fastapi). `PORT` and `RENDER_EXTERNAL_URL` are supplied by Render's [runtime environment](https://render.com/docs/environment-variables). Do not set a localhost public origin on Render.

## Custom domain

After configuring your domain and HTTPS in Render, set `OPTIONLAB_PUBLIC_ORIGIN=https://your-domain.example` using the actual domain, without a path. Redeploy and use that address. The canonical host/origin check then rejects the former `onrender.com` address for application requests; `/healthz` remains reachable for Render's internal health checker. Changing the origin requires signing in again on the new domain.

## Access key and sessions

Use the generated key in the sign-in screen. The browser keeps only a signed session cookie; it does not write the key to localStorage or sessionStorage. API clients can use `Authorization: Bearer <key>`. Browser mutations require the matching Origin header. Login attempts are limited to 20 per minute per running process.

Sign out removes this browser's cookie. Rotating `OPTIONLAB_API_TOKEN` in Render invalidates all existing sessions and API clients after the service restarts. The token authenticates one trusted operator, not separate customers. User accounts, account isolation, OIDC, and distributed rate limiting remain separate work.

## Data feed and runtime limits

The demo does not produce ticks automatically. Its prices become stale after 60 seconds. Refresh sample prices when practicing. Render restarts preserve database records, but there is no monitoring while the process is stopped. The initial plans are intended for a small private workspace, not an unmeasured multi-user workload.

For Kite data, use a separate database/workspace, turn demo off, configure read-only credentials in Render's environment, and run the collector as a separately managed worker. That worker and broker login lifecycle are not provisioned by this default Blueprint. Optional model credentials also belong in Render's environment; do not commit them.

## Troubleshooting

- **Missing tables:** Confirm the pre-deploy command is `alembic upgrade head` and succeeded against the same database used by the service.
- **SQLite / authentication startup error:** Use the Blueprint database link and `OPTIONLAB_ENVIRONMENT=render`, `OPTIONLAB_AUTH_REQUIRED=true`. Remove any SQLite `OPTIONLAB_DATABASE_URL` override.
- **Origin or host rejected:** Match `OPTIONLAB_PUBLIC_ORIGIN` to the exact HTTPS browser origin, or remove an unnecessary override to use `RENDER_EXTERNAL_URL`.
- **Login rejected:** Retrieve the current generated key from Render. Do not use a sample/test key from automated tests.
- **502 / failed health check:** Inspect service logs for startup or migration errors. The server reads `PORT` and requires a reachable database.
- **Blank account on first hosted launch:** This is a new PostgreSQL paper account. The local SQLite demo database is not copied automatically.

Before retaining important research records, enable an appropriate database backup policy and exercise a restore. A backup process is not configured by this Blueprint.

## Verification scope

Local Python and frontend helper tests, paper execution browser flows, secure-cookie/proxy/origin tests, and Blueprint schema validation are included. PostgreSQL verification also has a dedicated CI job. No Render service has been deployed, and the Docker/PostgreSQL runtime could not be exercised on this computer because its Docker daemon is unavailable. Check the CI result and Render deployment logs before treating the hosted installation as verified.
