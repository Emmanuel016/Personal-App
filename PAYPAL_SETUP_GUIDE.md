# PayPal Payment Integration Setup Guide

## Overview
Your application now supports **PayPal payments** for credit/debit cards in **GBP**. This guide walks you through the setup process.

---

## Step 1: Create a PayPal Business Account

1. Go to [PayPal Business](https://www.paypal.com/uk/en/webapps/mpp/business)
2. Click **"Get Started"** and create a PayPal Business account
3. Use your email: `ugwuemmanuel074@gmail.com`
4. Complete the business verification process

---

## Step 2: Set Up Sandbox for Testing

1. Log in to [PayPal Developer Dashboard](https://developer.paypal.com/)
2. Navigate to **Apps & Credentials**
3. Make sure you're in **Sandbox mode** (top left)
4. Under **Sandbox Accounts**, create:
   - **Business account** (for you as the merchant)
   - **Personal account** (for testing payments)

---

## Step 3: Get Your API Credentials

1. In **PayPal Developer Dashboard** → **Apps & Credentials** (Sandbox mode)
2. Find **Sandbox Signature** or **Sandbox Certificate**
3. Click on your app/business account to view credentials
4. Copy these values:
   - **Client ID** (looks like: `ABC123...`)
   - **Secret** (looks like: `XYZ789...`)

---

## Step 4: Set Environment Variables

Add these to your `.env` file or environment variables:

```bash
# PayPal Configuration
PAYPAL_MODE=sandbox          # Use "sandbox" for testing, "live" for production
PAYPAL_CLIENT_ID=YOUR_CLIENT_ID_HERE
PAYPAL_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
```

### For Local Development (.env file):
```
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=AXyz123...
PAYPAL_CLIENT_SECRET=XYZ789...
```

### For Production (Render/Deployment):
1. Log in to your Render dashboard
2. Go to your service **Settings** → **Environment**
3. Add the variables there (switch `sandbox` to `live`)
4. Use production credentials from PayPal Dashboard (toggle to **Live** mode)

---

## Step 5: Install PayPal SDK

The SDK is already added to `requirements.txt`, but to install locally:

```bash
pip install paypalrestsdk==1.7.1
```

---

## Step 6: Test the Integration

### Frontend Payment Flow:

1. Client goes to **Billing** page
2. Selects a project and enters payment amount
3. Clicks **"Pay with PayPal"**
4. Gets redirected to PayPal approval page
5. Logs in with PayPal account (use sandbox personal account for testing)
6. Approves payment
7. Redirected back to your app with payment confirmation

### API Endpoints:

**Create Payment:**
```bash
POST /api/paypal/create-payment
Content-Type: application/json

{
  "project_id": 1,
  "amount": 150.00
}
```

**Response (Success):**
```json
{
  "status": "success",
  "payment_id": "PAYID-ABC123...",
  "approval_url": "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-ABC123..."
}
```

**Execute Payment (after PayPal redirect):**
- Automatically handled when user returns from PayPal
- `GET /api/paypal/execute-payment?paymentId=PAYID-ABC123...&PayerID=PAYER123...`

---

## Step 7: Frontend Integration

### Update your `client_billing.html` template:

```html
<script>
  async function payWithPayPal(projectId, amount) {
    try {
      const response = await fetch('/api/paypal/create-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          project_id: projectId,
          amount: amount
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        // Redirect to PayPal
        window.location.href = data.approval_url;
      } else {
        alert('Error: ' + data.error);
      }
    } catch (error) {
      console.error('Payment error:', error);
      alert('Payment failed: ' + error.message);
    }
  }
</script>

<!-- Payment Button -->
<button onclick="payWithPayPal(projectId, amount)">
  Pay with PayPal
</button>
```

---

## Testing Credentials (Sandbox)

### Business Account (Your Account):
- Email: (your sandbox business email - created in PayPal Dashboard)
- Password: (from sandbox account creation)

### Personal Account (For Testing Payments):
- Email: (your sandbox personal email - created in PayPal Dashboard)
- Password: (from sandbox account creation)

---

## Switching to Live/Production

When ready to go live:

1. In [PayPal Developer Dashboard](https://developer.paypal.com/):
   - Toggle to **Live** mode (top left)
   - Copy your **Live Client ID** and **Live Secret**

2. Update environment variables:
   ```bash
   PAYPAL_MODE=live
   PAYPAL_CLIENT_ID=YOUR_LIVE_CLIENT_ID
   PAYPAL_CLIENT_SECRET=YOUR_LIVE_CLIENT_SECRET
   ```

3. Test thoroughly before going live!

---

## Important Notes

### Security:
- ⚠️ **Never commit** `.env` file with real credentials
- Use environment variables for all sensitive data
- Keep Client Secret safe - never expose in frontend code

### UK Regulations:
- PayPal handles PCI compliance for card payments
- You're compliant with UK payment regulations
- Customers see transactions in GBP

### Payment Recording:
- Each successful payment creates a Message record
- Payment details stored in `payment_data` JSON field
- All transactions traceable and auditable

---

## Troubleshooting

### Payment creation fails:
- Check PayPal credentials in environment variables
- Verify `PAYPAL_MODE=sandbox` for testing
- Check application logs: `[*] PayPal payment created successfully`

### User not redirected to PayPal:
- Verify `approval_url` is being returned
- Check browser console for JavaScript errors

### Payment won't execute:
- Ensure PayerID and PaymentID are correct
- Check payment status in PayPal Dashboard

---

## Next Steps

1. ✅ Create PayPal Business account
2. ✅ Get Sandbox credentials
3. ✅ Add to `.env` file
4. ✅ Update frontend billing page
5. ✅ Test with sandbox accounts
6. ✅ Deploy and switch to Live mode

---

## Support

For PayPal API help: [PayPal Developer Docs](https://developer.paypal.com/docs/)

For issues: Check application logs for `[!]` error markers
