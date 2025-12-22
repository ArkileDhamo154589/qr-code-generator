from flask import Flask, request, send_file, render_template_string
import qrcode
from PIL import Image
import io

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
  <title>QR Code Generator</title>
</head>
<body>
  <h2>QR Code Generator (Transparent)</h2>

  <form method="post">
    <input type="url" name="url" placeholder="Βάλε το URL εδώ" required style="width:300px">
    <button type="submit">Generate QR</button>
  </form>

  {% if qr_ready %}
    <br>
    <a href="/download">
      <button>Κατέβασε το QR (PNG)</button>
    </a>
  {% endif %}
</body>
</html>
"""

qr_image_bytes = None


def generate_qr(url: str):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGBA")

    datas = img.getdata()
    new_data = []

    for item in datas:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))  # transparent
        else:
            new_data.append(item)

    img.putdata(new_data)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@app.route("/", methods=["GET", "POST"])
def index():
    global qr_image_bytes

    if request.method == "POST":
        url = request.form["url"]
        qr_image_bytes = generate_qr(url)
        return render_template_string(HTML, qr_ready=True)

    return render_template_string(HTML, qr_ready=False)


@app.route("/download")
def download():
    return send_file(
        qr_image_bytes,
        mimetype="image/png",
        as_attachment=True,
        download_name="qr_transparent.png"
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
