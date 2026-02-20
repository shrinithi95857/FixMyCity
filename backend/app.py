"""Flask API for FixMyCity complaint management system."""
import os
import sys
import traceback
from pathlib import Path

# Allow running as python backend/app.py from project root
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import base64
import uuid
import requests

from database import init_db, get_db, create_user, authenticate_user, get_user_by_id, \
    track_complaint_submission, get_user_complaints, delete_user_complaint, \
    log_officer_action, get_officer_actions

app = Flask(__name__)
CORS(app)


def geocode_location(area_name, city="Chennai"):
    """Convert area name to latitude and longitude coordinates."""
    try:
        # Simple geocoding using OpenStreetMap Nominatim API
        # In production, use a proper geocoding service like Google Maps API
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{area_name}, {city}, India",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
            'accept-language': 'en-US,en;q=0.9'
        }
        
        # Set headers to avoid being blocked by some servers
        headers = {
            'User-Agent': 'FixMyCity/1.0'
        }
        
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data:
            location = data[0]
            lat = float(location['lat'])
            lon = float(location['lon'])
            app.logger.info(f"Successfully geocoded: {area_name} -> {lat}, {lon}")
            return lat, lon
        
        # Fallback coordinates if geocoding fails
        app.logger.warning(f"Geocoding failed for: {area_name}")
        return None, None
        
    except requests.exceptions.Timeout:
        app.logger.error(f"Geocoding timeout for: {area_name}")
        return None, None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Network error during geocoding for {area_name}: {e}")
        return None, None
    except (KeyError, ValueError, IndexError) as e:
        app.logger.error(f"Parsing error during geocoding for {area_name}: {e}")
        return None, None
    except Exception as e:
        app.logger.error(f"Unexpected error during geocoding for {area_name}: {e}")
        return None, None

# Create uploads directory
UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Ensure DB exists on startup
init_db()


@app.errorhandler(Exception)
def handle_error(e):
    """Return 500 with error detail in JSON so we can see what broke."""
    app.logger.exception(e)
    return jsonify({
        "error": "Internal server error",
        "detail": str(e),
        "traceback": traceback.format_exc() if app.debug else None,
    }), 500


