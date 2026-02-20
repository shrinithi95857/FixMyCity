# FixMyCity - Smart City Complaint Management System

Intelligent city complaint management with heatmap intelligence, clustering, priority scoring, and analytics dashboard.

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the backend (Flask API)

**Important:** Run from inside the `backend` folder:

```bash
cd backend
python app.py
```

You should see: `Starting backend at http://127.0.0.1:5000`

- Open **http://127.0.0.1:5000** in a browser — you should see `{"message": "FixMyCity API", ...}`
- Or check **http://127.0.0.1:5000/api/health** — should return `{"status": "ok"}`

Keep this terminal open. Use a **new** terminal for the frontend.

**If port 5000 is already in use:** set another port, e.g. `set PORT=5001` (Windows) then run `python app.py`. Then in the frontend, set `API_BASE` to `http://127.0.0.1:5001` (or use the sidebar if we add that).

### 3. Start the frontend (Streamlit)

In a **new terminal**:

```bash
cd frontend
streamlit run app.py
```

Opens in the browser (default **http://localhost:8501**).

## What's included

### 🏛️ Core Features

| Feature | Description |
|---------|-------------|
| **User Authentication** | Full registration/login system for citizens and officers |
| **Unified Complaint Form** | Single form with category dropdown + area importance selection |
| **Image Uploads** | Upload photos with complaints (JPG, PNG, WebP supported) |
| **Advanced Database** | SQLite with users, complaints, tracking, and officer actions |

### 🗺️ Intelligence Features

| Feature | Description |
|---------|-------------|
| **Heatmap Intelligence** | Glowing red/yellow areas showing complaint density |
| **Clustering** | DBSCAN algorithm groups nearby complaints into hotspots |
| **Priority Scoring** | Smart urgency scoring: `(count×2) + (severity×3) + (days×1.5) + (importance×2)` |
| **Analytics Dashboard** | Comprehensive insights, trends, and performance metrics |

### 📊 Navigation Pages

| Page | Functionality |
|------|--------------|
| **Dashboard** | Overview with quick stats and recent complaints |
| **File Complaint** | Unified form with dropdown category selection |
| **Heatmap** | Density visualization with clustering intelligence |
| **Priority Zones** | Ranked problem areas with detailed scoring |
| **Data Table** | Filterable complaint list with role-based actions |
| **Analytics** | Performance metrics, trends, and insights |

### 👥 User Roles

| Role | Permissions |
|------|-------------|
| **Citizen** | View all problems, file multiple complaints, delete own complaints |
| **Officer** | View all complaints, mark resolved/unresolved, track actions |

## API Endpoints

### Authentication
- `POST /api/register` — User registration
- `POST /api/login` — User login

### Complaints
- `GET /api/health` — Health check
- `POST /api/complaints` — Submit complaint (with user tracking)
- `GET /api/complaints` — List complaints with filters
- `GET /api/complaints/priority-zones?top=N` — Top priority zones
- `GET /api/uploads/<filename>` — Serve uploaded images

### User Management
- `GET /api/user/<user_id>/complaints` — Get user's complaints
- `DELETE /api/user/<user_id>/complaints/<complaint_id>` — Delete complaint

### Officer Actions
- `POST /api/complaints/<id>/resolve` — Mark complaint resolved
- `POST /api/complaints/<id>/unresolve` — Mark complaint unresolved
- `GET /api/officer/<officer_id>/actions` — Get officer action history

### Analytics
- `GET /api/analytics` — Get dashboard analytics data

## Enhanced Features

- **Clustering**: DBSCAN algorithm for intelligent complaint grouping
- **Area Importance**: Weight factors for schools, hospitals, critical infrastructure
- **Priority Scoring**: Advanced algorithm considering multiple factors
- **Role-based Access**: Different permissions for citizens vs officers
- **Action Tracking**: Complete audit trail of officer actions
- **Real-time Analytics**: Dashboard with performance metrics
