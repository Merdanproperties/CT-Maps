import { Property } from '../api/client'
import { Home, Building2, Users, Phone, Mail } from 'lucide-react'
import './PropertyCard.css'

interface PropertyCardProps {
  property: Property
  onClick?: () => void
}

export default function PropertyCard({ property, onClick }: PropertyCardProps) {
  const formatCurrency = (value: number | null) => {
    if (!value) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatShortCurrency = (value: number | null) => {
    if (!value) return null
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`
    }
    return formatCurrency(value)
  }

  // Determine property type display
  const getPropertyTypeDisplay = () => {
    if (!property.property_type) return null
    const type = property.property_type.toLowerCase()
    if (type.includes('single') || type.includes('one')) return 'Single Family'
    if (type.includes('two') || type.includes('2')) return 'Two Family'
    if (type.includes('multi') || type.includes('5+')) return 'Multi family (5+)'
    return property.property_type
  }

  return (
    <div className="property-card" onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      {/* Checkbox */}
      <input type="checkbox" className="property-card-checkbox" />

      {/* Address and Location */}
      <div className="property-header">
        <h3>{property.address || 'No Address'}</h3>
        {property.municipality && (
          <span className="municipality">{property.municipality}, CT {property.zip_code || ''}</span>
        )}
      </div>

      {/* Estimated Value (Top Right) */}
      <div className="property-value-section">
        {property.assessed_value && (
          <>
            <div className="property-value">{formatShortCurrency(property.assessed_value)}</div>
            <div className="value-label">Est. Value</div>
          </>
        )}
      </div>

      {/* Details Row */}
      <div className="property-details">
        {property.lot_size_sqft && (
          <div className="detail-row">
            <Home size={16} className="icon" />
            <span className="value">{property.lot_size_sqft.toLocaleString(undefined, { maximumFractionDigits: 0 })} Sq. Ft.</span>
          </div>
        )}

        {getPropertyTypeDisplay() && (
          <div className="detail-row">
            <Building2 size={16} className="icon" />
            <span className="value">{getPropertyTypeDisplay()}</span>
          </div>
        )}

        {property.is_absentee === 1 && (
          <div className="detail-row">
            <Users size={16} className="icon" />
            <span className="value">Individual Owned</span>
          </div>
        )}
      </div>

      {/* Owner Name (Bottom Right) */}
      <div className="equity-section">
        <div className="equity-value">{property.owner_name || 'N/A Owner'}</div>
        <div className="value-label">Owner</div>
      </div>

      {/* Contact Information - Always show */}
      <div className="property-contact">
        <div className="contact-item">
          <Phone size={14} className="contact-icon" />
          {property.owner_phone ? (
            <a href={`tel:${property.owner_phone}`} className="contact-link" onClick={(e) => e.stopPropagation()}>
              {property.owner_phone}
            </a>
          ) : (
            <span className="contact-na">N/A</span>
          )}
        </div>
        <div className="contact-item">
          <Mail size={14} className="contact-icon" />
          {property.owner_email ? (
            <a href={`mailto:${property.owner_email}`} className="contact-link" onClick={(e) => e.stopPropagation()}>
              {property.owner_email}
            </a>
          ) : (
            <span className="contact-na">N/A</span>
          )}
        </div>
      </div>

      {/* Tags */}
      <div className="property-tags">
        {property.is_absentee === 1 && (
          <span className="tag tag-absentee">Absentee Owners</span>
        )}
        {property.is_vacant === 1 && (
          <span className="tag tag-vacant">Vacant</span>
        )}
      </div>
    </div>
  )
}
