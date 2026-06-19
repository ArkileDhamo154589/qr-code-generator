from flask import Flask, render_template, request, jsonify
import qrcode
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


def convert_image(file_storage, target, quality=90, max_dim=0, original_bytes=0):
    pil_format, ext, mime, keeps_alpha = TARGETS[target]

    image = Image.open(file_storage.stream)

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
            results.append(convert_image(f, target, quality, max_dim, size))
        except Exception:
            errors.append({"name": f.filename, "error": "Could not convert this file."})

    if not results:
        return jsonify(error="None of the files could be converted.", errors=errors), 400

    return jsonify(results=results, errors=errors, target=target)


if __name__ == "__main__":
    app.run(debug=True)
