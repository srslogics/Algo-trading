# PeopleOS — Render deployment folder

This folder contains the complete recruitment and HR demo, including the login screen and all workspace pages. It is a static website. No database, server, API keys or environment variables are required.

## Deploy on Render

1. Use the existing GitHub repository: https://github.com/srslogics/Algo-trading. The demo is in `peopleos-render/`.
2. In Render, select **New → Static Site**, then connect that repository.
3. Use these settings:

| Setting | Value |
| --- | --- |
| Service type | Static Site |
| Root Directory | `peopleos-render` |
| Build Command | `npm run build` |
| Publish Directory | `public` |
| Environment variables | None |

These settings serve only the PeopleOS folder. The separate trading application at the repository root does not need any changes.

Click **Deploy Static Site**. Render deploys from the connected Git repository; this ZIP is a convenient way to move the files, not a direct Render upload.

The optional Blueprint file is `peopleos-render/render.yaml`; select that path if using Blueprints. Normal Static Site creation is sufficient. Do not use the repository-root Blueprint for this demo, because that belongs to the trading application.

## Demo login

Choose **Use demo credentials**, then **Sign in**.

- Email: `aarav@northstar.example`
- Password: `PeopleOS2026`

Login is a browser-only demo flow, not production authentication. All candidates and company details are fictional. AI, WhatsApp and hiring communications are simulated. Demo records reset on refresh; sign-in is remembered for the browser session when storage is available. Never put real employee data or secrets into this static demo.

## Files

- `public/index.html` — login and workspace shell
- `public/styles.css` — desktop and mobile design
- `public/app.js` — interactive workflows and demo login
- `public/data.js` — fictional demo records
- `package.json` — build check and local preview
- `render.yaml` — optional Render Blueprint

## Local preview

Run `npm start`, then open http://127.0.0.1:8100. Python 3 is required only for this local preview. Run `npm run build` to check JavaScript syntax. No dependency installation is needed.

Render documentation: https://render.com/docs/static-sites

## Link preview

The page includes public Open Graph metadata and a 1200 × 630 JPEG preview at `public/peopleos-share-v1.jpg`. Its absolute image URL targets the deployed Render domain. Update the canonical and sharing URLs in `public/index.html` if that domain changes. The editable source is `design/share-card.svg`.
