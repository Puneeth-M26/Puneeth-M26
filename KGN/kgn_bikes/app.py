import os
import random
import string
import datetime as dt
from typing import Optional
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory
)
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename

# -----------------------------
# Config
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_change_me")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/kgn_bikes")
mongo = PyMongo(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB


OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "kgnowner")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "kgn123")


BRANDS = ["Honda", "Yamaha", "Suzuki", "KTM", "Royal Enfield", "Bajaj", "TVS", "Hero"]

@app.route("/brand/<brand_name>")
def bikes_by_brand(brand_name):
    bikes = Bike.query.filter(Bike.name.ilike(f"%{brand_name}%")).all()
    return render_template("all_bikes.html", bikes=bikes, brand=brand_name)

# -----------------------------
    bikes = mongo.db.bikes.find({"name": {"$regex": brand_name, "$options": "i"}})
# -----------------------------
def _column_names(table_name: str) -> set[str]:
    rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).all()
    return {r[1] for r in rows}

 # Removed SQLAlchemy related functions and calls
def current_buyer() -> Optional[Buyer]:
    buyer_id = session.get("buyer_id")
    return Buyer.query.get(buyer_id) if buyer_id else None

def save_image(file) -> Optional[str]:
    if not file or file.filename == "":
     return mongo.db.buyers.find_one({"_id": buyer_id}) if buyer_id else None
    filename = secure_filename(file.filename)
    root, ext = os.path.splitext(filename)
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    filename = f"{root}_{rand}{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    return f"uploads/{filename}"

def clean_expired_otps():
    now = dt.datetime.utcnow()
    OTP.query.filter(OTP.expires_at < now).delete()
    db.session.commit()

def buyer_required(f):
    mongo.db.otps.delete_many({"expires_at": {"$lt": now}})
    if not session.get("buyer_id"):
        flash("Please login as buyer.", "error")
        return redirect(url_for("buyer_login"))
    return f(*args, **kwargs)

def owner_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("owner"):
            flash("Please login as owner.", "error")
            return redirect(url_for("owner_login"))
        return f(*args, **kwargs)
    return wrapper

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template(
        "home.html",
        title="KGN Bikes Home",
        brands=BRANDS,
        brand_logos=BRAND_LOGOS  # <-- add this
    )


# -----------------------------
# Owner Routes
# -----------------------------
# -----------------------------
# Brands and their logos
# -----------------------------
BRANDS = ["Honda", "Yamaha", "Suzuki", "KTM", "Royal Enfield", "Bajaj", "TVS", "Hero"]

BRAND_LOGOS = {
    "Honda": "/static/images/honda.webp",
    "Yamaha": "/static/images/yamaha.webp",
    "Suzuki": "/static/images/suszuki.webp",
    "KTM": "/static/images/ktm.webp",
    "Royal Enfield": "/static/images/royal.webp",
    "Bajaj": "/static/images/bajaj.webp",
    "TVS": "/static/images/tvs.jpg",
    "Hero": "/static/images/hero.webp",
}


