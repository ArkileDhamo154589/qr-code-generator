from flask import Flask, render_template, request, jsonify, redirect, send_file
import qrcode
import sqlite3
import secrets
import time
import zipfile
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer,
    RoundedModuleDrawer,
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
)
from qrcode.image.styles.colormasks import SolidFillColorMask, RadialGradiantColorMask
import base64
import re
import os
from io import BytesIO
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrstudio.db")
CODE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS links ("
        "code TEXT PRIMARY KEY, target TEXT NOT NULL, token TEXT NOT NULL, "
        "created_at REAL NOT NULL, scans INTEGER NOT NULL DEFAULT 0)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS scans ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, "
        "ts REAL NOT NULL, ua TEXT)"
    )
    con.commit()
    con.close()


init_db()


def _gen_code(n=6):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(n))


def _with_scheme(url):
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return "http://" + url
    return url


DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "dots": CircleModuleDrawer,
    "gapped": GappedSquareModuleDrawer,
}

MAX_FILES = 25
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB per file
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

# target format -> (PIL format, file extension, mime type, keeps alpha)
TARGETS = {
    "png": ("PNG", "png", "image/png", True),
    "jpg": ("JPEG", "jpg", "image/jpeg", False),
    "webp": ("WEBP", "webp", "image/webp", True),
    "avif": ("AVIF", "avif", "image/avif", True),
}

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _hex_to_rgb(value: str, fallback=(0, 0, 0)):
    if not value or not HEX_RE.match(value):
        return fallback
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _sanitize_hex(value, fallback="#000000"):
    value = (value or "").strip()
    return value if HEX_RE.match(value) else fallback


def _build_qr(data: str):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr


def generate_qr_png(qr, fill="#000000", transparent=True, style="square",
                    gradient=False, fill2="#000000", logo_img=None) -> str:
    fill_rgb = _hex_to_rgb(fill, (0, 0, 0))
    drawer_cls = DRAWERS.get(style, SquareModuleDrawer)

    if gradient:
        color_mask = RadialGradiantColorMask(
            back_color=(255, 255, 255),
            center_color=fill_rgb,
            edge_color=_hex_to_rgb(fill2, fill_rgb),
        )
    else:
        color_mask = SolidFillColorMask(back_color=(255, 255, 255), front_color=fill_rgb)

    kwargs = dict(
        image_factory=StyledPilImage,
        module_drawer=drawer_cls(),
        color_mask=color_mask,
    )
    if logo_img is not None:
        kwargs["embeded_image"] = logo_img

    img = qr.make_image(**kwargs).convert("RGBA")

    # Transparency only when there is no logo (so we don't punch holes in it).
    if transparent and logo_img is None:
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def generate_qr_svg(qr, fill="#000000", transparent=True, logo_data_url=None) -> str:
    fill = _sanitize_hex(fill, "#000000")
    count = qr.modules_count
    border = qr.border
    size = count + border * 2
    px = size * 10

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" '
        f'viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
    ]
    if not transparent:
        parts.append(f'<rect width="{size}" height="{size}" fill="#ffffff"/>')

    path = []
    modules = qr.modules
    for r in range(count):
        row = modules[r]
        for c in range(count):
            if row[c]:
                path.append(f"M{c + border} {r + border}h1v1h-1z")
    parts.append(f'<path d="{"".join(path)}" fill="{fill}"/>')

    if logo_data_url:
        lw = size * 0.24
        off = (size - lw) / 2.0
        pad = lw * 0.14
        parts.append(
            f'<rect x="{off - pad:.2f}" y="{off - pad:.2f}" '
            f'width="{lw + pad * 2:.2f}" height="{lw + pad * 2:.2f}" '
            f'rx="{lw * 0.12:.2f}" fill="#ffffff"/>'
        )
        parts.append(
            f'<image href="{logo_data_url}" x="{off:.2f}" y="{off:.2f}" '
            f'width="{lw:.2f}" height="{lw:.2f}" preserveAspectRatio="xMidYMid meet"/>'
        )

    parts.append("</svg>")
    return "".join(parts)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.webmanifest")
def manifest():
    resp = app.send_static_file("manifest.webmanifest")
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


