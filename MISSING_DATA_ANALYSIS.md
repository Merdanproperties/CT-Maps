# Missing Property Data Analysis

## Fields Available in Parcel Layer Geodatabase

Based on inspection of `2025 Parcel Layer.gdb`, the geodatabase contains **13 data columns**:

### ✅ Currently Being Used:
1. **Parcel_ID** → `parcel_id` ✅
2. **Location** → `address` ✅
3. **Town_Name** → `municipality` ✅
4. **Unit_Type** → `property_type` ✅
5. **Shape_Area** → `lot_size_sqft` ✅
6. **CAMA_Link** → Stored in `additional_data.cama_link` ✅

### ❌ Available but NOT Being Stored:
1. **Parcel_Type** - Type of parcel (e.g., "Standard Parcel")
   - 963,679 non-null values (75% of parcels)
   - Could be useful for filtering/classification

2. **Collection_year** - Year data was collected (2025)
   - 1,275,084 non-null values (99.4% of parcels)
   - Useful for data freshness tracking

3. **Edit_Date** - Last edit timestamp
   - 686,727 non-null values (53.5% of parcels)
   - Useful for tracking updates

4. **Editor** - Who edited the parcel
   - 818,069 non-null values (63.8% of parcels)
   - Metadata field

5. **Editor_Comment** - Editor notes
   - 457,366 non-null values (35.7% of parcels)
   - Could contain useful notes about parcels

6. **Link** - Alternative parcel identifier
   - 1,277,404 non-null values (99.6% of parcels)
   - Similar to Parcel_ID but different format

7. **Shape_Length** - Perimeter of parcel
   - 1,282,834 non-null values (100% of parcels)
   - Could be useful for calculations

## ❌ Missing from Geodatabase (Need CAMA Data):

The parcel layer geodatabase **does NOT contain** assessment or owner data. This data is typically in separate CAMA (Computer Assisted Mass Appraisal) files:

### Owner Information:
- ❌ **owner_name** - Property owner name
- ❌ **owner_address** - Owner mailing address
- ❌ **owner_city** - Owner city
- ❌ **owner_state** - Owner state
- ❌ **owner_zip** - Owner zip code

### Assessment Data:
- ❌ **assessed_value** - Total assessed value
- ❌ **land_value** - Land assessment value
- ❌ **building_value** - Building assessment value
- ❌ **total_value** - Total property value
- ❌ **assessment_year** - Year of assessment

### Property Details:
- ❌ **building_area_sqft** - Building square footage
- ❌ **year_built** - Year property was built
- ❌ **bedrooms** - Number of bedrooms
- ❌ **bathrooms** - Number of bathrooms
- ❌ **land_use** - Land use classification
- ❌ **zip_code** - Property zip code

### Sales Data:
- ❌ **last_sale_date** - Date of last sale
- ❌ **last_sale_price** - Price of last sale
- ❌ Sales history (in separate sales files)

## Summary

**From Parcel Layer (Available but not stored):**
- Parcel_Type
- Collection_year
- Edit_Date
- Editor
- Editor_Comment
- Link (alternative ID)
- Shape_Length (perimeter)

**From CAMA Data (Not in parcel layer, need separate files):**
- All owner information
- All assessment values
- Building details (sqft, year built, bedrooms, bathrooms)
- Land use classification
- Zip codes

## Recommendation

1. **Add available fields** from parcel layer to database:
   - `Parcel_Type` → `parcel_type` field
   - `Shape_Length` → `perimeter_ft` field
   - `Collection_year` → `collection_year` field
   - `Link` → Store in `additional_data` as alternative ID

2. **Locate and integrate CAMA data files** to populate:
   - Owner information
   - Assessment values
   - Building characteristics
   - Sales history

3. **Use CAMA_Link** to join parcel data with CAMA data when available.