@app.route("/")
def index():
    return jsonify({
        "message": "FixMyCity API", 
        "version": "1.0",
        "health": "/api/health", 
        "complaints": "/api/complaints",
        "register": "/api/register",
        "login": "/api/login"
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "citizen")
    
    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400
    
    if role not in ["citizen", "officer"]:
        return jsonify({"error": "role must be either 'citizen' or 'officer'"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    
    try:
        user_id = create_user(username, email, password, role)
        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id,
            "username": username,
            "role": role
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500


@app.route("/api/login", methods=["POST"])
def login():
    """Authenticate user."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    
    user = authenticate_user(username, password)
    if user:
        return jsonify({
            "message": "Login successful",
            "user": user
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/uploads/<filename>", methods=["GET"])
def serve_image(filename):
    """Serve uploaded images."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/api/complaints", methods=["POST"])
def create_complaint():
    """Submit a new complaint."""
    data = request.get_json(silent=True) or {}
    category = data.get("category") or ""
    severity = data.get("severity") or ""
    description = (data.get("description") or "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    area_name = (data.get("area_name") or "").strip()
    image_data = data.get("image")  # Base64 encoded image
    user_id = data.get("user_id")  # Optional user ID for tracking
    area_importance = data.get("area_importance", "normal")  # Area importance factor

    if not category or not severity:
        return jsonify({"error": "category and severity are required"}), 400
    if not description:
        return jsonify({"error": "description is required"}), 400
    if latitude is None and longitude is None and not area_name:
        return jsonify({"error": "provide latitude/longitude or area_name"}), 400
    
    if area_importance not in ["low", "normal", "high", "critical"]:
        area_importance = "normal"

    timestamp = datetime.utcnow().isoformat() + "Z"
    status = "unresolved"
    image_path = None

    # Geocoding: Convert area name to coordinates if coordinates not provided
    if (latitude is None or longitude is None) and area_name:
        lat_val, lon_val = geocode_location(area_name)
        if lat_val is None or lon_val is None:
            # Use default coordinates for the city if geocoding fails
            lat_val, lon_val = 13.0827, 80.2707  # Chennai default
            app.logger.info(f"Using default coordinates for: {area_name}")
    else:
        # Ensure types for SQLite (e.g. avoid numpy types from frontend)
        lat_val = float(latitude) if latitude is not None else None
        lon_val = float(longitude) if longitude is not None else None

    # Save image if provided
    if image_data:
        try:
            # Decode base64 image
            if "," in image_data:
                header, image_data = image_data.split(",", 1)
                # Try to detect format from header
                if "png" in header.lower():
                    ext = "png"
                elif "jpeg" in header.lower() or "jpg" in header.lower():
                    ext = "jpg"
                else:
                    ext = "jpg"  # Default to jpg
            else:
                ext = "jpg"  # Default if no header
            
            image_bytes = base64.b64decode(image_data)
            
            # Generate unique filename
            filename = f"{uuid.uuid4()}.{ext}"
            image_path = f"uploads/{filename}"
            full_path = UPLOAD_FOLDER / filename
            
            # Save file
            with open(full_path, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            app.logger.error(f"Failed to save image: {e}")
            return jsonify({"error": f"Failed to save image: {str(e)}"}), 400

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO complaints
               (category, severity, description, latitude, longitude, area_name, timestamp, status, image_path, area_importance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category, severity, description, lat_val, lon_val, area_name or None, timestamp, status, image_path, area_importance),
        )
        conn.commit()
        row_id = cur.lastrowid
        
        # Track user complaint if user_id provided
        if user_id:
            try:
                track_complaint_submission(user_id, row_id)
            except Exception as e:
                app.logger.error(f"Failed to track user complaint: {e}")
                # Don't fail the request if tracking fails

    return jsonify({
        "id": row_id,
        "category": category,
        "severity": severity,
        "description": description,
        "latitude": lat_val,
        "longitude": lon_val,
        "area_name": area_name,
        "timestamp": timestamp,
        "status": status,
        "image_path": image_path,
        "area_importance": area_importance
    }), 201


@app.route("/api/complaints", methods=["GET"])
def list_complaints():
    """List complaints with optional filters."""
    category = request.args.get("category")
    severity = request.args.get("severity")
    status = request.args.get("status")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = "SELECT id, category, severity, description, latitude, longitude, area_name, timestamp, status, image_path FROM complaints WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if status:
        query += " AND status = ?"
        params.append(status)
    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    if date_to:
        query += " AND timestamp <= ?"
        params.append(date_to)

    query += " ORDER BY timestamp DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        # Build list while connection is open (Row can fail after conn closes)
        complaints = []
        for r in rows:
            complaints.append({
                "id": r["id"],
                "category": r["category"],
                "severity": r["severity"],
                "description": r["description"] or "",
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "area_name": r["area_name"] or "",
                "timestamp": r["timestamp"],
                "status": r["status"],
                "image_path": r["image_path"] or "",
            })
    return jsonify(complaints)


@app.route("/api/complaints/priority-zones", methods=["GET"])
def priority_zones():
    """Return zones with priority score for map highlighting (top N)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, category, severity, latitude, longitude, area_name, timestamp, status, area_importance
            FROM complaints
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchall()

    # Severity weight (higher = more urgent)
    severity_weight = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    # Area importance weight
    area_importance_weight = {"low": 0.5, "normal": 1, "high": 2, "critical": 3}

    # Round lat/long to ~0.01 deg (~1km) to form "zones"
    from collections import defaultdict
    from datetime import datetime, timezone

    zone_complaints = defaultdict(list)
    for r in rows:
        lat, lon = float(r["latitude"]), float(r["longitude"])
        zone_key = (round(lat, 2), round(lon, 2))
        zone_complaints[zone_key].append({
            "id": r["id"],
            "severity": r["severity"],
            "timestamp": r["timestamp"],
            "status": r["status"],
            "area_importance": r["area_importance"] or "normal"
        })

    zones = []
    for (lat, lon), complaints in zone_complaints.items():
        n = len(complaints)
        max_severity = max(c["severity"] for c in complaints)
        sw = severity_weight.get(max_severity, 1)
        # Area importance factor
        max_area_importance = max(c["area_importance"] for c in complaints)
        aiw = area_importance_weight.get(max_area_importance, 1)
        # Days unresolved: use oldest complaint in zone
        oldest = min(c["timestamp"] for c in complaints)
        try:
            dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = max(0, (now - dt).days)
        except Exception:
            days = 0
        unresolved = sum(1 for c in complaints if c["status"] == "unresolved")
        days_unresolved = days if unresolved else 0

        # Enhanced priority score with area importance
        priority_score = (n * 2) + (sw * 3) + (days_unresolved * 1.5) + (aiw * 2)
        zones.append({
            "latitude": lat,
            "longitude": lon,
            "complaint_count": n,
            "priority_score": round(priority_score, 2),
            "severity": max_severity,
            "area_importance": max_area_importance,
            "days_unresolved": days_unresolved,
        })

    zones.sort(key=lambda z: z["priority_score"], reverse=True)
    top = request.args.get("top", 5, type=int)
    return jsonify(zones[:top])


@app.route("/api/complaints/<int:complaint_id>/resolve", methods=["POST"])
def resolve_complaint(complaint_id):
    """Mark a complaint as resolved (officer only)."""
    data = request.get_json(silent=True) or {}
    officer_id = data.get("officer_id")
    notes = data.get("notes", "")
    
    if not officer_id:
        return jsonify({"error": "officer_id is required"}), 400
    
    # Verify officer exists and has officer role
    user = get_user_by_id(officer_id)
    if not user or user['role'] != 'officer':
        return jsonify({"error": "Unauthorized: Officer access required"}), 403
    
    try:
        log_officer_action(officer_id, complaint_id, "resolved", notes)
        return jsonify({"message": "Complaint marked as resolved"}), 200
    except Exception as e:
        app.logger.error(f"Failed to resolve complaint: {e}")
        return jsonify({"error": "Failed to resolve complaint"}), 500


@app.route("/api/complaints/<int:complaint_id>/unresolve", methods=["POST"])
def unresolve_complaint(complaint_id):
    """Mark a complaint as unresolved (officer only)."""
    data = request.get_json(silent=True) or {}
    officer_id = data.get("officer_id")
    notes = data.get("notes", "")
    
    if not officer_id:
        return jsonify({"error": "officer_id is required"}), 400
    
    # Verify officer exists and has officer role
    user = get_user_by_id(officer_id)
    if not user or user['role'] != 'officer':
        return jsonify({"error": "Unauthorized: Officer access required"}), 403
    
    try:
        log_officer_action(officer_id, complaint_id, "unresolved", notes)
        return jsonify({"message": "Complaint marked as unresolved"}), 200
    except Exception as e:
        app.logger.error(f"Failed to unresolve complaint: {e}")
        return jsonify({"error": "Failed to unresolve complaint"}), 500


@app.route("/api/user/<int:user_id>/complaints", methods=["GET"])
def get_user_complaints_endpoint(user_id):
    """Get all complaints submitted by a user."""
    complaints = get_user_complaints(user_id)
    return jsonify(complaints)


@app.route("/api/user/<int:user_id>/complaints/<int:complaint_id>", methods=["DELETE"])
def delete_user_complaint_endpoint(user_id, complaint_id):
    """Delete a user's complaint."""
    success = delete_user_complaint(user_id, complaint_id)
    if success:
        return jsonify({"message": "Complaint deleted successfully"}), 200
    else:
        return jsonify({"error": "Complaint not found or unauthorized"}), 404


@app.route("/api/officer/<int:officer_id>/actions", methods=["GET"])
def get_officer_actions_endpoint(officer_id):
    """Get all actions performed by an officer."""
    actions = get_officer_actions(officer_id)
    return jsonify(actions)


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Get analytics data for dashboard."""
    with get_db() as conn:
        # Total complaints
        total = conn.execute("SELECT COUNT(*) as count FROM complaints").fetchone()[0]
        
        # Complaints by category
        by_category = conn.execute(
            """SELECT category, COUNT(*) as count FROM complaints 
               GROUP BY category ORDER BY count DESC"""
        ).fetchall()
        
        # Complaints by status
        by_status = conn.execute(
            """SELECT status, COUNT(*) as count FROM complaints 
               GROUP BY status"""
        ).fetchall()
        
        # Complaints by severity
        by_severity = conn.execute(
            """SELECT severity, COUNT(*) as count FROM complaints 
               GROUP BY severity ORDER BY 
               CASE severity 
                 WHEN 'critical' THEN 1
                 WHEN 'high' THEN 2
                 WHEN 'medium' THEN 3
                 WHEN 'low' THEN 4
               END"""
        ).fetchall()
        
        # Recent complaints (last 30 days)
        recent = conn.execute(
            """SELECT DATE(timestamp) as date, COUNT(*) as count 
               FROM complaints 
               WHERE timestamp >= datetime('now', '-30 days')
               GROUP BY DATE(timestamp)
               ORDER BY date"""
        ).fetchall()
        
        return jsonify({
            "total_complaints": total,
            "by_category": [dict(row) for row in by_category],
            "by_status": [dict(row) for row in by_status],
            "by_severity": [dict(row) for row in by_severity],
            "recent_trends": [dict(row) for row in recent]
        })


@app.route("/api/geocode", methods=["POST"])
def geocode_endpoint():
    """Geocode an area name to coordinates."""
    data = request.get_json(silent=True) or {}
    area_name = data.get("area_name", "").strip()
    city = data.get("city", "Chennai")
    
    if not area_name:
        return jsonify({"error": "area_name is required"}), 400
    
    lat, lon = geocode_location(area_name, city)
    
    if lat is not None and lon is not None:
        return jsonify({
            "area_name": area_name,
            "latitude": lat,
            "longitude": lon,
            "status": "success"
        })
    else:
        return jsonify({
            "area_name": area_name,
            "latitude": 13.0827,  # Default Chennai coordinates
            "longitude": 80.2707,
            "status": "default_used",
            "message": "Could not geocode location, using default coordinates"
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting backend at http://127.0.0.1:{port}")
    print("  Health: http://127.0.0.1:{}/api/health".format(port))
    app.run(host="127.0.0.1", port=port, debug=True)
