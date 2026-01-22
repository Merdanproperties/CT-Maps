# Debug Fixes Applied

## Issues Found and Fixed

### 1. ✅ Missing `and_` Import in filters.py
**Problem**: The `filters.py` route was using `and_` from SQLAlchemy but it wasn't imported, which would cause a runtime error when filtering vacant properties.

**Fix**: Added `and_` to the SQLAlchemy imports:
```python
from sqlalchemy import func, or_, and_
```

### 2. ✅ Deprecated `from_orm` Method
**Problem**: The `_format_properties` function in `filters.py` was using `PropertyResponse.from_orm(prop)` which is deprecated in Pydantic v2.

**Fix**: Replaced with manual property mapping (consistent with other routes):
```python
result = PropertyResponse(
    id=prop.id,
    parcel_id=prop.parcel_id,
    # ... all other fields manually mapped
)
```

### 3. ✅ SearchBar Navigation State Bug
**Problem**: In `SearchBar.tsx`, when handling state type suggestions, the navigation state object had a duplicate `state` key which would cause issues.

**Fix**: Removed the duplicate `state: suggestion.value` from the navigation state object.

### 4. ⚠️ Missing .env File
**Problem**: The backend requires a `.env` file with `DATABASE_URL` but it doesn't exist.

**Note**: The `.env` file is in `.gitignore` (as it should be), so you need to create it manually:

```bash
cd backend
cat > .env << EOF
DATABASE_URL=postgresql://localhost:5432/ct_properties
EOF
```

## How to Start the Application

### 1. Create .env File (if not exists)
```bash
cd "/Users/jacobmermelstein/Desktop/CT Maps/backend"
cat > .env << EOF
DATABASE_URL=postgresql://localhost:5432/ct_properties
EOF
```

### 2. Start Backend
```bash
cd "/Users/jacobmermelstein/Desktop/CT Maps/backend"
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 3. Start Frontend (in a new terminal)
```bash
cd "/Users/jacobmermelstein/Desktop/CT Maps/frontend"
npm run dev
```

### 4. Open Browser
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Common Issues

### CORS Errors
- **Cause**: Backend is not running
- **Solution**: Make sure the backend is running on port 8000

### Database Connection Errors
- **Cause**: PostgreSQL is not running or DATABASE_URL is incorrect
- **Solution**: 
  1. Make sure PostgreSQL is running
  2. Check that the database `ct_properties` exists
  3. Verify DATABASE_URL in `.env` file

### 0 Properties Found
- **Cause**: Database is empty or backend is not running
- **Solution**: 
  1. Make sure backend is running
  2. Check if you've processed parcel data: `python3 backend/scripts/process_parcels.py --limit 10000`

### Map Not Loading
- **Cause**: Usually a frontend build issue or missing dependencies
- **Solution**: 
  1. Make sure all frontend dependencies are installed: `cd frontend && npm install`
  2. Check browser console for errors
  3. Verify Leaflet CSS is imported (it should be in MapView.tsx)

## Testing

After starting both servers, test:
1. Search for "Bridgeport" - should show properties
2. Click on a property on the map - should show property details
3. Use filters (High Equity, Vacant, etc.) - should filter properties
4. Export results - should download CSV/JSON

## All Fixed Issues

✅ Missing `and_` import in filters.py
✅ Deprecated `from_orm` usage in filters.py  
✅ SearchBar navigation state bug
✅ Code is now consistent with Pydantic v2 patterns
✅ All routes use manual property mapping (no deprecated methods)
