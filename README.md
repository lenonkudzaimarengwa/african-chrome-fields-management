# African Chrome Fields Management System

## Overview
A complete offline-first management system for African Chrome Fields mining operations. Works seamlessly on **desktops (office)** and **tablets (field workers)** with automatic cloud synchronization.

---

## 📋 What This System Tracks

### 1. **Logistics & Fleet**
   - Chrome ore extraction logs
   - Haulage truck load tracking
   - Fuel consumption per vehicle
   - Weighbridge ticket data

### 2. **Operations & Field Inspections**
   - Equipment status checklists
   - Safety audit reports
   - Machinery maintenance logs
   - Daily field activity reports

### 3. **Inventory & Spares**
   - Heavy equipment spare parts tracking
   - Processing plant inputs/outputs
   - Stock level management
   - Equipment repair history

### 4. **HR & Workforce**
   - Shift logs and clock-in/clock-out
   - Geofenced team locations
   - Worker attendance
   - Incident reports

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│     TABLET/DESKTOP BROWSER              │
│  ├─ Vue.js / React UI (Responsive)      │
│  ├─ PouchDB (Local Database)            │
│  └─ Service Workers (Offline Cache)     │
└──────────────┬──────────────────────────┘
               │
        [Automatic HTTPS Sync]
               │
┌──────────────▼──────────────────────────┐
│   PYTHON BACKEND (FastAPI)              │
│  ├─ REST API Endpoints                  │
│  ├─ Conflict Resolution                 │
│  └─ Business Logic Processing           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  POSTGRESQL DATABASE (Cloud)            │
│  ├─ Single Source of Truth              │
│  ├─ Automated Backups                   │
│  └─ Real-time Analytics                 │
└─────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Vue.js / Tailwind CSS | Responsive UI for tablets & desktops |
| **Local DB** | PouchDB (JavaScript) | Browser-based offline storage |
| **Backend** | FastAPI (Python) | High-performance API server |
| **ORM** | SQLAlchemy | Python-to-PostgreSQL mapping |
| **Database** | PostgreSQL | Cloud database (single source of truth) |
| **Hosting** | Render / Railway (Backend) | Python backend deployment |
| **Hosting** | Vercel / Netlify (Frontend) | Static site deployment |
| **Sync Engine** | Custom FastAPI endpoints | Handles offline→online data merge |

---

## 📁 Project Structure

```
african-chrome-fields-management/
│
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── models.py           # SQLAlchemy database models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── database.py         # PostgreSQL connection setup
│   │   ├── sync.py             # Offline sync logic
│   │   └── routes/
│   │       ├── fleet.py        # Fleet management endpoints
│   │       ├── inventory.py    # Inventory endpoints
│   │       ├── operations.py   # Operations endpoints
│   │       ├── hr.py           # HR & workforce endpoints
│   │       └── sync.py         # Sync endpoint
│   │
│   ├── tests/                  # Pytest unit tests
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── Dockerfile              # Container setup
│
├── frontend/                   # Vue.js + Tailwind frontend
│   ├── src/
│   │   ├── components/         # Vue components
│   │   ├── pages/              # Page layouts
│   │   ├── db/                 # PouchDB sync logic
│   │   ├── App.vue             # Main app component
│   │   └── main.js             # Entry point
│   │
│   ├── public/                 # Static assets
│   ├── package.json            # Node dependencies
│   └── vite.config.js          # Build config
│
├── docker-compose.yml          # Local dev database
└── deployment/                 # Deployment configs
    ├── render.yaml             # Render.com backend config
    └── vercel.json             # Vercel frontend config
```

---

## 🚀 Getting Started (3 Steps)

### Step 1: Clone & Install (5 minutes)
```bash
git clone https://github.com/lenonkudzaimarengwa/african-chrome-fields-management.git
cd african-chrome-fields-management

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env

# Frontend setup
cd ../frontend
npm install
```

### Step 2: Start Local Development (2 minutes)
```bash
# Terminal 1: Start PostgreSQL (local)
docker-compose up

# Terminal 2: Start FastAPI backend
cd backend
uvicorn app.main:app --reload

# Terminal 3: Start Vue frontend
cd frontend
npm run dev
```

### Step 3: Access the App
- **Frontend**: `http://localhost:5173`
- **API Docs**: `http://localhost:8000/docs`
- **Database**: `localhost:5432`

---

## 📚 Learning Path (For You)

1. **Week 1**: Backend API models & database schema
2. **Week 2**: CRUD endpoints for each module
3. **Week 3**: Frontend UI with Vue.js
4. **Week 4**: Offline sync engine (PouchDB)
5. **Week 5**: Testing & bug fixes
6. **Week 6**: Deployment to cloud

---

## 🔐 Security Features

- ✅ Field-level encryption for sensitive data (truck GPS, worker IDs)
- ✅ Role-based access control (Manager, Supervisor, Field Worker)
- ✅ Audit logs for all modifications
- ✅ Automatic session timeout on tablets
- ✅ Data validation on both frontend and backend

---

## 📞 Support & Next Steps

This README will be updated as we build each phase.

**Current Status**: Phase 1 - Project Structure Setup ⏳
