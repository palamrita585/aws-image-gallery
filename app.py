
from flask import Flask, render_template_string, request, redirect, flash
import boto3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "temporary-gallery-key-change-later"

BUCKET_NAME = "amrita-gallery-123"
REGION = "ap-southeast-2"

ALLOWED = {"jpg", "jpeg", "png", "webp", "gif"}

s3 = boto3.client("s3", region_name=REGION)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>AWS Image Gallery</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {margin:0;background:#111827;color:white;font-family:Arial}
header {text-align:center;padding:30px;background:#1f2937}
.actions {text-align:center;padding:25px}
button {background:#2563eb;color:white;border:0;padding:12px 20px;
border-radius:7px;cursor:pointer;margin:5px}
.delete {background:#dc2626}
.gallery {display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
gap:22px;padding:25px}
.card {background:#1f2937;border-radius:12px;overflow:hidden;text-align:center}
.card img {width:100%;height:230px;object-fit:cover}
footer {text-align:center;padding:25px;color:#9ca3af}
</style>
</head>
<body>

<header>
<h1>My AWS Image Gallery</h1>
<p>Powered by Amazon EC2 and Amazon S3</p>
</header>

<div class="actions">
<h3>Upload New Image</h3>
<form action="/upload" method="POST" enctype="multipart/form-data">
<input type="file" name="image" accept="image/*" required>
<button type="submit">Upload Image</button>
</form>
{% with messages = get_flashed_messages() %}
{% for message in messages %}
<p>{{ message }}</p>
{% endfor %}
{% endwith %}
</div>

<div class="gallery">
{% for image in images %}
<div class="card">
<img src="{{ image.url }}" alt="{{ image.name }}">
<h3>{{ image.name }}</h3>
<form action="/delete" method="POST"
onsubmit="return confirm('Are you sure you want to delete this image?')">
<input type="hidden" name="key" value="{{ image.key }}">
<button class="delete" type="submit">Delete Image</button>
</form>
</div>
{% endfor %}
</div>

<footer>Hosted on AWS EC2 | Images stored in Amazon S3</footer>
</body>
</html>
"""

@app.route("/")
def home():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    images = []

    for item in response.get("Contents", []):
        key = item["Key"]
        if "." in key and key.rsplit(".", 1)[1].lower() in ALLOWED:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET_NAME, "Key": key},
                ExpiresIn=3600
            )
            images.append({"name": key, "key": key, "url": url})

    return render_template_string(HTML, images=images)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")

    if not file or not file.filename:
        flash("Please select an image.")
        return redirect("/")

    filename = secure_filename(file.filename)

    if "." not in filename or filename.rsplit(".", 1)[1].lower() not in ALLOWED:
        flash("Invalid image format.")
        return redirect("/")

    try:
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": file.mimetype or "application/octet-stream"}
        )
        flash("Image uploaded successfully!")
    except Exception:
        app.logger.exception("Upload failed")
        flash("Upload failed.")

    return redirect("/")


@app.route("/delete", methods=["POST"])
def delete():
    key = request.form.get("key", "")

    if "/" in key or "." not in key or key.rsplit(".", 1)[1].lower() not in ALLOWED:
        return "Invalid filename", 400

    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=key)
        flash("Image deleted successfully!")
    except Exception:
        app.logger.exception("Delete failed")
        flash("Delete failed.")

    return redirect("/")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
