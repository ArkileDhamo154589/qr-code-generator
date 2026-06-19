# QR Code Generator

A fast, local-first QR code generator built with Flask. Turn any link or text
into a static QR code, then export it as a transparent image, a print-ready
PDF, or a designed business card.

The UI is a dark, CloudConvert-style interface with a live 3D animated
background (three.js) and a mobile-first responsive layout.

## Features

- Convert any URL or text into a static QR code (never expires, no tracking)
- Pick the QR color and toggle a transparent background
- Three export modes:
  - **Image** — transparent PNG, ready for any design
  - **PDF** — A4 page with the QR centered and the link printed below
  - **Card** — business-card layout (85.6 x 54 mm) you can print or save as PDF
- 3D animated background and tilt interactions
- No database, no third-party APIs, runs fully offline once installed

## Tech stack

- Flask (Python)
- qrcode + Pillow for QR generation
- three.js (animated background)
- jsPDF (client-side PDF and card export, vendored locally)
- gunicorn (production server)

## Run locally

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask --app app run --debug
```

Then open http://127.0.0.1:5000

To make it reachable from other devices on your network (e.g. a phone):

```bash
flask --app app run --host 0.0.0.0 --port 8080
```

Open `http://<your-computer-ip>:8080`. Avoid browser-blocked ports such as
5060/5061; 8080 and 8000 are safe.

## Deploy to Render

This repo is ready for [Render](https://render.com):

- A `render.yaml` blueprint and a `Procfile` are included.
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Build command: `pip install -r requirements.txt`

Create a new Web Service from the repository (or use the blueprint) and Render
will build and start it automatically.

## License

Open source. Use it freely for websites, print, or internal tools.
