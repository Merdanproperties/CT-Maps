# Reference: Map View & Sidebar Fixes (Jan 2026)

This document records the fixes made to resolve sidebar layout issues, whitespace below the map, and map resize behavior (including when opening DevTools with F12). Use it as a reference when similar issues appear or when changing layout/CSS.

---

## 1. Sidebar Empty State Whitespace

**Problem:** The right sidebar showed "No properties found" in a small centered block with a large blank white area below it.

**Cause:** The empty-state container (`.property-list-empty`) did not grow to fill the sidebar content area; it only took the height of its content.

**Fix (MapView.css):**

- For `.property-list-loading`, `.property-list-empty`, and `.property-list-error`:
  - Added `flex: 1` and `min-height: 0` so they fill the content area and the message stays centered in the full panel.

```css
.property-list-loading,
.property-list-empty,
.property-list-error {
  /* ... existing ... */
  flex: 1;
  min-height: 0;
}
```

---

## 2. Sidebar Header Overlap (Property Card Over Export / “Show 1 - 1 of 1 Results”)

**Problem:** The property card content (phone/email N/A, “Absentee Owners” button) overlapped the sidebar header (“Show 1 - 1 of 1 Results”, Export, close).

**Cause:**

- `.property-list-header` used `position: sticky` with a viewport-based `top`, so it could sit in the wrong place relative to the sidebar.
- `.property-list-content` had no `min-height: 0`, so the flex child didn’t shrink and the scroll region didn’t stay below the header.
- `.property-list-scroll` also needed `min-height: 0` so the scroll container gets a defined height.

**Fix (MapView.css):**

- **`.property-list-header`:** Removed `position: sticky` and `top`; set `position: relative` so the header stays at the top of the sidebar.
- **`.property-list-content`:** Added `min-height: 0` so it can shrink and leave room for the header; only the scroll area scrolls.
- **`.property-list-scroll`:** Added `min-height: 0` so the scroll container gets the remaining height and scrolls correctly.

---

## 3. Results Populating as User Types in the Three Search Bars

**Expected behavior:** Typing in any of the three search bars (Address/town, Search by owner, Enter mailing address) should open the sidebar and show results (or “No properties found”) as the user types.

**How it works (no structural change needed):**

- **Address or town** and **Search by owner:** Both use `SearchBar` with `onQueryChange={onSearchChange}`. MapView’s `onSearchChange` sets `searchQuery`, `showPropertyList(true)`, `sidebarCollapsed(false)`, and clears other filters. `usePropertyQuery` runs with `q=searchQuery`; the backend search matches address, owner name, and owner address.
- **Enter mailing address:** Uses `FilterDropdown` with `isTextInput`; `onSelect` calls `handleFilterChange('ownerAddress', value)`. MapView sets `searchQuery`, `filterParams.owner_address`, `showPropertyList(true)`, and `sidebarCollapsed(false)`. The query runs via `hasCustomFilters` with `owner_address`.

Ensure `onSearchChange` and `handleFilterChange('ownerAddress', …)` are wired as above so all three bars open the sidebar and trigger the property query.

### 3.1 All Three Search Chips Returning Correct Sidebar Results (Feb 2026)

**Problem:** When all three chips were active (Address/Town, Owner, Owner Address), the sidebar showed "No properties found" even when a matching property existed (e.g. 14 PEARL ST, GARCIA JOSE, PO BOX 461).

**Cause:** The frontend sent a single combined `q` (e.g. `"14 PEARL ST GARCIA JOSE"`). The backend matched that entire string against each field; no single column contains that concatenation, so no rows matched.

**Fix:**

- **Backend (`backend/api/routes/search.py`):** The search endpoint now supports **multiple terms** in `q` when separated by a **pipe** (`|`). For each term it applies the same OR-across-fields logic (address, owner_name, owner_address, etc.). Terms are **AND**ed: a row must match every term (each in at least one field). Example: `q=14 PEARL ST|GARCIA JOSE` returns rows where (address/owner/… matches "14 PEARL ST") **and** (matches "GARCIA JOSE").
- **Frontend (`frontend/src/pages/MapView.tsx`):** When both "Address or town" and "Search by owner" have values, `effectiveSearchQuery` joins them with `|` instead of a space, so the API receives pipe-separated terms. The "Owner Address" chip continues to use the existing `owner_address` filter.

**Result:** With all three chips set, the sidebar shows the correct matching properties (e.g. 14 Pearl St, owner Garcia Jose, PO Box 461). Do not change the pipe delimiter or the backend AND logic without updating both sides.

---

## 4. White Space Below the Map (Including After F12 / DevTools)

**Problem:** A large white area appeared below the map, especially noticeable when opening the browser console (F12). The map did not fill the viewport.

**Cause:** Multiple layout issues:

- **Layout chain:** `.main-content` did not use `min-height: 0` or a flex column, so the flex chain from `#root` down did not reliably give the map a height.
- **Map view height:** `.map-view` used `height: 100vh` instead of filling its parent, so it didn’t participate in the flex layout.
- **Map container:** `.map-container-wrapper` had no `flex: 1` or `min-height: 0`, so in a column layout it didn’t take the remaining space.
- **Grid with sidebar:** With one row (`1fr`), the filter bar and map/sidebar shared the same row; the map needed its own row with `1fr` height.

