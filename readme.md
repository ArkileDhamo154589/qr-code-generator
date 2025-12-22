# QR Code Generator (Local Web App)

This project is a **generic QR Code generator section** that can be used
as part of a website or as a standalone local tool.

It allows you to generate QR codes from any URL and download them as
images with a **transparent background**.

The application runs **100% locally** and does not require an internet
connection after installation.

---

##  What is this project?

This is a simple local web application that:
- Can be embedded as a **generic section** in a website
- Allows users to input a URL
- Generates a QR Code that **never expires**
- Allows downloading the QR Code as a **transparent PNG**

It does not use any third-party APIs or external services.

---

##  Features

- Local web interface
- URL input via form
- QR codes that never expire
- Transparent PNG export
- Lightweight & fast
- No database
- No external APIs
- Ideal for websites, print, or internal tools

---

##  Requirements

- Python 3.9+
- pip
- Linux / macOS / Windows (WSL works)

---

##  Installation & Setup (Local)

### 1️ Clone the repository

```bash
git clone https://github.com/ArkileDhamo154589/qr-code-generator.git
cd qr-code-generator

Create a virtual environment
python3 -m venv venv

Activate it:
source venv/bin/activate

If activation was successful, your terminal will show: (venv)

Install dependencies

pip install flask qrcode[pil] pillow

Run the application
python app.py

If everything is correct, you will see:
Running on http://127.0.0.1:5000