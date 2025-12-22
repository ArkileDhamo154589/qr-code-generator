from flask import Flask, render_template, request
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)


def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
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
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            qr_image = generate_qr_base64(url)
            return render_template("index.html", qr_image=qr_image, url=url)

    # GET → clean page
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
