# CT Property Search Platform

A Propwire-like property search and lead generation platform for Connecticut properties, built with free and open-source technologies.

## 🎯 Features

- **Interactive Map View** - Browse properties on an interactive map (Leaflet + OpenStreetMap - FREE!)
- **Advanced Search** - Filter by address, owner, municipality, and more
- **Lead Generation Filters**:
  - High equity properties
  - Vacant lots/homes
  - Absentee owners
  - Recently sold properties
  - Low equity properties
- **Property Details** - View comprehensive property information
- **Data Export** - Download filtered property lists as CSV/JSON
- **Analytics Tracking** - Track search patterns and popular filters

## 🚀 Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript
- **Database**: PostgreSQL with PostGIS
- **Maps**: Leaflet + OpenStreetMap (FREE, unlimited!)
- **Data Processing**: Python (GeoPandas, Fiona)

## 📋 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL with PostGIS (or Postgres.app for macOS)

### 1. Install PostgreSQL

**macOS (Recommended):**
- Download [Postgres.app](https://postgresapp.com/)
- Install and launch
- Click "Initialize" to start PostgreSQL

**Or via Homebrew:**
```bash
brew install postgresql postgis
brew services start postgresql
```

### 2. Set Up Database

```bash
# Add Postgres.app to PATH (if using Postgres.app)
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"

# Create database
createdb ct_properties

# Enable PostGIS
psql ct_properties -c "CREATE EXTENSION postgis;"
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://localhost:5432/ct_properties
EOF
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# No API keys needed! Uses free OpenStreetMap
```

### 5. Initialize Database

```bash
cd backend
source venv/bin/activate
python3 scripts/setup_database.py
```

### 6. Process Parcel Data

```bash
# Process sample (10,000 parcels) - recommended first
python3 scripts/process_parcels.py --limit 10000

# Or process all parcels (1.28M - takes 30-60 minutes)
python3 scripts/process_parcels.py
```

### 7. Validate Code (Before Starting Backend)

**Important**: Run this validation script to catch duplicate keyword arguments:

```bash
cd backend
source venv/bin/activate
python scripts/validate_response_constructors.py
```

This will catch `SyntaxError: keyword argument repeated` errors before they cause startup failures.

### 8. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 9. Open in Browser

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Data Sources

- **Connecticut Parcel and CAMA Data 2025** - From data.ct.gov
  - Parcel boundaries (polygon geometries)
  - Basic property info (address, town, property type)
  - CAMA links (for future data joining)

## 🗺️ Maps - FREE & Unlimited!

This platform uses **Leaflet + OpenStreetMap** - completely free with no usage limits!

- ✅ No API keys needed
- ✅ No usage limits
- ✅ No costs
- ✅ Same great functionality

## 📁 Project Structure

```
CT Maps/
├── backend/              # FastAPI backend
│   ├── api/             # API routes
│   ├── scripts/         # Data processing scripts
│   ├── main.py          # FastAPI app
│   └── models.py         # Database models
├── frontend/             # React frontend
│   └── src/
│       ├── pages/       # Page components
│       ├── components/  # Reusable components
│       └── api/         # API client
├── 2025 Parcel Layer.gdb/ # CT parcel data
└── README.md            # This file
```

## 🔧 Scripts

### Inspect Geodatabase
```bash
python3 backend/scripts/inspect_gdb.py
```

### Process Parcels
```bash
# Sample (10K parcels)
python3 backend/scripts/process_parcels.py --limit 10000

# All parcels
python3 backend/scripts/process_parcels.py
```

### View Database (Web Interface)
```bash
python3 backend/scripts/view_data.py
# Open http://localhost:8080
```

## 📝 Database Queries

See `TABLEPLUS_QUERIES.sql` for useful SQL queries you can run in TablePlus or psql.

## 🎨 Features

### Map View
- Interactive map with parcel boundaries
- Click parcels to see details
- Filter by lead types
- Export results

### Search
- Search by address, owner, parcel ID
- Filter by municipality, property type
- Paginated results

### Property Details
- Full property information
- Assessment data (when CAMA data is added)
- Owner information (when CAMA data is added)
- Sales history

## 🔮 Future Enhancements

- Add CAMA data for full property details
- User authentication and saved searches
- Email alerts for new properties
- Draw tool for custom search areas
- Advanced analytics dashboard

## 📞 Troubleshooting

### Backend Won't Start - "Address already in use" (Port 8000)

**Problem**: `ERROR: [Errno 48] Address already in use`

**Solution**: Kill the process using port 8000:
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use this alternative:
kill -9 $(lsof -ti:8000)

# Then start the backend again
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Backend Syntax Error - "keyword argument repeated"

**Problem**: `SyntaxError: keyword argument repeated: owner_phone` (or similar)

**Solution**: 
1. **Run the validation script** to catch this early:
   ```bash
   cd backend
   source venv/bin/activate
   python scripts/validate_response_constructors.py
   ```

2. Check `backend/api/routes/properties.py` and `backend/api/routes/search.py` for duplicate arguments in `PropertyResponse` or `PropertyDetailResponse` constructors. Remove the duplicates.

3. **Root cause fix**: `PropertyDetailResponse` inherits from `PropertyResponse`, so don't redefine fields that already exist in the parent class. The model definition in `properties.py` should NOT redefine `owner_phone` and `owner_email` since they're already in `PropertyResponse`.

**Example fix** (in `properties.py`):
```python
# ❌ WRONG - duplicate owner_phone in constructor
result = PropertyDetailResponse(
    owner_phone=property.owner_phone,
    # ... other fields ...
    owner_phone=property.owner_phone,  # DUPLICATE!
)

# ✅ CORRECT - only one owner_phone
result = PropertyDetailResponse(
    owner_phone=property.owner_phone,
    # ... other fields ...
)
```

**Prevention**: Always run `python scripts/validate_response_constructors.py` before starting the backend to catch these errors early.

### Frontend Connection Timeout Errors

**Problem**: `ERR_CONNECTION_TIMED_OUT` in browser console

**Solution**: 
1. Make sure the backend is running (see "Backend Won't Start" above)
2. Verify backend is accessible: Open http://localhost:8000/docs in your browser
3. Check that backend shows: `INFO: Application startup complete.`
4. Refresh your frontend browser

### Database Connection Issues
- Ensure PostgreSQL is running
- Check DATABASE_URL in `backend/.env`
- Verify user permissions

### Map Not Loading
- No API keys needed! Leaflet uses OpenStreetMap (free)
- Check browser console for errors

### Processing Errors
- Check geodatabase path
- Verify PostGIS is enabled
- Review error messages in console

## 📄 License

Open source - feel free to customize and extend!

## 🙏 Acknowledgments

- Connecticut Office of Policy and Management for parcel data
- OpenStreetMap for free map tiles
- Leaflet for the mapping library
