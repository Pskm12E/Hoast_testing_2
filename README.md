# Little Notes

A small, responsive, two-page web app for testing website hosting.

Live site: **https://notebook.pyiesone.dev**

- **Home:** introduction, note count, and the two latest notes.
- **Notes:** add notes, delete them, and undo the latest deletion.
- Notes persist after refresh in this browser's `localStorage`.
- No database, external services, analytics, fonts, or runtime dependencies.

## Run it

Install Node.js 22 or later, clone this repository, then run:

```sh
npm start
```

Open **http://127.0.0.1:3000**. No `npm install` or build step is needed.

The server binds to localhost by default. Set `HOST` and `PORT` if your hosting
environment needs a different interface or port. For example, on Linux:

```sh
HOST=0.0.0.0 PORT=3000 npm start
```

For home-server hosting, keep the default localhost binding and place your
existing HTTPS reverse proxy or tunnel in front of it. Do not expose development
or admin services just to serve this app.

## Static hosting

You can also serve the **`public/`** directory with Nginx, Caddy, or another static
host. The pages link to `index.html` and `notes.html`, so no special routing or
build is required. Use HTTPS for a public deployment. The included Node server
also accepts `/notes`.

## Data and limits

This is a browser-local demo, not a shared database app. Each browser and origin
has its own notebook. Clearing site data removes the notes, and opening the app
on a new device, hostname, or port shows a separate notebook. It stores up to
100 notes, with 80-character titles and 2,000-character bodies. There is no login,
cloud backup, or cross-device sync; don't use it as the only copy of important data.

## Check the JavaScript

```sh
npm run check
```

## Home-server deployment

The live site is served by Nginx inside 4bytedigi's isolated application VM.
Traffic passes through the existing gateway VM and named Cloudflare tunnel.
Notebook has its own hostname and shares the existing internal web port; no
new public server ports, database, or Node process are required.

`deploy/install.py` is specific to this server's existing configuration. It
checks the archive checksum, installs only the five public assets, validates
Nginx and tunnel configuration, tests Notebook and both existing health
endpoints, and restores prior routing configuration if installation fails.
Configuration snapshots are kept under `/var/backups/notebook` on the host.
It requires the existing root-only VM SSH configuration; no credentials are
stored in this repository.

To release a new committed revision from PowerShell in this repository:

```powershell
git archive --format=tar --output="$env:TEMP/notebook-release.tar" HEAD
$releaseHash = (Get-FileHash "$env:TEMP/notebook-release.tar" -Algorithm SHA256).Hash.ToLower()
scp "$env:TEMP/notebook-release.tar" 4bytedigi:/home/pyie/notebook-deploy/release.tar
scp deploy/install.py 4bytedigi:/home/pyie/notebook-deploy/install.py
ssh -t 4bytedigi "sudo python3 /home/pyie/notebook-deploy/install.py /home/pyie/notebook-deploy/release.tar $releaseHash"
```

The proxied Cloudflare DNS record for `notebook` already points at the existing
tunnel. Ordinary releases do not require DNS changes. Git pushes alone do not
deploy automatically; run the release commands after pushing. Nginx and the
tunnel start with the existing hosting services, so closing the SSH terminal
does not stop the site.

The source is recoverable from GitHub and can be redeployed if the VM is lost.
Server backups do not contain visitors' notes: notes exist only in each
visitor's browser, and notes from the localhost preview are a separate notebook.

## Files

```text
public/
  index.html     Home page
  notes.html     Notebook page
  styles.css     Responsive design
  app.js         Local note storage and interactions
  favicon.svg    App icon
server.mjs       Optional Node.js static server
```
