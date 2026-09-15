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

After the one-time passwordless deployment setup below, release a committed
revision from PowerShell in this repository:

```powershell
git -c core.autocrlf=false archive --format=tar --output="$env:TEMP/notebook-release.tar" HEAD
scp "$env:TEMP/notebook-release.tar" 4bytedigi:/home/pyie/notebook-deploy/release.tar
ssh -o BatchMode=yes 4bytedigi "sudo -n /usr/local/sbin/notebook-deploy < /home/pyie/notebook-deploy/release.tar"
```

The proxied Cloudflare DNS record for `notebook` already points at the existing
tunnel. Ordinary releases do not require DNS changes. Git pushes alone do not
deploy automatically; run the release commands after pushing. Nginx and the
tunnel start with the existing hosting services, so closing the SSH terminal
does not stop the site.

The source is recoverable from GitHub and can be redeployed if the VM is lost.
Server backups do not contain visitors' notes: notes exist only in each
visitor's browser, and notes from the localhost preview are a separate notebook.

### One-time passwordless deployment setup

An administrator installs reviewed copies of `install.py`,
`passwordless-entry.py`, and the `notebook-deploy` wrapper using
`deploy/setup-passwordless.sh` on 4bytedigi. This step needs the server's sudo
password entered privately in the terminal once. It creates this permission:

```sudoers
pyie ALL=(root) NOPASSWD: /usr/local/sbin/notebook-deploy ""
```

The [empty argument list](https://www.sudo.ws/docs/man/1.9.14/sudoers.man.pdf)
allows only that exact command without arguments. The installed wrapper and
Python programs are owned by root and cannot be edited by the deployment user.
Python runs in isolated mode with a fixed environment. The command accepts an
uncompressed release archive on stdin, checks its size and file types, and
copies only the five public assets. It never executes code from the archive.
Concurrent deployments are rejected. Server passwords are not stored.

This permission is available to the server user `pyie`, including authorized
SSH sessions. It allows publishing replacement HTML/JavaScript on Notebook,
so protect the SSH key as a publishing credential. General administrator
commands still require normal sudo authentication. New applications, changes
to this privileged installer, and new DNS records need separate setup.

To revoke this permission, an administrator removes
`/etc/sudoers.d/notebook-deploy` and runs `sudo visudo -c`. Existing web hosting
continues to run. Security input checks can be run without root on Linux:

```sh
python3 -I deploy/test-entry.py
```

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