@app.route("/sw.js")
def service_worker():
    # Served from root so the service worker can control the whole site.
    resp = app.send_static_file("sw.js")
    resp.headers["Content-Type"] = "text/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/generate", methods=["POST"])
def generate():
    # Accept multipart (with an optional logo file) or JSON.
    data = request.form if request.form else (request.get_json(silent=True) or {})

    url = (data.get("url") or "").strip()
    if not url:
        return jsonify(error="Please enter a link or text."), 400

    color = _sanitize_hex(data.get("color"), "#000000")
    color2 = _sanitize_hex(data.get("color2"), color)
    transparent = str(data.get("transparent", "true")).lower() != "false"
    style = (data.get("style") or "square").lower()
    if style not in DRAWERS:
        style = "square"
    gradient = str(data.get("gradient", "false")).lower() == "true"

    logo_img = None
    logo_data_url = None
    logo_file = request.files.get("logo")
    if logo_file and logo_file.filename:
        try:
            logo_img = Image.open(logo_file.stream).convert("RGBA")
            buf = BytesIO()
            logo_img.save(buf, format="PNG")
            logo_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            logo_img = None
            logo_data_url = None

    qr = _build_qr(url)
    png = generate_qr_png(qr, color, transparent, style, gradient, color2, logo_img)
    svg = generate_qr_svg(qr, color, transparent, logo_data_url)

    return jsonify(qr_image=png, svg=svg, url=url)


def convert_image(file_storage, target, quality=90, max_dim=0, original_bytes=0,
                  rotate=0, flip="", crop=False):
    pil_format, ext, mime, keeps_alpha = TARGETS[target]

    image = Image.open(file_storage.stream)

    # Center-crop to a square.
    if crop:
        s = min(image.width, image.height)
        left = (image.width - s) // 2
        top = (image.height - s) // 2
        image = image.crop((left, top, left + s, top + s))

    # Rotate clockwise by 90 / 180 / 270 degrees.
    if rotate in (90, 180, 270):
        image = image.rotate(-rotate, expand=True)

    # Flip.
    if flip == "h":
        image = image.transpose(Image.FLIP_LEFT_RIGHT)
    elif flip == "v":
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

    # Optional downscale (keeps aspect ratio, never upscales).
    if max_dim and (image.width > max_dim or image.height > max_dim):
        image.thumbnail((max_dim, max_dim), Image.LANCZOS)

    save_kwargs = {}
    if keeps_alpha:
        if image.mode not in ("RGBA", "RGB"):
            image = image.convert("RGBA")
    else:
        # Formats without alpha (JPEG): flatten onto white.
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

    if pil_format == "PNG":
        save_kwargs["optimize"] = True
    else:
        save_kwargs["quality"] = quality

    buffer = BytesIO()
    image.save(buffer, format=pil_format, **save_kwargs)
    buffer.seek(0)

    base = os.path.splitext(os.path.basename(file_storage.filename or "image"))[0]
    out_name = (base or "image") + "." + ext
    data_url = "data:" + mime + ";base64," + base64.b64encode(buffer.getvalue()).decode()
    return {
        "name": out_name,
        "dataUrl": data_url,
        "bytes": buffer.getbuffer().nbytes,
        "originalBytes": original_bytes,
        "width": image.width,
        "height": image.height,
    }


@app.route("/convert", methods=["POST"])
def convert():
    target = (request.form.get("target") or "").strip().lower()
    if target not in TARGETS:
        return jsonify(error="Unsupported target format."), 400

    try:
        quality = int(request.form.get("quality") or 90)
    except ValueError:
        quality = 90
    quality = max(10, min(100, quality))

    try:
        max_dim = int(request.form.get("max_dim") or 0)
    except ValueError:
        max_dim = 0
    max_dim = max(0, min(10000, max_dim))

    try:
        rotate = int(request.form.get("rotate") or 0)
    except ValueError:
        rotate = 0
    if rotate not in (0, 90, 180, 270):
        rotate = 0

    flip = (request.form.get("flip") or "").strip().lower()
    if flip not in ("", "h", "v"):
        flip = ""

    crop = str(request.form.get("crop", "false")).lower() == "true"

    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        return jsonify(error="Please add at least one image."), 400
    if len(files) > MAX_FILES:
        return jsonify(error="Too many files (max %d at once)." % MAX_FILES), 400

    results, errors = [], []
    for f in files:
        try:
            f.stream.seek(0, os.SEEK_END)
            size = f.stream.tell()
            f.stream.seek(0)
            if size > MAX_FILE_BYTES:
                errors.append({"name": f.filename, "error": "File too large (max 20 MB)."})
                continue
            results.append(convert_image(f, target, quality, max_dim, size, rotate, flip, crop))
        except Exception:
            errors.append({"name": f.filename, "error": "Could not convert this file."})

    if not results:
        return jsonify(error="None of the files could be converted.", errors=errors), 400

    return jsonify(results=results, errors=errors, target=target)


