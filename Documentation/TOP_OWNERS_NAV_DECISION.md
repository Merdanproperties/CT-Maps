# Top Owners feature — navigation decision

**Decision:** Global nav shows **Map** and **Top owners** only. No "Search" link.

- Search stays on the map page via the existing search bars (address/town, owner, filters).
- Top Owners is a separate page at `/owners`, reachable from the header.

When implementing the Top Owners plan, the Layout header should include:
- **Map** (links to `/`)
- **Top owners** (links to `/owners`)

Do not add a "Search" link to the nav.
