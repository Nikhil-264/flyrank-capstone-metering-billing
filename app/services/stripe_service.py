import stripe
import uuid
from typing import Optional
from app.config.settings import settings

# Initialize the Stripe client globally
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    async def get_or_create_pro_price() -> str:
        """
        Get or create the 'Pro Plan' product and price in Stripe.
        Returns the price ID.
        """
        import asyncio
        return await asyncio.to_thread(StripeService._sync_get_or_create_pro_price)

    @staticmethod
    def _sync_get_or_create_pro_price() -> str:
        # 1. Look for existing active product named "Pro Plan"
        products = stripe.Product.list(limit=100)
        pro_product = None
        for p in products.data:
            if p.name == "Pro Plan" and p.active:
                pro_product = p
                break
        
        if not pro_product:
            pro_product = stripe.Product.create(
                name="Pro Plan",
                description="Usage Metering & Billing Pro Plan"
            )
        
        # 2. Look for active recurring price under that product
        prices = stripe.Price.list(product=pro_product.id, active=True, limit=100)
        pro_price = None
        for pr in prices.data:
            if pr.type == "recurring" and pr.recurring.interval == "month":
                pro_price = pr
                break
                
        if not pro_price:
            # Create a monthly recurring price for $49.00 USD (4900 cents)
            pro_price = stripe.Price.create(
                product=pro_product.id,
                unit_amount=4900,
                currency="usd",
                recurring={"interval": "month"}
            )
            
        return pro_price.id

    @staticmethod
    async def create_checkout_session(
        tenant_id: uuid.UUID,
        success_url: str,
        cancel_url: str,
        stripe_customer_id: Optional[str] = None
    ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout Session for subscription upgrade.
        Saves tenant metadata under metadata and subscription_data.metadata to propagate to webhook events.
        """
        import asyncio
        pro_price_id = await StripeService.get_or_create_pro_price()
        
        def _sync_create():
            kwargs = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": pro_price_id,
                    "quantity": 1
                }],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "subscription_data": {
                    "metadata": {
                        "tenant_id": str(tenant_id),
                        "plan_id": "pro"
                    }
                },
                "metadata": {
                    "tenant_id": str(tenant_id),
                    "plan_id": "pro"
                }
            }
            if stripe_customer_id:
                kwargs["customer"] = stripe_customer_id
            
            return stripe.checkout.Session.create(**kwargs)
            
        return await asyncio.to_thread(_sync_create)
