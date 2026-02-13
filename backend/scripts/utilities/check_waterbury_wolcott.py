"""
Check what Wolcott St addresses exist in the database for Waterbury.
Run from project root: python backend/scripts/utilities/check_waterbury_wolcott.py
Useful to see if we have 64 and/or 66 Wolcott St (same parcel / multi-number issue).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property


def main():
    db = SessionLocal()
    try:
        # All Waterbury properties whose address contains "wolcott"
        props = (
            db.query(Property.id, Property.address, Property.parcel_id, Property.municipality)
            .filter(
                Property.municipality.ilike("%Waterbury%"),
                Property.address.isnot(None),
                Property.address.ilike("%wolcott%"),
            )
            .order_by(Property.address)
            .all()
        )
        print("Waterbury properties with 'Wolcott' in address:")
        print("-" * 80)
        if not props:
            print("(none found)")
            return
        for p in props:
            print(f"  id={p.id}  parcel_id={p.parcel_id}  address={p.address!r}  municipality={p.municipality}")
        # Specifically 64 and 66 Wolcott St
        for num in ("64", "66"):
            exact = (
                db.query(Property.id, Property.address, Property.parcel_id)
                .filter(
                    Property.municipality.ilike("%Waterbury%"),
                    Property.address.ilike(f"{num}%wolcott%"),
                )
                .all()
            )
            print()
            print(f"  '{num} Wolcott' in Waterbury: {len(exact)} match(es)")
            for p in exact:
                print(f"    id={p.id}  parcel_id={p.parcel_id}  address={p.address!r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
