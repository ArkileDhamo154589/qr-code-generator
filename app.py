from flask import Flask, render_template, request, jsonify
import qrcode
import base64
import re
from io import BytesIO

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(debug=True)
