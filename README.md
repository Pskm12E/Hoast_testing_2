# Little Notes

A small, responsive, two-page web app for testing website hosting.

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
