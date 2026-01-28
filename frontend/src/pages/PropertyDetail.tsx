import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { propertyApi } from '../api/client'
import { useSafeProperty } from '../hooks/useSafeProperty'
import PropertyImageGallery from '../components/PropertyImageGallery'
import PropertyComments from '../components/PropertyComments'
import { ToastContainer } from '../components/Toast'
import { generateZillowUrl } from '../utils/zillow'
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
  Edit2,
  Save,
  X,
  ExternalLink,
} from 'lucide-react'
import { useState, useCallback } from 'react'
import './PropertyDetail.css'

type ToastType = { id: string; message: string; type: 'success' | 'error' | 'warning' }

interface EditableFieldProps {
  label: string
  value: any
  fieldName: string
  type?: 'text' | 'number' | 'email' | 'tel' | 'textarea' | 'checkbox'
  formatValue?: (val: any) => string
  icon?: React.ReactNode
  isEditing: boolean
  editedData: Record<string, any>
  setEditedData: React.Dispatch<React.SetStateAction<Record<string, any>>>
}

const EditableField = ({
  label,
  value,
  fieldName,
  type = 'text',
  formatValue,
  icon,
  isEditing,
  editedData,
  setEditedData,
}: EditableFieldProps) => {
  const displayValue = isEditing ? (editedData[fieldName] !== undefined ? editedData[fieldName] : value) : value
  const formattedDisplay = formatValue ? formatValue(displayValue) : displayValue

  // Handle checkbox type
  if (type === 'checkbox') {
    const boolValue = isEditing 
      ? (editedData[fieldName] !== undefined ? editedData[fieldName] : (value ? 1 : 0))
      : (value ? 1 : 0)
    
    if (!isEditing) {
      return (
        <div className="info-item">
          <span className="label">
            {icon}
            {icon && <span style={{ marginLeft: '0.5rem' }} />}
            {label}
          </span>
          <span className="value">{boolValue === 1 ? 'Yes' : 'No'}</span>
        </div>
      )
    }
    
    return (
      <div className="info-item editable checkbox-field">
        <label className="checkbox-label">
          <input
            type="checkbox"
            className="editable-checkbox"
            checked={boolValue === 1}
            onChange={(e) => setEditedData((prev) => ({ ...prev, [fieldName]: e.target.checked ? 1 : 0 }))}
          />
          <span>{label}</span>
        </label>
      </div>
    )
  }

  if (!isEditing) {
    // Special handling for phone and email in view mode
    if (type === 'tel' && displayValue) {
      return (
        <div className="info-item">
          <span className="label">
            {icon}
            {icon && <span style={{ marginLeft: '0.5rem' }} />}
            {label}
          </span>
          <span className="value">
            <a href={`tel:${displayValue}`} className="contact-link">
              {displayValue}
            </a>
          </span>
        </div>
      )
    }
    if (type === 'email' && displayValue) {
      return (
        <div className="info-item">
          <span className="label">
            {icon}
            {icon && <span style={{ marginLeft: '0.5rem' }} />}
            {label}
          </span>
          <span className="value">
            <a href={`mailto:${displayValue}`} className="contact-link">
              {displayValue}
            </a>
          </span>
        </div>
      )
    }
    return (
      <div className="info-item">
        <span className="label">
          {icon}
          {icon && <span style={{ marginLeft: '0.5rem' }} />}
          {label}
        </span>
        <span className="value">{formattedDisplay || 'N/A'}</span>
      </div>
    )
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newValue = type === 'number' ? (e.target.value === '' ? null : parseFloat(e.target.value)) : e.target.value
    setEditedData((prev) => ({ ...prev, [fieldName]: newValue }))
  }

  const inputValue = editedData[fieldName] !== undefined ? editedData[fieldName] : (value ?? '')

  if (type === 'textarea') {
    return (
      <div className="info-item editable">
        <span className="label">{icon || null}{icon && <span style={{ marginLeft: '0.5rem' }} />}{label}</span>
        <textarea
          className="editable-input"
          value={inputValue}
          onChange={handleChange}
          rows={3}
        />
      </div>
    )
  }

  return (
    <div className="info-item editable">
      <span className="label">{icon || null}{icon && <span style={{ marginLeft: '0.5rem' }} />}{label}</span>
      <input
        type={type}
        className="editable-input"
        value={inputValue ?? ''}
        onChange={handleChange}
      />
    </div>
  )
}

