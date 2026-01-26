# Billing Setup and Usage Monitoring

## Mapbox Billing Configuration

### 1. Set Up Mapbox Account

1. Create account at https://account.mapbox.com/
2. Navigate to Account Settings > Billing
3. Add payment method (required even for free tier)

### 2. Configure Usage Alerts

Set up alerts in Mapbox dashboard:

1. Go to https://account.mapbox.com/usage/
2. Click "Set up alerts"
3. Configure alerts:
   - **40,000 loads** (80% of free tier) - Warning
   - **50,000 loads** (free tier limit) - Critical
   - **75,000 loads** (if expecting growth) - Budget alert

### 3. Set Spending Limits

1. Go to Account Settings > Billing
2. Set monthly spending limit (optional but recommended)
3. Enable email notifications for billing events

### 4. Monitor Usage

#### Via Mapbox Dashboard

- Daily usage: https://account.mapbox.com/usage/
- Projected costs: Shown in dashboard
- Historical data: Available for past 90 days

#### Via Application API

```bash
# Get usage statistics
curl http://localhost:8000/api/analytics/map-usage?days=30
```

Response includes:
- Total map loads
- Daily averages
- Monthly estimates
- Cost estimates for Mapbox and Google Maps
- Recommended plan based on usage

### 5. Cost Optimization Tips

1. **Lazy Loading**: Only initialize map when user interacts
2. **Caching**: Cache map tiles when possible
3. **Static Maps**: Use static map images for non-interactive displays
4. **Monitor Daily**: Check usage dashboard regularly

### 6. Billing Alerts Setup

#### Email Notifications

Mapbox automatically sends:
- Weekly usage summaries
- Billing alerts when thresholds are reached
- Payment confirmations

#### Custom Alerts

Set up custom alerts via:
1. Account Settings > Notifications
2. Enable "Usage alerts"
3. Set custom thresholds

### 7. Cost Estimation

Based on your usage data:

- **0-50K loads/month**: Free
- **50K-100K loads/month**: ~$250/month
- **100K-200K loads/month**: ~$500/month (with volume discounts)

### 8. Switching Plans

If usage exceeds free tier:

1. Review usage patterns in dashboard
2. Consider optimizations (lazy loading, caching)
3. If needed, upgrade to pay-as-you-go
4. Volume discounts apply automatically

### 9. Emergency Procedures

If unexpected charges occur:

1. Check usage dashboard immediately
2. Review recent changes to application
3. Contact Mapbox support: https://support.mapbox.com/
4. Consider temporarily disabling map if needed

### 10. Monthly Review Checklist

- [ ] Review usage dashboard
- [ ] Check cost projections
- [ ] Verify alerts are working
- [ ] Review optimization opportunities
- [ ] Update spending limits if needed

## Google Maps Alternative

If considering Google Maps instead:

### Pricing Comparison

- **Starter Plan**: $100/month (50K loads)
- **Essentials Plan**: $275/month (100K loads)
- **Pay-as-you-go**: ~$7 per 1,000 loads

### When to Consider Google Maps

- Predictable, consistent usage
- Need for bundled features (Places, Routes)
- Preference for fixed monthly costs

## Support Resources

- Mapbox Support: https://support.mapbox.com/
- Mapbox Pricing: https://www.mapbox.com/pricing
- Usage Dashboard: https://account.mapbox.com/usage/
- Billing FAQ: https://docs.mapbox.com/help/troubleshooting/billing/
