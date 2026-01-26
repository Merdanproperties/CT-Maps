"""
Match geocoded addresses to nearest geodatabase parcels using spatial proximity
Finds the closest parcel in the geodatabase for each geocoded Excel address
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"
MUNICIPALITY = "Torrington"
MAX_DISTANCE_METERS = 200.0  # Maximum distance to consider a match (increased from 50m)

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_parcel_centroid(geometry, source_crs='EPSG:6434') -> Optional[Tuple[float, float]]:
    """Get centroid of a parcel geometry in WGS84"""
    try:
        if geometry is None:
            return None
        
        # Create GeoSeries with source CRS
        from geopandas import GeoSeries
        geom_series = GeoSeries([geometry], crs=source_crs)
        
        # Convert to WGS84
        geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
        
        centroid = geom_wgs84.centroid
        return (centroid.x, centroid.y)  # lon, lat
    except Exception as e:
        return None

def load_geodatabase_parcels() -> gpd.GeoDataFrame:
    """Load Torrington parcels from geodatabase"""
    print("Loading geodatabase parcels...")
    
    gdf = gpd.read_file(GDB_PATH, layer='Full_State_Parcels_25', driver='FileGDB')
    torrington_gdf = gdf[gdf['Town_Name'].str.contains(MUNICIPALITY, case=False, na=False)]
    
    print(f"  Loaded {len(torrington_gdf):,} Torrington parcels from geodatabase")
    
    # Get source CRS
    source_crs = torrington_gdf.crs or 'EPSG:6434'
    print(f"  Source CRS: {source_crs}")
    
    # Calculate centroids for all parcels
    print("  Calculating parcel centroids (converting to WGS84)...")
    centroids = []
    for idx, row in torrington_gdf.iterrows():
        centroid = get_parcel_centroid(row.geometry, source_crs)
        centroids.append(centroid)
    
    torrington_gdf = torrington_gdf.copy()  # Avoid SettingWithCopyWarning
    torrington_gdf['centroid'] = centroids
    
    # Filter out parcels without centroids
    valid_parcels = torrington_gdf[torrington_gdf['centroid'].notna()]
    print(f"  {len(valid_parcels):,} parcels with valid centroids")
    
    return valid_parcels

def find_nearest_parcel(
    lon: float,
    lat: float,
    geodatabase_parcels: gpd.GeoDataFrame,
    max_distance: float = MAX_DISTANCE_METERS
) -> Optional[Dict]:
    """
    Find nearest parcel in geodatabase to given coordinates
    Returns dict with parcel info and distance, or None if no parcel within threshold
    """
    min_distance = float('inf')
    nearest_parcel = None
    
    for idx, row in geodatabase_parcels.iterrows():
        centroid = row['centroid']
        if centroid is None:
            continue
        
        parcel_lon, parcel_lat = centroid
        distance = haversine_distance(lon, lat, parcel_lon, parcel_lat)
        
        if distance < min_distance:
            min_distance = distance
            nearest_parcel = {
                'index': idx,
                'parcel_id': row.get('Parcel_ID', ''),
                'geometry': row.geometry,
                'distance_meters': distance
            }
    
    # Check if within threshold - but also return if we found something (even if over threshold)
    # We'll log it separately
    if nearest_parcel:
        if nearest_parcel['distance_meters'] <= max_distance:
            return nearest_parcel
        else:
            # Return it anyway but mark it as over threshold
            nearest_parcel['over_threshold'] = True
            return nearest_parcel
    
    return None

def match_geocoded_to_geodatabase(
    geocoded_records: List[Dict],
    geodatabase_parcels: gpd.GeoDataFrame
) -> List[Dict]:
    """
    Match geocoded Excel addresses to nearest geodatabase parcels
    Returns list of matched records with parcel info
    """
    print("\nMatching geocoded addresses to geodatabase parcels...")
    
    matched = []
    matched_over_threshold = []
    unmatched = []
    
    for i, record in enumerate(geocoded_records, 1):
        if not record.get('geocoded') or 'lon' not in record or 'lat' not in record:
            unmatched.append(record)
            continue
        
        lon = record['lon']
        lat = record['lat']
        
        nearest = find_nearest_parcel(lon, lat, geodatabase_parcels)
        
        if nearest:
            record['matched_parcel_id'] = nearest['parcel_id']
            record['matched_distance'] = nearest['distance_meters']
            record['matched_geometry'] = nearest['geometry']
            if nearest.get('over_threshold'):
                matched_over_threshold.append(record)
            else:
                matched.append(record)
        else:
            record['matched_parcel_id'] = None
            record['matched_distance'] = None
            record['matched_geometry'] = None
            unmatched.append(record)
        
        if i % 100 == 0:
            print(f"  Progress: {i:,}/{len(geocoded_records):,} | Matched: {len(matched):,} | Over threshold: {len(matched_over_threshold):,} | Unmatched: {len(unmatched):,}")
    
    print(f"\n📊 Matching Summary:")
    print(f"  ✅ Matched (within {MAX_DISTANCE_METERS}m): {len(matched):,}")
    print(f"  ⚠️  Matched (over {MAX_DISTANCE_METERS}m threshold): {len(matched_over_threshold):,}")
    print(f"  ❌ Unmatched: {len(unmatched):,}")
    
    # Show distance statistics for matched
    all_matched = matched + matched_over_threshold
    if all_matched:
        distances = [r['matched_distance'] for r in all_matched]
        avg_distance = sum(distances) / len(distances)
        max_distance = max(distances)
        min_distance = min(distances)
        print(f"  📏 Distance stats for all matches:")
        print(f"    Min: {min_distance:.2f}m")
        print(f"    Avg: {avg_distance:.2f}m")
        print(f"    Max: {max_distance:.2f}m")
    
    # Show sample over threshold
    if matched_over_threshold:
        print(f"\n⚠️  Sample Over Threshold (first 10):")
        for record in matched_over_threshold[:10]:
            print(f"    {record.get('address', 'No address')}: {record['matched_distance']:.2f}m")
    
    # Show sample unmatched
    if unmatched:
        print(f"\n⚠️  Sample Unmatched (first 10):")
        for record in unmatched[:10]:
            print(f"    {record.get('address', 'No address')}")
    
    # Return all matches (including over threshold)
    return all_matched

def main():
    """Main function"""
    import json
    
    print("\n" + "=" * 60)
    print("Matching Geocoded Addresses to Geodatabase Parcels")
    print("=" * 60)
    
    # Load geocoded records (from previous step)
    geocoded_file = "logs/geocoded_unmatched.json"
    try:
        with open(geocoded_file, 'r') as f:
            geocoded_records = json.load(f)
        print(f"\nLoaded {len(geocoded_records):,} geocoded records")
    except FileNotFoundError:
        print(f"\n⚠️  Geocoded records file not found: {geocoded_file}")
        print("   Run geocode_unmatched_addresses.py first")
        return []
    
    # Load geodatabase parcels
    print("\nStep 1: Loading geodatabase parcels...")
    geodatabase_parcels = load_geodatabase_parcels()
    
    # Match geocoded addresses to parcels
    print("\nStep 2: Matching geocoded addresses to parcels...")
    matched = match_geocoded_to_geodatabase(geocoded_records, geodatabase_parcels)
    
    # Save matched records
    output_file = "logs/matched_to_geodatabase.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Convert geometry to WGS84 WKT for JSON serialization
    matched_serializable = []
    source_crs = geodatabase_parcels.crs or 'EPSG:6434'
    
    for record in matched:
        rec = record.copy()
        if 'matched_geometry' in rec and rec['matched_geometry'] is not None:
            # Convert geometry to WGS84 WKT
            try:
                from geopandas import GeoSeries
                geom = rec['matched_geometry']
                geom_series = GeoSeries([geom], crs=source_crs)
                geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
                # Ensure 2D
                from shapely import wkt
                geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
                rec['matched_geometry_wkt'] = geom_2d.wkt
            except Exception as e:
                print(f"      ⚠️  Geometry conversion error for {rec.get('address', 'unknown')}: {e}")
                rec['matched_geometry_wkt'] = None
            # Remove geometry object (not JSON serializable)
            del rec['matched_geometry']
        matched_serializable.append(rec)
    
    with open(output_file, 'w') as f:
        json.dump(matched_serializable, f, indent=2)
    
    print(f"\n✅ Saved {len(matched):,} matched records to {output_file}")
    
    return matched

if __name__ == "__main__":
    matched = main()
    print("\n✅ Spatial matching complete!")
    if matched:
        print(f"   Matched {len(matched):,} addresses to geodatabase parcels")
