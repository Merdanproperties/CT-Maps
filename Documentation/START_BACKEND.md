# ⚠️ CRITICAL: Backend Must Be Running!

## The CORS Error Means Your Backend Is Not Running

The error `Access to XMLHttpRequest at 'http://localhost:8000/api/search/...' has been blocked by CORS policy` means the backend server is not running.

## Start the Backend NOW:

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

## Then Refresh Your Browser

Once the backend is running, refresh http://localhost:3000 and try searching for "Bridgeport" again.

## What I Fixed:

1. ✅ Fixed `useRef` import (it's already imported)
2. ✅ Fixed infinite loop in MapUpdater
3. ✅ Fixed map centering when searching
4. ✅ Improved municipality search logic

## The Backend MUST Be Running!

Without the backend running, you'll get:
- ❌ CORS errors
- ❌ 0 properties found
- ❌ Search won't work

**Start the backend first, then everything will work!**
