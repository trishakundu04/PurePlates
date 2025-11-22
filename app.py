from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "MahimaSingh@121"  # change for production

# --- Database (users)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Load dataset
CSV_PATH = "PurePlates.csv"
if not os.path.exists(CSV_PATH):
    print("WARNING: PurePlates.csv not found. Put it in the project root.")
    df = None
else:
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]


# --- Routes
@app.route("/")
def logo():
    return render_template("logo.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists", "danger")
            return redirect(url_for("signup"))

        user = User(fullname=fullname, email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Logged in successfully", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("result.html", user=session.get("username"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# API: JSON search
@app.route("/api/search", methods=["POST"])
def api_search():
    if "user_id" not in session:
        return jsonify({"error": "unauthenticated"}), 401
    payload = request.get_json() or {}
    query = (payload.get("query") or "").strip().lower()
    search_by = payload.get("by", "any")  # 'food', 'allergen', or 'any'

    if not df is None and query:
        results = []
        for idx, row in df.iterrows():
            # safe-get columns (use names from your CSV)
            food = str(row.get("food_product", "") or "")
            ingredients = str(row.get("main_ingredient", "") or "")
            allergens = str(row.get("allergic_ingredients", "") or "")
            allergy_type = str(row.get("associated_allergies", "") or "")
            symptoms = str(row.get("symptoms", "") or "")

            hay = " ".join([food, ingredients, allergens, allergy_type, symptoms]).lower()

            match = False
            if search_by == "food":
                match = query in food.lower()
            elif search_by == "allergen":
                match = query in allergens.lower() or query in ingredients.lower() or query in allergy_type.lower()
            else:
                match = query in hay

            if match:
                results.append({
                    "id": int(idx),
                    "food": food,
                    "ingredients": ingredients,
                    "allergens": allergens,
                    "allergy_type": allergy_type,
                    "symptoms": symptoms
                })

        return jsonify(results)
    return jsonify([])

# Optional: detail page for a row
@app.route("/food/<int:row_id>")
def food_detail(row_id):
    if df is None:
        flash("Dataset not loaded", "danger")
        return redirect(url_for("dashboard"))
    try:
        row = df.iloc[row_id]
    except Exception:
        flash("Food item not found", "danger")
        return redirect(url_for("dashboard"))

    return render_template("food_detail.html",
                           food=str(row.get("food_product", "")),
                           ingredients=str(row.get("main_ingredient", "")),
                           allergens=str(row.get("allergic_ingredients", "")),
                           allergy_type=str(row.get("associated_allergies", "")),
                           symptoms=str(row.get("symptoms", "")),
                           row_id=row_id)


   

if __name__ == "__main__":
    # Create DB tables once at startup (avoid using removed before_first_request)
    with app.app_context():
        db.create_all()

        # Debug prints to confirm CSV load and working directory
        if df is None:
            print("WARNING: PurePlates.csv not found. Current working directory:", os.getcwd())
            print("Files in current directory:", os.listdir())
        else:
            print("Loaded PurePlates.csv successfully. Rows:", len(df))
            # print first 5 rows to verify
            print(df.head().to_string(index=False))

    app.run(debug=True)

