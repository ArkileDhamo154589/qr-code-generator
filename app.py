from flask import Flask, render_template, request, jsonify
import qrcode
import base64
import re
import os
from io import BytesIO
from PIL import Image

app = Flask(__name__)

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


def generate_qr_base64(url: str, fill_color="#000000", transparent=True) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    fill = _hex_to_rgb(fill_color, (0, 0, 0))

    img = qr.make_image(
        fill_color=fill,
        back_color="white",
    ).convert("RGBA")

    if transparent:
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or request.form
    url = (data.get("url") or "").strip()
    color = (data.get("color") or "#000000").strip()
    transparent = str(data.get("transparent", "true")).lower() != "false"

    if not url:
        return jsonify(error="Please enter a link or text."), 400

    qr_image = generate_qr_base64(url, fill_color=color, transparent=transparent)
    return jsonify(qr_image=qr_image, url=url)


def convert_image(file_storage, target):
    pil_format, ext, mime, keeps_alpha = TARGETS[target]

    image = Image.open(file_storage.stream)

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
        save_kwargs["quality"] = 90

    buffer = BytesIO()
    image.save(buffer, format=pil_format, **save_kwargs)
    buffer.seek(0)

    base = os.path.splitext(os.path.basename(file_storage.filename or "image"))[0]
    out_name = (base or "image") + "." + ext
    data_url = "data:" + mime + ";base64," + base64.b64encode(buffer.getvalue()).decode()
    return {"name": out_name, "dataUrl": data_url, "bytes": buffer.getbuffer().nbytes}


@app.route("/convert", methods=["POST"])
def convert():
    target = (request.form.get("target") or "").strip().lower()
    if target not in TARGETS:
        return jsonify(error="Unsupported target format."), 400

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
            results.append(convert_image(f, target))
        except Exception:
            errors.append({"name": f.filename, "error": "Could not convert this file."})

    if not results:
        return jsonify(error="None of the files could be converted.", errors=errors), 400

    return jsonify(results=results, errors=errors, target=target)


if __name__ == "__main__":
    app.run(debug=True)
