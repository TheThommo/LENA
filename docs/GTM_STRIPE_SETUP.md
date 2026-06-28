# LENA GTM — Stripe Setup Checklist

Use this after deploying the GTM branch to production. LENA billing routes are already wired; you only need to create products in Stripe and set Railway env vars.

## 1. Create Stripe products (Dashboard → Products)

| Plan | Price | Billing | Notes |
|------|-------|---------|-------|
| **LENA Pro** | **$19.00 USD** | Monthly recurring | Primary conversion SKU |
| **LENA Pro Annual** | **$190.00 USD** | Yearly recurring | ~17% discount vs monthly |
| **LENA Pro Founding** | **$50.00 USD** | Yearly recurring | First **10** redemptions only (tracked in app) |

Optional later:
- **Voice add-on** ~$5/mo (create when feature ships)

## 2. Copy Price IDs to Railway (backend service)

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_ANNUAL=price_...
STRIPE_PRICE_PRO_FOUNDING=price_...
```

Also verify:
```env
BILLING_SUCCESS_URL=https://lena-app.up.railway.app/chat?billing=success
BILLING_CANCEL_URL=https://lena-app.up.railway.app/chat?billing=cancelled
APP_URL=https://lena-app.up.railway.app
```

## 3. Webhook endpoint

In Stripe → Developers → Webhooks, add:

```
https://lena-production-health.up.railway.app/api/billing/webhook
```

Events to subscribe:
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## 4. Test checkout (Stripe test mode first)

1. Set test keys in a staging env or temporarily in Railway.
2. Register a test user at `/register`.
3. In chat, hit **Upgrade to Pro** when at free limit (or add a test button).
4. Complete Checkout with card `4242 4242 4242 4242`.
5. Confirm webhook writes subscription row and user gets unlimited searches.

## 5. Go-live checklist

- [ ] `./scripts/smoke_test_production.sh` passes
- [ ] Landing page live at `/`, app at `/chat`
- [ ] Free tier: 1 anon search, 10/month registered
- [ ] Pro copy shows **$19/mo** and **$190/yr** in Upgrade CTA
- [ ] Live Stripe keys + webhook secret in Railway
- [ ] Test one real $19 subscription and refund in Dashboard

## 6. Marketing launch

- Point ads and social to `https://lena-app.up.railway.app/` (landing)
- Primary CTA: **Try free** → `/chat` (1 search, no signup)
- Secondary: **Create account** → `/register` (10 searches/month)

Support: hello@lena-app.com
