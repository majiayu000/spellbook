# product-analytics Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Key Metrics & Formulas`.

## Key Metrics & Formulas

### Engagement Metrics

```
Daily Active Users (DAU)
= Unique users performing key action per day

Monthly Active Users (MAU)
= Unique users performing key action per month

Stickiness = DAU / MAU × 100%
• 20%+ = Good (users engage 6+ days/month)
• 10-20% = Average
• <10% = Low engagement

Session Duration
= Average time between session start and end

Session Frequency
= Average sessions per user per time period
```

### Retention Metrics

```
Retention Rate (Classic)
= Users active in Week N / Users in original cohort

Retention Rate (Bracket)
= Users active in Week N / Users active in Week 0

Churn Rate
= (Users at start - Users at end) / Users at start

Quick Ratio (Growth Health)
= (New MRR + Expansion MRR) / (Churned MRR + Contraction MRR)
• >4 = Excellent growth
• 2-4 = Good
• <1 = Shrinking
```

### Conversion Metrics

```
Conversion Rate
= (Conversions / Total visitors) × 100%

Funnel Conversion
= (Users completing final step / Users entering funnel) × 100%

Time to Convert
= Median time from first touch to conversion
```

### Revenue Metrics

```
Monthly Recurring Revenue (MRR)
= Sum of all monthly subscription values

Annual Recurring Revenue (ARR)
= MRR × 12

Average Revenue Per User (ARPU)
= Total revenue / Number of users

Customer Lifetime Value (LTV)
= ARPU × Average customer lifetime (months)
OR
= ARPU × Gross Margin % / Monthly Churn Rate

Customer Acquisition Cost (CAC)
= Total sales & marketing spend / New customers acquired

LTV:CAC Ratio
= LTV / CAC
• >3:1 = Healthy
• 1:1 = Unsustainable

Payback Period
= CAC / (ARPU × Gross Margin %)
• <12 months = Good
• 12-18 months = Acceptable
• >18 months = Concerning
```

---

## Event Tracking Best Practices

### Event Naming Convention

```
Object + Action pattern (recommended)

✓ user_signed_up
✓ project_created
✓ file_uploaded
✓ payment_completed

✗ signup (unclear)
✗ new_project (inconsistent)
✗ Upload File (inconsistent case)
```

### Event Properties Structure

```javascript
// Standard event structure
{
  event: "checkout_completed",        // Event name
  timestamp: "2025-12-16T10:30:00Z",  // When
  user_id: "usr_123",                 // Who
  session_id: "ses_abc",              // Session context
  properties: {                       // Event-specific data
    order_id: "ord_789",
    total_amount: 99.99,
    currency: "USD",
    item_count: 3,
    payment_method: "credit_card",
    coupon_used: true,
    discount_amount: 10.00
  },
  context: {                          // Global context
    app_version: "2.4.1",
    platform: "web",
    user_agent: "...",
    ip: "192.168.1.1",
    locale: "en-US"
  }
}
```

### Critical Events to Track

```markdown
## User Lifecycle
- user_signed_up
- user_activated (first key action)
- user_onboarded (completed setup)
- user_upgraded (plan change)
- user_churned (canceled/inactive)

## Feature Usage
- feature_viewed
- feature_used
- feature_completed

## Commerce
- product_viewed
- product_added_to_cart
- checkout_started
- payment_completed
- order_fulfilled

## Engagement
- session_started
- session_ended
- page_viewed
- search_performed
- content_shared

## Errors
- error_occurred
- payment_failed
- api_error
```

### Privacy & Compliance

```javascript
// ✓ GOOD: No PII in events
track('user_signed_up', {
  user_id: hashUserId('user@example.com'),  // Hashed
  plan: 'pro',
  source: 'organic'
});

// ✗ BAD: Contains PII
track('user_signed_up', {
  email: 'user@example.com',  // PII!
  password: '...',            // Never log!
  credit_card: '...'          // Never log!
});

// Masking strategies
const maskEmail = (email) => {
  const [name, domain] = email.split('@');
  return `${name[0]}***@${domain}`;
};

const maskCard = (card) => `****${card.slice(-4)}`;
```

---

## See Also

- [reference/event-tracking.md](reference/event-tracking.md) — Event tracking and data modeling guide
- [reference/metrics-framework.md](reference/metrics-framework.md) — North Star, AARRR, key metrics deep dive
- [reference/experimentation.md](reference/experimentation.md) — A/B testing and statistical best practices
- [reference/retention.md](reference/retention.md) — Cohort analysis and retention strategies
- [templates/tracking-plan.md](templates/tracking-plan.md) — Event tracking plan template
