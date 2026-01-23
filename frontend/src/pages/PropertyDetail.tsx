import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { propertyApi } from '../api/client'
import { useSafeProperty } from '../hooks/useSafeProperty'
import PropertyImageGallery from '../components/PropertyImageGallery'
import {
  ArrowLeft,
  MapPin,
  User,
  DollarSign,
  Calendar,
  Home,
  Phone,
  Mail,
  Building,
  Landmark,
  Layers,
  Thermometer,
  Wind,
  Flame,
  Car,
} from 'lucide-react'
import './PropertyDetail.css'

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: property, isLoading, error } = useQuery({
    queryKey: ['property', id],
    queryFn: () => propertyApi.getProperty(parseInt(id!)),
    enabled: !!id,
  })

  // Use safe property hook for type-safe access
  // Always call the hook (Rules of Hooks) - pass empty object if property is null
  const safeProperty = useSafeProperty(property || {} as any)

  const formatCurrency = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return 'N/A'
    }
  }

  const formatNumber = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return 'N/A'
    return Number(value).toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="property-detail">
        <div className="loading">
          <div className="spinner" />
          <p>Loading property details...</p>
        </div>
      </div>
    )
  }

  if (error || !property) {
    return (
      <div className="property-detail">
        <div className="error">
          <p>Property not found</p>
          <button onClick={() => navigate('/')}>Back to Map</button>
        </div>
      </div>
    )
  }

  // Use safe getter for all property access
  const getSafe = safeProperty.getSafe

  return (
    <div className="property-detail">
      <div className="detail-container">
        <button className="back-button" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
          Back
        </button>

        {/* Header with Address */}
        <div className="detail-header">
          <h1>{getSafe('address', 'No Address')}</h1>
          {getSafe('municipality') && (
            <div className="location">
              <MapPin size={18} />
              <span>
                {getSafe('municipality')}, CT {getSafe('zip_code', '')}
              </span>
            </div>
          )}
        </div>

        {/* Image Gallery */}
        <PropertyImageGallery
          address={getSafe('address')}
          city={getSafe('city')}
          parcelId={getSafe('parcel_id')}
          images={getSafe('images')}
        />

        {/* Main Content Grid */}
        <div className="detail-grid">
          {/* Property Characteristics */}
          <div className="detail-section">
            <h2>
              <Home size={20} />
              Property Characteristics
            </h2>
            <div className="info-grid">
              <div className="info-item">
                <span className="label">Parcel ID</span>
                <span className="value">{getSafe('parcel_id', 'N/A')}</span>
              </div>
              {getSafe('property_type') && (
                <div className="info-item">
                  <span className="label">Property Type</span>
                  <span className="value">{getSafe('property_type')}</span>
                </div>
              )}
              {getSafe('land_use') && (
                <div className="info-item">
                  <span className="label">Land Use</span>
                  <span className="value">{getSafe('land_use')}</span>
                </div>
              )}
              {getSafe('year_built') && (
                <div className="info-item">
                  <span className="label">Year Built</span>
                  <span className="value">{getSafe('year_built')}</span>
                </div>
              )}
              {getSafe('stories') && (
                <div className="info-item">
                  <span className="label">Stories</span>
                  <span className="value">{getSafe('stories')}</span>
                </div>
              )}
              {getSafe('total_rooms') && (
                <div className="info-item">
                  <span className="label">Total Rooms</span>
                  <span className="value">{getSafe('total_rooms')}</span>
                </div>
              )}
              {getSafe('bedrooms') && (
                <div className="info-item">
                  <span className="label">Bedrooms</span>
                  <span className="value">{getSafe('bedrooms')}</span>
                </div>
              )}
              {getSafe('bathrooms') && (
                <div className="info-item">
                  <span className="label">Bathrooms</span>
                  <span className="value">{getSafe('bathrooms')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Land Information */}
          <div className="detail-section">
            <h2>
              <Layers size={20} />
              Land Information
            </h2>
            <div className="info-grid">
              {getSafe('lot_size_sqft') && (
                <div className="info-item">
                  <span className="label">Lot Size</span>
                  <span className="value">{formatNumber(getSafe('lot_size_sqft'))} sq ft</span>
                </div>
              )}
              {getSafe('land_value') && (
                <div className="info-item">
                  <span className="label">Land Value</span>
                  <span className="value">{formatCurrency(getSafe('land_value'))}</span>
                </div>
              )}
              {getSafe('land_use') && (
                <div className="info-item">
                  <span className="label">Land Use Classification</span>
                  <span className="value">{getSafe('land_use')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Tax Information */}
          <div className="detail-section">
            <h2>
              <Landmark size={20} />
              Tax Information
            </h2>
            <div className="info-grid">
              {getSafe('tax_amount') != null && (
                <div className="info-item">
                  <span className="label">Annual Tax Amount</span>
                  <span className="value highlight">{formatCurrency(getSafe('tax_amount'))}</span>
                </div>
              )}
              {getSafe('tax_year') && (
                <div className="info-item">
                  <span className="label">Tax Year</span>
                  <span className="value">{getSafe('tax_year')}</span>
                </div>
              )}
              {getSafe('assessment_year') && (
                <div className="info-item">
                  <span className="label">Assessment Year</span>
                  <span className="value">{getSafe('assessment_year')}</span>
                </div>
              )}
              {getSafe('tax_exemptions') && (
                <div className="info-item">
                  <span className="label">Tax Exemptions</span>
                  <span className="value">{getSafe('tax_exemptions')}</span>
                </div>
              )}
              {getSafe('assessed_value') != null && (
                <div className="info-item">
                  <span className="label">Assessed Value</span>
                  <span className="value">{formatCurrency(getSafe('assessed_value'))}</span>
                </div>
              )}
            </div>
          </div>

          {/* Assessment & Value */}
          <div className="detail-section">
            <h2>
              <DollarSign size={20} />
              Assessment & Value
            </h2>
            <div className="info-grid">
              {getSafe('assessed_value') != null && (
                <div className="info-item">
                  <span className="label">Assessed Value</span>
                  <span className="value highlight">{formatCurrency(getSafe('assessed_value'))}</span>
                </div>
              )}
              {getSafe('land_value') != null && (
                <div className="info-item">
                  <span className="label">Land Value</span>
                  <span className="value">{formatCurrency(getSafe('land_value'))}</span>
                </div>
              )}
              {getSafe('building_value') != null && (
                <div className="info-item">
                  <span className="label">Building Value</span>
                  <span className="value">{formatCurrency(getSafe('building_value'))}</span>
                </div>
              )}
              {getSafe('equity_estimate') != null && (
                <div className="info-item">
                  <span className="label">Estimated Equity</span>
                  <span className="value highlight">{formatCurrency(getSafe('equity_estimate'))}</span>
                </div>
              )}
            </div>
          </div>

          {/* Building Details */}
          <div className="detail-section">
            <h2>
              <Building size={20} />
              Building Details
            </h2>
            <div className="info-grid">
              {getSafe('building_area_sqft') != null && (
                <div className="info-item">
                  <span className="label">Building Area</span>
                  <span className="value">{formatNumber(getSafe('building_area_sqft'))} sq ft</span>
                </div>
              )}
              {getSafe('year_built') && (
                <div className="info-item">
                  <span className="label">Year Built</span>
                  <span className="value">{getSafe('year_built')}</span>
                </div>
              )}
              {getSafe('stories') && (
                <div className="info-item">
                  <span className="label">Stories</span>
                  <span className="value">{getSafe('stories')}</span>
                </div>
              )}
              {getSafe('bedrooms') && (
                <div className="info-item">
                  <span className="label">Bedrooms</span>
                  <span className="value">{getSafe('bedrooms')}</span>
                </div>
              )}
              {getSafe('bathrooms') && (
                <div className="info-item">
                  <span className="label">Bathrooms</span>
                  <span className="value">{getSafe('bathrooms')}</span>
                </div>
              )}
              {getSafe('total_rooms') && (
                <div className="info-item">
                  <span className="label">Total Rooms</span>
                  <span className="value">{getSafe('total_rooms')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Building Exterior Details */}
          <div className="detail-section">
            <h2>
              <Building size={20} />
              Building Exterior Details
            </h2>
            <div className="info-grid">
              {getSafe('exterior_walls') && (
                <div className="info-item">
                  <span className="label">Exterior Walls</span>
                  <span className="value">{getSafe('exterior_walls')}</span>
                </div>
              )}
              {getSafe('roof_type') && (
                <div className="info-item">
                  <span className="label">Roof Type</span>
                  <span className="value">{getSafe('roof_type')}</span>
                </div>
              )}
              {getSafe('roof_material') && (
                <div className="info-item">
                  <span className="label">Roof Material</span>
                  <span className="value">{getSafe('roof_material')}</span>
                </div>
              )}
              {getSafe('foundation_type') && (
                <div className="info-item">
                  <span className="label">Foundation Type</span>
                  <span className="value">{getSafe('foundation_type')}</span>
                </div>
              )}
              {getSafe('exterior_finish') && (
                <div className="info-item">
                  <span className="label">Exterior Finish</span>
                  <span className="value">{getSafe('exterior_finish')}</span>
                </div>
              )}
              {getSafe('garage_type') && (
                <div className="info-item">
                  <span className="label">Garage Type</span>
                  <span className="value">{getSafe('garage_type')}</span>
                </div>
              )}
              {getSafe('garage_spaces') != null && (
                <div className="info-item">
                  <span className="label">Garage Spaces</span>
                  <span className="value">{getSafe('garage_spaces')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Building Interior Details */}
          <div className="detail-section">
            <h2>
              <Home size={20} />
              Building Interior Details
            </h2>
            <div className="info-grid">
              {getSafe('interior_finish') && (
                <div className="info-item">
                  <span className="label">Interior Finish</span>
                  <span className="value">{getSafe('interior_finish')}</span>
                </div>
              )}
              {getSafe('heating_type') && (
                <div className="info-item">
                  <span className="label">
                    <Thermometer size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                    Heating Type
                  </span>
                  <span className="value">{getSafe('heating_type')}</span>
                </div>
              )}
              {getSafe('cooling_type') && (
                <div className="info-item">
                  <span className="label">
                    <Wind size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                    Cooling Type
                  </span>
                  <span className="value">{getSafe('cooling_type')}</span>
                </div>
              )}
              {getSafe('fireplace_count') != null && (
                <div className="info-item">
                  <span className="label">
                    <Flame size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                    Fireplaces
                  </span>
                  <span className="value">{getSafe('fireplace_count')}</span>
                </div>
              )}
              {getSafe('bedrooms') && (
                <div className="info-item">
                  <span className="label">Bedrooms</span>
                  <span className="value">{getSafe('bedrooms')}</span>
                </div>
              )}
              {getSafe('bathrooms') && (
                <div className="info-item">
                  <span className="label">Bathrooms</span>
                  <span className="value">{getSafe('bathrooms')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Owner Information */}
          <div className="detail-section">
            <h2>
              <User size={20} />
              Owner Information
            </h2>
            <div className="info-grid">
              {getSafe('owner_name') && (
                <div className="info-item">
                  <span className="label">Owner Name</span>
                  <span className="value">{getSafe('owner_name')}</span>
                </div>
              )}
              {getSafe('owner_address') && (
                <div className="info-item">
                  <span className="label">Owner Address</span>
                  <span className="value">
                    {getSafe('owner_address')}
                    {getSafe('owner_city') && `, ${getSafe('owner_city')}`}
                    {getSafe('owner_state') && `, ${getSafe('owner_state')}`}
                  </span>
                </div>
              )}
              <div className="info-item">
                <span className="label">
                  <Phone size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Phone
                </span>
                <span className="value">
                  {getSafe('owner_phone') ? (
                    <a href={`tel:${getSafe('owner_phone')}`} className="contact-link">
                      {getSafe('owner_phone')}
                    </a>
                  ) : (
                    <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>
                  )}
                </span>
              </div>
              <div className="info-item">
                <span className="label">
                  <Mail size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Email
                </span>
                <span className="value">
                  {getSafe('owner_email') ? (
                    <a href={`mailto:${getSafe('owner_email')}`} className="contact-link">
                      {getSafe('owner_email')}
                    </a>
                  ) : (
                    <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>
                  )}
                </span>
              </div>
              {Number(getSafe('is_absentee', 0)) === 1 && (
                <div className="info-item">
                  <span className="label">Owner Status</span>
                  <span className="value tag-absentee">Absentee Owner</span>
                </div>
              )}
            </div>
          </div>

          {/* Sales History */}
          {(getSafe('last_sale_date') || getSafe('sales_count', 0) > 0) && (
            <div className="detail-section">
              <h2>
                <Calendar size={20} />
                Sales History
              </h2>
              <div className="info-grid">
                {getSafe('last_sale_date') && (
                  <div className="info-item">
                    <span className="label">Last Sale Date</span>
                    <span className="value">{formatDate(getSafe('last_sale_date'))}</span>
                  </div>
                )}
                {getSafe('last_sale_price') != null && (
                  <div className="info-item">
                    <span className="label">Last Sale Price</span>
                    <span className="value highlight">{formatCurrency(getSafe('last_sale_price'))}</span>
                  </div>
                )}
                {getSafe('days_since_sale') != null && (
                  <div className="info-item">
                    <span className="label">Days Since Sale</span>
                    <span className="value">{getSafe('days_since_sale')} days</span>
                  </div>
                )}
                {Number(getSafe('sales_count', 0)) > 0 && (
                  <div className="info-item">
                    <span className="label">Total Sales</span>
                    <span className="value">{getSafe('sales_count')}</span>
                  </div>
                )}
              </div>

              {getSafe('sales') && Array.isArray(getSafe('sales')) && getSafe('sales').length > 0 && (
                <div className="sales-history">
                  <h3>Sales History</h3>
                  <div className="sales-list">
                    {getSafe('sales').map((sale: any, index: number) => (
                      <div key={index} className="sale-item">
                        <div className="sale-date">{formatDate(sale.sale_date)}</div>
                        <div className="sale-price">{formatCurrency(sale.sale_price)}</div>
                        {sale.buyer_name && (
                          <div className="sale-details">Buyer: {sale.buyer_name}</div>
                        )}
                        {sale.seller_name && (
                          <div className="sale-details">Seller: {sale.seller_name}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Property Tags */}
          <div className="detail-section">
            <h2>
              <Home size={20} />
              Property Tags
            </h2>
            <div className="tags">
              {Number(getSafe('is_absentee', 0)) === 1 && (
                <span className="tag tag-absentee">Absentee Owner</span>
              )}
              {Number(getSafe('is_vacant', 0)) === 1 && (
                <span className="tag tag-vacant">Vacant</span>
              )}
              {getSafe('property_type') && (
                <span className="tag">{getSafe('property_type')}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
