import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { propertyApi } from '../api/client'
import { ArrowLeft, MapPin, User, DollarSign, Calendar, Home, Phone, Mail } from 'lucide-react'
import './PropertyDetail.css'

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: property, isLoading, error } = useQuery({
    queryKey: ['property', id],
    queryFn: () => propertyApi.getProperty(parseInt(id!)),
    enabled: !!id,
  })

  const formatCurrency = (value: number | null) => {
    if (!value) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
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

  return (
    <div className="property-detail">
      <div className="detail-container">
        <button className="back-button" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
          Back
        </button>

        <div className="detail-header">
          <h1>{property.address || 'No Address'}</h1>
          {property.municipality && (
            <div className="location">
              <MapPin size={18} />
              <span>{property.municipality}, CT</span>
            </div>
          )}
        </div>

        <div className="detail-grid">
          <div className="detail-section">
            <h2>
              <MapPin size={20} />
              Property Information
            </h2>
            <div className="info-grid">
              <div className="info-item">
                <span className="label">Parcel ID</span>
                <span className="value">{property.parcel_id}</span>
              </div>
              {property.property_type && (
                <div className="info-item">
                  <span className="label">Property Type</span>
                  <span className="value">{property.property_type}</span>
                </div>
              )}
              {property.land_use && (
                <div className="info-item">
                  <span className="label">Land Use</span>
                  <span className="value">{property.land_use}</span>
                </div>
              )}
              {property.lot_size_sqft && (
                <div className="info-item">
                  <span className="label">Lot Size</span>
                  <span className="value">
                    {property.lot_size_sqft.toLocaleString()} sq ft
                  </span>
                </div>
              )}
              {property.building_area_sqft && (
                <div className="info-item">
                  <span className="label">Building Area</span>
                  <span className="value">
                    {property.building_area_sqft.toLocaleString()} sq ft
                  </span>
                </div>
              )}
              {property.year_built && (
                <div className="info-item">
                  <span className="label">Year Built</span>
                  <span className="value">{property.year_built}</span>
                </div>
              )}
              {property.bedrooms && (
                <div className="info-item">
                  <span className="label">Bedrooms</span>
                  <span className="value">{property.bedrooms}</span>
                </div>
              )}
              {property.bathrooms && (
                <div className="info-item">
                  <span className="label">Bathrooms</span>
                  <span className="value">{property.bathrooms}</span>
                </div>
              )}
            </div>
          </div>

          <div className="detail-section">
            <h2>
              <DollarSign size={20} />
              Assessment & Value
            </h2>
            <div className="info-grid">
              {property.assessed_value && (
                <div className="info-item">
                  <span className="label">Assessed Value</span>
                  <span className="value highlight">
                    {formatCurrency(property.assessed_value)}
                  </span>
                </div>
              )}
              {property.land_value && (
                <div className="info-item">
                  <span className="label">Land Value</span>
                  <span className="value">{formatCurrency(property.land_value)}</span>
                </div>
              )}
              {property.building_value && (
                <div className="info-item">
                  <span className="label">Building Value</span>
                  <span className="value">{formatCurrency(property.building_value)}</span>
                </div>
              )}
              {property.equity_estimate && (
                <div className="info-item">
                  <span className="label">Estimated Equity</span>
                  <span className="value highlight">
                    {formatCurrency(property.equity_estimate)}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="detail-section">
            <h2>
              <User size={20} />
              Owner Information
            </h2>
            <div className="info-grid">
              {property.owner_name && (
                <div className="info-item">
                  <span className="label">Owner Name</span>
                  <span className="value">{property.owner_name}</span>
                </div>
              )}
              {property.owner_address && (
                <div className="info-item">
                  <span className="label">Owner Address</span>
                  <span className="value">
                    {property.owner_address}
                    {property.owner_city && `, ${property.owner_city}`}
                    {property.owner_state && `, ${property.owner_state}`}
                    {property.owner_zip && ` ${property.owner_zip}`}
                  </span>
                </div>
              )}
              <div className="info-item">
                <span className="label">
                  <Phone size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Phone
                </span>
                <span className="value">
                  {property.owner_phone ? (
                    <a href={`tel:${property.owner_phone}`} className="contact-link">
                      {property.owner_phone}
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
                  {property.owner_email ? (
                    <a href={`mailto:${property.owner_email}`} className="contact-link">
                      {property.owner_email}
                    </a>
                  ) : (
                    <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>
                  )}
                </span>
              </div>
              {property.is_absentee === 1 && (
                <div className="info-item">
                  <span className="label">Owner Status</span>
                  <span className="value tag-absentee">Absentee Owner</span>
                </div>
              )}
            </div>
          </div>

          {property.last_sale_date && (
            <div className="detail-section">
              <h2>
                <Calendar size={20} />
                Sales History
              </h2>
              <div className="info-grid">
                <div className="info-item">
                  <span className="label">Last Sale Date</span>
                  <span className="value">{formatDate(property.last_sale_date)}</span>
                </div>
                {property.last_sale_price && (
                  <div className="info-item">
                    <span className="label">Last Sale Price</span>
                    <span className="value highlight">
                      {formatCurrency(property.last_sale_price)}
                    </span>
                  </div>
                )}
                {property.days_since_sale && (
                  <div className="info-item">
                    <span className="label">Days Since Sale</span>
                    <span className="value">{property.days_since_sale} days</span>
                  </div>
                )}
                {property.sales_count > 0 && (
                  <div className="info-item">
                    <span className="label">Total Sales</span>
                    <span className="value">{property.sales_count}</span>
                  </div>
                )}
              </div>

              {property.sales && property.sales.length > 0 && (
                <div className="sales-history">
                  <h3>Sales History</h3>
                  <div className="sales-list">
                    {property.sales.map((sale, index) => (
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

          <div className="detail-section">
            <h2>
              <Home size={20} />
              Property Tags
            </h2>
            <div className="tags">
              {property.is_absentee === 1 && (
                <span className="tag tag-absentee">Absentee Owner</span>
              )}
              {property.is_vacant === 1 && (
                <span className="tag tag-vacant">Vacant</span>
              )}
              {property.property_type && (
                <span className="tag">{property.property_type}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
