# Search Bar Navigation Fix

## Issue
When typing an address and pressing Enter (or selecting from autocomplete), the map was not moving/zooming to the selected parcel.

## Root Cause
The `TopFilterBar` component was passing an empty `onSelect` callback to `SearchBar`:
```tsx
<SearchBar 
  onSelect={(suggestion) => {
    // Empty callback - this was the problem!
  }}
  onQueryChange={onSearchChange}
/>
```

When `onSelect` is provided to `SearchBar`, it calls that callback instead of using its default navigation behavior. Since the callback was empty, nothing happened when addresses were selected.

## Fix
**Removed the `onSelect` prop from `TopFilterBar`** so `SearchBar` uses its default navigation behavior:

```tsx
<SearchBar 
  placeholder="Address, city, county, state" 
  onQueryChange={onSearchChange}
/>
```

## How It Works Now
1. User types address or selects from autocomplete
2. `SearchBar`'s `handleSelect` is called
3. Since `onSelect` is not provided, it uses default behavior:
   - Creates navigation state with center coordinates and zoom level
   - Navigates to map view with location state
4. `MapView` receives location state and:
   - Sets map center and zoom
   - Searches for the address property
   - Centers map on property geometry
5. Map moves and zooms to the selected address ✅

## Important Notes
- **DO NOT** pass an empty `onSelect` callback to `SearchBar` - it will block navigation
- If you need custom behavior, implement the full navigation logic in the `onSelect` callback
- The default behavior handles address, town, and state suggestions with appropriate zoom levels

## Files Changed
- `frontend/src/components/TopFilterBar.tsx` - Removed empty `onSelect` prop

## Date Fixed
January 2025