@app.route("/owner-login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == OWNER_USERNAME and password == OWNER_PASSWORD:
            session["owner"] = True
            flash("Owner logged in.", "success")
            return redirect(url_for("owner_portal"))
        flash("Invalid credentials.", "error")
    return render_template("owner_login.html")

@app.route("/owner-portal", methods=["GET", "POST"])
@owner_required
def owner_portal():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        model = (request.form.get("model") or "").strip()
        price_raw = (request.form.get("price") or "").strip()
        year_raw = (request.form.get("year") or "").strip()
        mileage_raw = (request.form.get("mileage") or "").strip()
        runned_kms_raw = (request.form.get("runned_kms") or "").strip()
        location = (request.form.get("location") or "").strip()
        description = (request.form.get("description") or "").strip()
        contact = (request.form.get("contact") or "").strip()
        imgfile = request.files.get("image")

        if not name or not model or not price_raw or not year_raw:
            flash("Name, model, price and year are required.", "error")
            return redirect(url_for("owner_portal"))

        try:
            price = float(price_raw)
        except ValueError:
            price = 0.0

        try:
            year = int(year_raw)
        except ValueError:
            year = 0

        mileage = float(mileage_raw) if mileage_raw else None
        runned_kms = int(runned_kms_raw) if runned_kms_raw else None

        bike = Bike(
            name=name, model=model, price=price, year=year,
            mileage=mileage, runned_kms=runned_kms,
            location=location, description=description,
            contact=contact, image=save_image(imgfile)
        )
        db.session.add(bike)
        db.session.commit()
        flash("Bike added successfully!", "success")
        return redirect(url_for("owner_portal"))

    bikes = Bike.query.order_by(Bike.id.desc()).all()
    return render_template("owner_portal.html", bikes=bikes)

@app.route("/delete-bike/<int:bike_id>")
@owner_required
def delete_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    if bike.image:
        path = os.path.join(app.static_folder, bike.image)
        if os.path.isfile(path):
            try: os.remove(path)
            except Exception: pass
    db.session.delete(bike)
    db.session.commit()
    flash("Bike deleted.", "success")
    return redirect(url_for("owner_portal"))

@app.route("/owner-logout", methods=["POST"])
@owner_required
def owner_logout():
    session.pop("owner", None)
    flash("Owner logged out.", "info")
    return redirect(url_for("home"))

# -----------------------------
# Buyer Routes
# -----------------------------
@app.route("/buyer-login", methods=["GET", "POST"])
def buyer_login():
    clean_expired_otps()
    otp_sent = False
    phone = None
    otp = None
    if request.method == "POST":
        if request.form.get("otp_input"):
            phone = (request.form.get("phone") or "").strip()
            code = (request.form.get("otp_input") or "").strip()
            record = OTP.query.filter_by(phone=phone, code=code).filter(
                OTP.expires_at > dt.datetime.utcnow()
            ).first()
            if record:
                buyer = Buyer.query.filter_by(phone=phone).first()
                if not buyer:
                    buyer = Buyer(phone=phone)
                    db.session.add(buyer)
                    db.session.commit()
                session["buyer_id"] = buyer.id
                db.session.delete(record)
                db.session.commit()
                flash("Logged in successfully.", "success")
                return redirect(url_for("buy_bikes"))
            flash("Invalid or expired OTP.", "error")
        else:
            phone = (request.form.get("phone") or "").strip()
            if phone:
                otp = str(random.randint(1000, 9999))
                db.session.add(OTP(
                    phone=phone,
                    code=otp,
                    expires_at=dt.datetime.utcnow() + dt.timedelta(minutes=5)
                ))
                db.session.commit()
                otp_sent = True
                flash(f"OTP generated (demo): {otp}", "info")
            else:
                flash("Enter phone number.", "error")
    return render_template("buyer_login.html", otp_sent=otp_sent, otp=otp, phone=phone)

@app.route("/buyer-logout", methods=["POST"])
@buyer_required
def buyer_logout():
    session.pop("buyer_id", None)
    flash("Buyer logged out.", "info")
    return redirect(url_for("home"))

@app.route("/profile", methods=["GET", "POST"])
@buyer_required
def profile():
    buyer = current_buyer()
    if request.method == "POST":
        buyer.name = (request.form.get("name") or "").strip()
        buyer.email = (request.form.get("email") or "").strip()
        buyer.address = (request.form.get("address") or "").strip()
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", buyer=buyer)

@app.route("/buy-bikes")
@buyer_required
def buy_bikes():
    bikes = Bike.query.order_by(Bike.id.desc()).all()
    return render_template("buy_bikes.html", bikes=bikes)

@app.route("/cart")
@buyer_required
def cart():
    buyer = current_buyer()
    items = CartItem.query.filter_by(buyer_id=buyer.id).all()
    total = sum(i.bike.price for i in items)
    return render_template("cart.html", items=items, total=total)

@app.route("/wishlist")
@buyer_required
def wishlist():
    buyer = current_buyer()
    items = WishlistItem.query.filter_by(buyer_id=buyer.id).all()
    return render_template("wishlist.html", items=items)

# Cart / Wishlist Actions
@app.route("/add-to-cart/<int:bike_id>", methods=["POST"])
@buyer_required
def add_to_cart(bike_id):
    buyer = current_buyer()
    exists = CartItem.query.filter_by(buyer_id=buyer.id, bike_id=bike_id).first()
    if not exists:
        db.session.add(CartItem(buyer_id=buyer.id, bike_id=bike_id))
        db.session.commit()
        flash("Added to cart.", "success")
    else:
        flash("Already in cart.", "info")
    return redirect(url_for("buy_bikes"))

@app.route("/add-to-wishlist/<int:bike_id>", methods=["POST"])
@buyer_required
def add_to_wishlist(bike_id):
    buyer = current_buyer()
    exists = WishlistItem.query.filter_by(buyer_id=buyer.id, bike_id=bike_id).first()
    if not exists:
        db.session.add(WishlistItem(buyer_id=buyer.id, bike_id=bike_id))
        db.session.commit()
        flash("Added to wishlist.", "success")
    else:
        flash("Already in wishlist.", "info")
    return redirect(url_for("buy_bikes"))

@app.route("/remove-from-cart/<int:item_id>", methods=["POST"])
@buyer_required
def remove_from_cart(item_id):
    buyer = current_buyer()
    item = CartItem.query.get_or_404(item_id)
    if item.buyer_id != buyer.id:
        flash("Not allowed.", "error")
        return redirect(url_for("cart"))
    db.session.delete(item)
    db.session.commit()
    flash("Removed from cart.", "success")
    return redirect(url_for("cart"))

@app.route("/remove-from-wishlist/<int:item_id>", methods=["POST"])
@buyer_required
def remove_from_wishlist(item_id):
    buyer = current_buyer()
    item = WishlistItem.query.get_or_404(item_id)
    if item.buyer_id != buyer.id:
        flash("Not allowed.", "error")
        return redirect(url_for("wishlist"))
    db.session.delete(item)
    db.session.commit()
    flash("Removed from wishlist.", "success")
    return redirect(url_for("wishlist"))

@app.route("/move-wishlist-to-cart/<int:item_id>", methods=["POST"])
@buyer_required
def move_wishlist_to_cart(item_id):
    buyer = current_buyer()
    item = WishlistItem.query.get_or_404(item_id)
    if item.buyer_id != buyer.id:
        flash("Not allowed.", "error")
        return redirect(url_for("wishlist"))
    exists = CartItem.query.filter_by(buyer_id=buyer.id, bike_id=item.bike_id).first()
    if not exists:
        db.session.add(CartItem(buyer_id=buyer.id, bike_id=item.bike_id))
    db.session.delete(item)
    db.session.commit()
    flash("Moved to cart.", "success")
    return redirect(url_for("cart"))

#emi route
@app.route('/emi-calculator')
def emi_calculator():
    return render_template('emi.html')


# Public Pages
@app.route("/all-bikes")
def all_bikes():
    bikes = Bike.query.order_by(Bike.id.desc()).all()
    return render_template("all_bikes.html", bikes=bikes)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/bike/<int:bike_id>")
def bike_info(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    return render_template("bike_info.html", bike=bike)

# Run App
if __name__ == "__main__":
    import socket

    # Get your PC's local IP (for easy copy-paste on mobile)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\n🚀 KGN Bikes app is running!")
    print(f"👉 On this PC:   http://127.0.0.1:5000")
    print(f"👉 On your phone: http://{local_ip}:5000\n")

    app.run(host="0.0.0.0", port=5000, debug=True)