# ---------------------------------------------------------------------------
# Dynamic QR codes (short links + scan analytics)
# ---------------------------------------------------------------------------
@app.route("/api/links", methods=["POST"])
def create_link():
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    if not target:
        return jsonify(error="Missing destination."), 400
    target = _with_scheme(target)

    con = sqlite3.connect(DB_PATH)
    code = None
    for _ in range(6):
        candidate = _gen_code()
        try:
            con.execute(
                "INSERT INTO links(code, target, token, created_at) VALUES (?, ?, ?, ?)",
                (candidate, target, secrets.token_urlsafe(12), time.time()),
            )
            con.commit()
            code = candidate
            break
        except sqlite3.IntegrityError:
            continue
    if code is None:
        con.close()
        return jsonify(error="Could not allocate a code, try again."), 500
    token = con.execute("SELECT token FROM links WHERE code=?", (code,)).fetchone()[0]
    con.close()
    return jsonify(code=code, token=token, short_url=request.host_url + "r/" + code)


@app.route("/api/links/<code>", methods=["POST", "PUT"])
def update_link(code):
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    target = (data.get("target") or "").strip()
    if not target:
        return jsonify(error="Missing destination."), 400
    target = _with_scheme(target)

    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT token FROM links WHERE code=?", (code,)).fetchone()
    if not row:
        con.close()
        return jsonify(error="Link not found."), 404
    if row[0] != token:
        con.close()
        return jsonify(error="Invalid edit token."), 403
    con.execute("UPDATE links SET target=? WHERE code=?", (target, code))
    con.commit()
    con.close()
    return jsonify(ok=True, target=target)


@app.route("/api/links/<code>/stats")
def link_stats(code):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT target, created_at, scans FROM links WHERE code=?", (code,)).fetchone()
    if not row:
        con.close()
        return jsonify(error="Link not found."), 404
    recent = con.execute(
        "SELECT ts, ua FROM scans WHERE code=? ORDER BY id DESC LIMIT 10", (code,)
    ).fetchall()
    con.close()
    return jsonify(
        target=row[0],
        created_at=row[1],
        scans=row[2],
        recent=[{"ts": r[0], "ua": r[1]} for r in recent],
    )


@app.route("/r/<code>")
def redirect_link(code):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT target FROM links WHERE code=?", (code,)).fetchone()
    if not row:
        con.close()
        return "Link not found", 404
    con.execute("UPDATE links SET scans = scans + 1 WHERE code=?", (code,))
    con.execute(
        "INSERT INTO scans(code, ts, ua) VALUES (?, ?, ?)",
        (code, time.time(), (request.headers.get("User-Agent") or "")[:300]),
    )
    con.commit()
    con.close()
    return redirect(row[0], code=302)


# ---------------------------------------------------------------------------
# Bulk QR generation -> ZIP
# ---------------------------------------------------------------------------
@app.route("/api/bulk-qr", methods=["POST"])
def bulk_qr():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    items = [str(x).strip() for x in items if str(x).strip()][:200]
    if not items:
        return jsonify(error="Add at least one line."), 400

    color = _sanitize_hex(data.get("color"), "#000000")
    style = (data.get("style") or "square").lower()
    if style not in DRAWERS:
        style = "square"
    transparent = str(data.get("transparent", "true")).lower() != "false"

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, item in enumerate(items, 1):
            qr = _build_qr(item)
            png_b64 = generate_qr_png(qr, color, transparent, style, False, color, None)
            zf.writestr("qr-%03d.png" % i, base64.b64decode(png_b64))
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="qr-codes.zip")


if __name__ == "__main__":
    app.run(debug=True)
