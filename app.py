import os
from flask import Flask, request, jsonify, render_template, redirect, session
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__, template_folder="templates")
app.secret_key = "keshika-secret"  # For sessions

# MongoDB connection
client = MongoClient("mongodb+srv://krishnabk0803:keshika0803@cluster0.5jw6k.mongodb.net/database")
db = client["database"]
collection = db["collection"]

# Home Page
@app.route("/")
def home():
    return render_template("home.html")

# Passenger Page
@app.route("/passenger")
def passenger():
    return render_template("index.html")

# Search Buses by location + time
@app.route("/search", methods=["GET"])
def search_buses():
    start = request.args.get("start")
    end = request.args.get("end")
    time_from = request.args.get("time_from")
    time_to = request.args.get("time_to")

    if not start or not end or not time_from or not time_to:
        return jsonify({"error": "Missing search inputs"}), 400

    try:
        from_time_obj = datetime.strptime(time_from, "%H:%M")
        to_time_obj = datetime.strptime(time_to, "%H:%M")

        from_am_pm = from_time_obj.strftime("%I:%M %p")
        to_am_pm = to_time_obj.strftime("%I:%M %p")
    except ValueError:
        return jsonify({"error": "Invalid time format"}), 400

    buses = collection.find(
        {"start": start, "end": end},
        {"busName": 1, "time": 1, "status": 1, "location": 1, "_id": 0}
    )

    results = []
    for bus in buses:
        try:
            bus_time = datetime.strptime(bus["time"], "%I:%M %p").time()
            if from_time_obj.time() <= bus_time <= to_time_obj.time():
                results.append(bus)
        except:
            continue

    if not results:
        return jsonify({"message": "No buses found for selected time and route."})

    return jsonify(results)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username.endswith("-con"):
            bus_name = username.replace("-con", "")
            if password == f"{bus_name}1234":
                session["bus"] = bus_name
                return redirect("/conductor")
            else:
                return render_template("login.html", error="Invalid password")
        else:
            return render_template("login.html", error="Invalid username format")

    return render_template("login.html")

# Conductor Dashboard
@app.route("/conductor", methods=["GET", "POST"])
def conductor():
    if "bus" not in session:
        return redirect("/login")

    bus_name = session["bus"]

    if request.method == "POST":
        status = request.form["status"]
        lat = request.form.get("lat")
        lng = request.form.get("lng")

        update_fields = {"status": status}
        if lat and lng:
            update_fields["location"] = {"lat": float(lat), "lng": float(lng)}

        result = collection.update_one(
            {"busName": bus_name},
            {"$set": update_fields},
            upsert=False
        )

        message = "Status and location updated!" if result.modified_count else "No matching bus found."
        return render_template("conductor.html", bus=bus_name, message=message)

    return render_template("conductor.html", bus=bus_name)

# Live Location Update Route (every 5 seconds)
@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json()

    lat = data.get('lat')
    lng = data.get('lng')
    bus_name = data.get('bus_name')

    if not all([lat, lng, bus_name]):
        return jsonify({'error': 'Missing data'}), 400

    result = collection.update_one(
        {"busName": bus_name},
        {"$set": {"location": {"lat": float(lat), "lng": float(lng)}}}
    )

    if result.matched_count:
        return jsonify({'message': 'Location updated'}), 200
    else:
        return jsonify({'error': 'Bus not found'}), 404

# Add Bus
@app.route("/add_bus", methods=["POST"])
def add_bus():
    data = request.get_json()

    required_fields = ["busName", "start", "end", "time"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    status = data.get("status", "Not Started")
    location = data.get("location", None)

    new_bus = {
        "busName": data["busName"],
        "start": data["start"],
        "end": data["end"],
        "time": data["time"],
        "status": status,
    }

    if location:
        new_bus["location"] = location

    collection.insert_one(new_bus)
    return jsonify({"message": "Bus added successfully"}), 201

# Logout
@app.route("/logout")
def logout():
    session.pop("bus", None)
    return redirect("/")

# Start Server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
