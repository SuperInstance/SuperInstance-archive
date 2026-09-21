"""
Stripe Integration Module
Handles all Stripe API interactions for payment processing
"""

import os
import stripe
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize Stripe with API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


class StripeIntegration:
    """Main Stripe integration class"""

    def __init__(self):
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    # Customer Management

    def create_customer(self, user_id: str, email: str, name: str, metadata: Dict = None) -> stripe.Customer:
        """Create a new Stripe customer"""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                'user_id': user_id,
                **(metadata or {})
            }
        )
        return customer

    def get_customer(self, customer_id: str) -> stripe.Customer:
        """Retrieve customer by Stripe ID"""
        return stripe.Customer.retrieve(customer_id)

    def update_customer(self, customer_id: str, **kwargs) -> stripe.Customer:
        """Update customer information"""
        return stripe.Customer.modify(customer_id, **kwargs)

    def delete_customer(self, customer_id: str) -> stripe.Customer:
        """Delete a customer"""
        return stripe.Customer.delete(customer_id)

    # Payment Method Management

    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> stripe.PaymentMethod:
        """Attach payment method to customer"""
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id
        )
        return payment_method

    def set_default_payment_method(self, customer_id: str, payment_method_id: str):
        """Set default payment method for customer"""
        stripe.Customer.modify(
            customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id
            }
        )

    def list_payment_methods(self, customer_id: str) -> List[stripe.PaymentMethod]:
        """List all payment methods for customer"""
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        )
        return payment_methods.data

    def detach_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """Remove payment method"""
        return stripe.PaymentMethod.detach(payment_method_id)

    # Subscription Management

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        quantity: int = 1,
        trial_period_days: Optional[int] = None,
        metadata: Dict = None
    ) -> stripe.Subscription:
        """Create a new subscription"""
        subscription_params = {
            'customer': customer_id,
            'items': [{
                'price': price_id,
                'quantity': quantity
            }],
            'payment_behavior': 'default_incomplete',
            'payment_settings': {
                'save_default_payment_method': 'on_subscription'
            },
            'expand': ['latest_invoice.payment_intent'],
            'metadata': metadata or {}
        }

        if trial_period_days:
            subscription_params['trial_period_days'] = trial_period_days

        return stripe.Subscription.create(**subscription_params)

    def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Retrieve subscription details"""
        return stripe.Subscription.retrieve(subscription_id)

    def update_subscription(
        self,
        subscription_id: str,
        price_id: Optional[str] = None,
        quantity: Optional[int] = None,
        proration_behavior: str = 'create_prorations',
        metadata: Optional[Dict] = None
    ) -> stripe.Subscription:
        """Update subscription (upgrade/downgrade)"""
        params = {
            'proration_behavior': proration_behavior
        }

        if price_id:
            subscription = self.get_subscription(subscription_id)
            params['items'] = [{
                'id': subscription['items']['data'][0].id,
                'price': price_id,
                'quantity': quantity or 1
            }]
        elif quantity:
            subscription = self.get_subscription(subscription_id)
            params['items'] = [{
                'id': subscription['items']['data'][0].id,
                'quantity': quantity
            }]

        if metadata:
            params['metadata'] = metadata

        return stripe.Subscription.modify(subscription_id, **params)

    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> stripe.Subscription:
        """Cancel subscription"""
        if at_period_end:
            return stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            return stripe.Subscription.delete(subscription_id)

    def resume_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Resume a canceled subscription"""
        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )

    # Usage-Based Billing

    def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[datetime] = None,
        action: str = 'increment'
    ) -> stripe.UsageRecord:
        """Report usage for metered billing"""
        params = {
            'quantity': quantity,
            'action': action
        }

        if timestamp:
            params['timestamp'] = int(timestamp.timestamp())

        return stripe.SubscriptionItem.create_usage_record(
            subscription_item_id,
            **params
        )

    def list_usage_records(
        self,
        subscription_item_id: str,
        limit: int = 100
    ) -> List[stripe.UsageRecord]:
        """List usage records for subscription item"""
        records = stripe.SubscriptionItem.list_usage_record_summaries(
            subscription_item_id,
            limit=limit
        )
        return records.data

    # Invoice Management

    def create_invoice_item(
        self,
        customer_id: str,
        amount: int,
        currency: str = 'usd',
        description: str = None
    ) -> stripe.InvoiceItem:
        """Create one-time invoice item (e.g., for overages)"""
        return stripe.InvoiceItem.create(
            customer=customer_id,
            amount=amount,
            currency=currency,
            description=description
        )

    def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool = True
    ) -> stripe.Invoice:
        """Create invoice for customer"""
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=auto_advance
        )
        return invoice

    def get_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Retrieve invoice details"""
        return stripe.Invoice.retrieve(invoice_id)

    def list_invoices(
        self,
        customer_id: str,
        limit: int = 100
    ) -> List[stripe.Invoice]:
        """List invoices for customer"""
        invoices = stripe.Invoice.list(
            customer=customer_id,
            limit=limit
        )
        return invoices.data

    def pay_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Pay an invoice"""
        return stripe.Invoice.pay(invoice_id)

    def void_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Void an invoice"""
        return stripe.Invoice.void_invoice(invoice_id)

    # Price Management

    def create_price(
        self,
        product_id: str,
        unit_amount: int,
        currency: str = 'usd',
        recurring_interval: str = 'month',
        metadata: Dict = None
    ) -> stripe.Price:
        """Create a new price"""
        return stripe.Price.create(
            product=product_id,
            unit_amount=unit_amount,
            currency=currency,
            recurring={'interval': recurring_interval},
            metadata=metadata or {}
        )

    def list_prices(self, active: bool = True, limit: int = 100) -> List[stripe.Price]:
        """List all prices"""
        prices = stripe.Price.list(
            active=active,
            limit=limit
        )
        return prices.data

    # Product Management

    def create_product(
        self,
        name: str,
        description: str = None,
        metadata: Dict = None
    ) -> stripe.Product:
        """Create a new product"""
        return stripe.Product.create(
            name=name,
            description=description,
            metadata=metadata or {}
        )

    def list_products(self, active: bool = True, limit: int = 100) -> List[stripe.Product]:
        """List all products"""
        products = stripe.Product.list(
            active=active,
            limit=limit
        )
        return products.data

    # Webhook Handling

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> stripe.Event:
        """Verify and construct webhook event"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return event
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

    # Refunds

    def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> stripe.Refund:
        """Create a refund"""
        params = {
            'payment_intent': payment_intent_id
        }

        if amount:
            params['amount'] = amount
        if reason:
            params['reason'] = reason

        return stripe.Refund.create(**params)

    # Payment Intents (for one-time payments)

    def create_payment_intent(
        self,
        amount: int,
        currency: str = 'usd',
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Dict = None
    ) -> stripe.PaymentIntent:
        """Create payment intent for one-time payment"""
        params = {
            'amount': amount,
            'currency': currency,
            'metadata': metadata or {}
        }

        if customer_id:
            params['customer'] = customer_id
        if payment_method_id:
            params['payment_method'] = payment_method_id
            params['confirm'] = True

        return stripe.PaymentIntent.create(**params)

    # Coupons and Discounts

    def create_coupon(
        self,
        percent_off: Optional[int] = None,
        amount_off: Optional[int] = None,
        duration: str = 'once',
        duration_in_months: Optional[int] = None,
        max_redemptions: Optional[int] = None,
        metadata: Dict = None
    ) -> stripe.Coupon:
        """Create a coupon"""
        params = {
            'duration': duration,
            'metadata': metadata or {}
        }

        if percent_off:
            params['percent_off'] = percent_off
        elif amount_off:
            params['amount_off'] = amount_off

        if duration == 'repeating' and duration_in_months:
            params['duration_in_months'] = duration_in_months

        if max_redemptions:
            params['max_redemptions'] = max_redemptions

        return stripe.Coupon.create(**params)

    def apply_coupon(
        self,
        customer_id: str,
        coupon_id: str
    ) -> stripe.Customer:
        """Apply coupon to customer"""
        return stripe.Customer.modify(
            customer_id,
            coupon=coupon_id
        )

    # Reporting

    def get_balance(self) -> stripe.Balance:
        """Get Stripe account balance"""
        return stripe.Balance.retrieve()

    def list_charges(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100
    ) -> List[stripe.Charge]:
        """List charges"""
        params = {'limit': limit}
        if customer_id:
            params['customer'] = customer_id

        charges = stripe.Charge.list(**params)
        return charges.data

    # Tax Rates

    def create_tax_rate(
        self,
        display_name: str,
        percentage: Decimal,
        inclusive: bool = False,
        jurisdiction: Optional[str] = None
    ) -> stripe.TaxRate:
        """Create tax rate"""
        return stripe.TaxRate.create(
            display_name=display_name,
            percentage=float(percentage),
            inclusive=inclusive,
            jurisdiction=jurisdiction
        )


# Pricing Plan IDs (to be created in Stripe Dashboard)
STRIPE_PRICE_IDS = {
    'hobbyist_monthly': 'price_hobbyist_monthly',
    'hobbyist_annual': 'price_hobbyist_annual',
    'pro_monthly': 'price_pro_monthly',
    'pro_annual': 'price_pro_annual',
    'team_monthly': 'price_team_monthly',
    'team_annual': 'price_team_annual',
}

# Product IDs
STRIPE_PRODUCT_IDS = {
    'swarm_platform': 'prod_swarm_platform'
}