**Fixes applied:**

### 4.1 Layout (Layout.css)

- **`.main-content`:** Added `min-height: 0`, `display: flex`, `flex-direction: column` so it fills the layout and passes height down to the map view.

### 4.2 Map view and grid (MapView.css)

- **`.map-view`:** Changed `height: 100vh` to `height: 100%`; added `min-height: 0` and `flex-direction: column` so it fills `.main-content` and lays out filter bar + map in a column.
- **`.map-view.with-sidebar`:** Set `grid-template-rows: auto 1fr` (and `min-height: 0`) so the first row is the filter bar and the second row gets the remaining height. Added rules so:
  - The filter bar (`.top-filter-bar`) spans the first row: `grid-column: 1 / -1`.
  - The map (`.map-container-wrapper`) is in row 2, column 1: `grid-row: 2; grid-column: 1`.
  - The sidebar (`.property-list-sidebar`) is in row 2, column 2: `grid-row: 2; grid-column: 2`.
- **`.map-container-wrapper`:** Added `min-height: 0` and `flex: 1` so the map area takes the remaining space in both flex and grid layouts.

**What we did not do:** Using `100dvh` or Visual Viewport–based height for the map view caused the map to shrink (and sometimes keep shrinking); those changes were reverted. The fix was to use a proper flex/grid chain with `height: 100%` and `min-height: 0`, not viewport units or JS-driven height for the map view.

---

## 5. Map Resize on Viewport / Container Change (F12, Window Resize)

**Problem:** When the viewport or container size changed (e.g. opening DevTools with F12 or resizing the window), the map canvas did not recalculate, leaving a blank/white area under the map.

**Cause:** Leaflet and Mapbox GL do not automatically recalculate size when the container or window resizes; they need an explicit call (`invalidateSize()` for Leaflet, `resize()` for Mapbox).

**Fixes:**

### 5.1 Leaflet (LeafletMap.tsx – MapResizeHandler)

- **ResizeObserver:** Already present on the map container; on size change it calls `map.invalidateSize()` (via `setTimeout(..., 0)`).
- **Window resize:** Added `window.addEventListener('resize', ...)` that also calls `map.invalidateSize()` so the map updates when the window is resized (and when F12 triggers a resize in browsers that fire it).

### 5.2 Mapbox (MapboxMap.tsx)

- **ResizeObserver:** Added a `ResizeObserver` on the map wrapper div (using `wrapperRef`) that calls `mapInstance.resize()` when the container size changes.
- **Window resize:** Added `window.addEventListener('resize', ...)` that calls `mapInstance.resize()`.
- **Ref:** Set `ref={wrapperRef}` on the `map-container-wrapper` div so the ResizeObserver has a DOM node to observe.

**Note:** In Chrome, opening/closing F12 often does **not** fire `window.resize`. The main fix for “white space after F12” is the layout chain (Section 4) so the map container has a correct height. The resize handlers ensure the map redraws when the container or window size does change.

---

## 6. Files Touched (Summary)

| File | Changes |
|------|--------|
| **frontend/src/pages/MapView.css** | Sidebar empty/loading/error flex; header relative + content/scroll min-height; map-view height 100% + flex column; with-sidebar grid rows + placement; map-container-wrapper flex + min-height. |
| **frontend/src/pages/MapView.tsx** | (Section 3.1) effectiveSearchQuery joins address + owner with `\|` for multi-term search. |
| **backend/api/routes/search.py** | (Section 3.1) Text search: split `q` by `\|`, apply AND across terms (each term OR across fields). |
| **frontend/src/components/Layout.css** | main-content min-height: 0, display flex, flex-direction column. |
| **frontend/src/components/map/LeafletMap.tsx** | MapResizeHandler: window resize listener in addition to ResizeObserver. |
| **frontend/src/components/map/MapboxMap.tsx** | ResizeObserver on wrapper + window resize calling mapInstance.resize(); ref on map-container-wrapper. |

---

## 7. Debug Instrumentation (Optional)

During debugging, instrumentation was added in MapView and usePropertyQuery (e.g. fetch to an ingest URL, sidebar/search state logs). These can be removed or kept behind a flag; see the debug-mode instructions in the project for details. They are not required for the fixes above.

---

## 8. Quick Reference: Flex + Map Gotcha

When the map lives in a flex (or grid) layout:

- **Parent of the map container** must have `min-height: 0` (and typically `flex: 1`) so the flex item can shrink and the map container gets a defined height.
- **Map container** should have `flex: 1` and `min-height: 0` when it is a flex child that should fill remaining space.
- **After any container or window size change,** call Leaflet’s `map.invalidateSize()` or Mapbox’s `map.resize()` (via ResizeObserver and/or window `resize` listener).

This avoids “map not filling” and “whitespace below map” issues.