export default function PropertyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedData, setEditedData] = useState<Record<string, any>>({})
  const [toasts, setToasts] = useState<ToastType[]>([])

  const { data: property, isLoading, error } = useQuery({
    queryKey: ['property', id],
    queryFn: () => propertyApi.getProperty(parseInt(id!)),
    enabled: !!id,
  })

  // Use safe property hook for type-safe access
  // Always call the hook (Rules of Hooks) - pass empty object if property is null
  const safeProperty = useSafeProperty(property || {} as any)

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'warning' = 'success') => {
    const toastId = `toast-${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id: toastId, message, type }])
  }, [])

  const removeToast = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
  }, [])

  const updateMutation = useMutation({
    mutationFn: (updates: Partial<any>) => propertyApi.updateProperty(parseInt(id!), updates),
    onSuccess: (updatedProperty) => {
      showToast('✅ Changes saved successfully! Property details have been updated.', 'success')
      queryClient.setQueryData(['property', id], updatedProperty)
      queryClient.invalidateQueries({ queryKey: ['properties'] })
      queryClient.invalidateQueries({ queryKey: ['search'] })
      setIsEditing(false)
      setEditedData({})
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to save changes. Please try again.'
      showToast(errorMessage, 'error')
    },
  })

  const handleEdit = () => {
    setIsEditing(true)
    setEditedData({})
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditedData({})
  }

  const handleSave = () => {
    // Client-side validation
    const validationErrors: string[] = []
    
    if (editedData.owner_email && editedData.owner_email.trim() !== '') {
      const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
      if (!emailPattern.test(editedData.owner_email)) {
        validationErrors.push('Invalid email format')
      }
    }
    
    if (editedData.owner_phone && editedData.owner_phone.trim() !== '') {
      const cleaned = editedData.owner_phone.replace(/[^\d]/g, '')
      if (cleaned.length < 10 || cleaned.length > 15) {
        validationErrors.push('Phone number must be 10-15 digits')
      }
    }
    
    if (editedData.year_built != null) {
      const year = parseInt(editedData.year_built)
      if (isNaN(year) || year < 1800 || year > 2100) {
        validationErrors.push('Year built must be between 1800 and 2100')
      }
    }

    if (validationErrors.length > 0) {
      showToast(validationErrors.join(', '), 'error')
      return
    }

    // Filter out empty strings and convert to null
    const updates: Record<string, any> = {}
    for (const [key, value] of Object.entries(editedData)) {
      if (value === '' || value === null || value === undefined) {
        updates[key] = null
      } else {
        updates[key] = value
      }
    }

    updateMutation.mutate(updates)
  }

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
          <div className="detail-header-top">
            <h1>{getSafe('address', 'No Address')}</h1>
            {(() => {
              const zillowUrl = generateZillowUrl(
                getSafe('address'),
                getSafe('municipality'),
                getSafe('zip_code')
              )
              if (zillowUrl) {
                return (
                  <a
                    href={zillowUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="zillow-link-button"
                    title="View on Zillow"
                  >
                    <ExternalLink size={18} />
                    View on Zillow
                  </a>
                )
              }
              return null
            })()}
          </div>
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
          city={getSafe('municipality')}
          parcelId={getSafe('parcel_id')}
          images={getSafe('images')}
        />

        {/* Comments Section */}
        <PropertyComments propertyId={parseInt(id!)} />

        {/* Edit Button */}
        <div className="detail-actions">
          {!isEditing ? (
            <button className="edit-button" onClick={handleEdit}>
              <Edit2 size={18} />
              Edit Details
            </button>
          ) : (
            <div className="edit-actions">
              <button
                className="save-button"
                onClick={handleSave}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? (
                  <>
                    <div className="spinner-small" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    Save Changes
                  </>
                )}
              </button>
              <button
                className="cancel-button"
                onClick={handleCancel}
                disabled={updateMutation.isPending}
              >
                <X size={18} />
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Toast Container */}
        <ToastContainer toasts={toasts} onRemove={removeToast} />

        {/* Main Content Grid - Reordered Sections */}
        <div className="detail-grid">
          {/* Row 1: Owner Information */}
          <div className="detail-section">
            <h2>
              <User size={20} />
              Owner Information
            </h2>
            <div className="info-grid">
              <EditableField
                label="Owner Name"
                value={getSafe('owner_name')}
                fieldName="owner_name"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Owner Mailing Address"
                value={getSafe('owner_address')}
                fieldName="owner_address"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Owner Mailing City"
                value={getSafe('owner_city')}
                fieldName="owner_city"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Owner Mailing State"
                value={getSafe('owner_state')}
                fieldName="owner_state"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Phone"
                value={getSafe('owner_phone')}
                fieldName="owner_phone"
                type="tel"
                icon={<Phone size={16} />}
                formatValue={(val) => val || 'N/A'}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Email"
                value={getSafe('owner_email')}
                fieldName="owner_email"
                type="email"
                icon={<Mail size={16} />}
                formatValue={(val) => val || 'N/A'}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Absentee Owner"
                value={Number(getSafe('is_absentee', 0))}
                fieldName="is_absentee"
                type="checkbox"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 1: Sales History */}
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

          {/* Row 2: Property Characteristics */}
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
              <EditableField
                label="Property Type"
                value={getSafe('property_type')}
                fieldName="property_type"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Land Use"
                value={getSafe('land_use')}
                fieldName="land_use"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Year Built"
                value={getSafe('year_built')}
                fieldName="year_built"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Stories"
                value={getSafe('stories')}
                fieldName="stories"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Total Rooms"
                value={getSafe('total_rooms')}
                fieldName="total_rooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Bedrooms"
                value={getSafe('bedrooms')}
                fieldName="bedrooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Bathrooms"
                value={getSafe('bathrooms')}
                fieldName="bathrooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 2: Building Details */}
          <div className="detail-section">
            <h2>
              <Building size={20} />
              Building Details
            </h2>
            <div className="info-grid">
              <EditableField
                label="Building Area"
                value={getSafe('building_area_sqft')}
                fieldName="building_area_sqft"
                type="number"
                formatValue={(val) => val ? `${formatNumber(val)} sq ft` : 'N/A'}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Year Built"
                value={getSafe('year_built')}
                fieldName="year_built"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Stories"
                value={getSafe('stories')}
                fieldName="stories"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Bedrooms"
                value={getSafe('bedrooms')}
                fieldName="bedrooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Bathrooms"
                value={getSafe('bathrooms')}
                fieldName="bathrooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Total Rooms"
                value={getSafe('total_rooms')}
                fieldName="total_rooms"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 3: Building Interior Details */}
          <div className="detail-section">
            <h2>
              <Home size={20} />
              Building Interior Details
            </h2>
            <div className="info-grid">
              <EditableField
                label="Interior Finish"
                value={getSafe('interior_finish')}
                fieldName="interior_finish"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Heating Type"
                value={getSafe('heating_type')}
                fieldName="heating_type"
                icon={<Thermometer size={16} />}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Cooling Type"
                value={getSafe('cooling_type')}
                fieldName="cooling_type"
                icon={<Wind size={16} />}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Fireplaces"
                value={getSafe('fireplace_count')}
                fieldName="fireplace_count"
                type="number"
                icon={<Flame size={16} />}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 3: Building Exterior Details */}
          <div className="detail-section">
            <h2>
              <Building size={20} />
              Building Exterior Details
            </h2>
            <div className="info-grid">
              <EditableField
                label="Exterior Walls"
                value={getSafe('exterior_walls')}
                fieldName="exterior_walls"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Roof Type"
                value={getSafe('roof_type')}
                fieldName="roof_type"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Roof Material"
                value={getSafe('roof_material')}
                fieldName="roof_material"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Foundation Type"
                value={getSafe('foundation_type')}
                fieldName="foundation_type"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Exterior Finish"
                value={getSafe('exterior_finish')}
                fieldName="exterior_finish"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Garage Type"
                value={getSafe('garage_type')}
                fieldName="garage_type"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Garage Spaces"
                value={getSafe('garage_spaces')}
                fieldName="garage_spaces"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 4: Assessment & Value */}
          <div className="detail-section">
            <h2>
              <DollarSign size={20} />
              Assessment & Value
            </h2>
            <div className="info-grid">
              <EditableField
                label="Assessed Value"
                value={getSafe('assessed_value')}
                fieldName="assessed_value"
                type="number"
                formatValue={(val) => formatCurrency(val)}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Land Value"
                value={getSafe('land_value')}
                fieldName="land_value"
                type="number"
                formatValue={(val) => formatCurrency(val)}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Building Value"
                value={getSafe('building_value')}
                fieldName="building_value"
                type="number"
                formatValue={(val) => formatCurrency(val)}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              {getSafe('equity_estimate') != null && (
                <div className="info-item">
                  <span className="label">Estimated Equity</span>
                  <span className="value highlight">{formatCurrency(getSafe('equity_estimate'))}</span>
                </div>
              )}
            </div>
          </div>

          {/* Row 4: Tax Information */}
          <div className="detail-section">
            <h2>
              <Landmark size={20} />
              Tax Information
            </h2>
            <div className="info-grid">
              <EditableField
                label="Annual Tax Amount"
                value={getSafe('tax_amount')}
                fieldName="tax_amount"
                type="number"
                formatValue={(val) => formatCurrency(val)}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Tax Year"
                value={getSafe('tax_year')}
                fieldName="tax_year"
                type="number"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              {getSafe('assessment_year') && (
                <div className="info-item">
                  <span className="label">Assessment Year</span>
                  <span className="value">{getSafe('assessment_year')}</span>
                </div>
              )}
              <EditableField
                label="Tax Exemptions"
                value={getSafe('tax_exemptions')}
                fieldName="tax_exemptions"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 5: Land Information */}
          <div className="detail-section">
            <h2>
              <Layers size={20} />
              Land Information
            </h2>
            <div className="info-grid">
              <EditableField
                label="Lot Size"
                value={getSafe('lot_size_sqft')}
                fieldName="lot_size_sqft"
                type="number"
                formatValue={(val) => val ? `${formatNumber(val)} sq ft` : 'N/A'}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Land Value"
                value={getSafe('land_value')}
                fieldName="land_value"
                type="number"
                formatValue={(val) => formatCurrency(val)}
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Land Use Classification"
                value={getSafe('land_use')}
                fieldName="land_use"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
          </div>

          {/* Row 5: Property Tags */}
          <div className="detail-section">
            <h2>
              <Home size={20} />
              Property Tags
            </h2>
            <div className="info-grid">
              <EditableField
                label="Absentee Owner"
                value={Number(getSafe('is_absentee', 0))}
                fieldName="is_absentee"
                type="checkbox"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
              <EditableField
                label="Vacant"
                value={Number(getSafe('is_vacant', 0))}
                fieldName="is_vacant"
                type="checkbox"
                isEditing={isEditing}
                editedData={editedData}
                setEditedData={setEditedData}
              />
            </div>
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
