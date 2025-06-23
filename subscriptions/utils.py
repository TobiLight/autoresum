# File: subscriptions/utils.py
# Author: Oluwatobiloba Light
"""STRIPE UTILITIES"""
from datetime import timezone
import logging
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model

from subscriptions.models import PaymentHistory, SubscriptionPlan

logger = logging.getLogger(__name__)
User = get_user_model()

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for Stripe operations"""

    def __init__(self):
        self.stripe = stripe

    def get_or_create_customer(self, user):
        """Get or create a Stripe customer for the user"""
        from .models import SubscriptionPlan

        try:
            subscription_plan = SubscriptionPlan.objects.get(user=user)
            if subscription_plan.stripe_customer_id:
                # Verify customer exists in Stripe
                try:
                    customer = self.stripe.Customer.retrieve(
                        subscription_plan.stripe_customer_id
                    )
                    return customer
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist, create new one
                    pass
        except SubscriptionPlan.DoesNotExist:
            # Create subscription plan if it doesn't exist
            subscription_plan = SubscriptionPlan.objects.create(user=user)

        # Create new Stripe customer
        customer = self.stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip(),
            metadata={
                "user_id": user.id,
            },
        )

        # Update subscription plan with customer ID
        subscription_plan.stripe_customer_id = customer.id
        subscription_plan.save()

        logger.info(f"Created Stripe customer for user: {user.email}")
        return customer

    def create_checkout_session(
        self, user, price_id, success_url=None, cancel_url=None
    ):
        """Create a Stripe checkout session"""
        customer = self.get_or_create_customer(user)

        # Default URLs
        if not success_url:
            success_url = f"http://localhost:8000/api/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"http://localhost:8000/api/subscription/canceled"

        session = self.stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user.id,
            },
            # Enable customer portal after checkout
            subscription_data={
                "metadata": {
                    "user_id": user.id,
                }
            },
        )

        logger.info(f"Created checkout session for user: {user.email}")
        return session

    def create_portal_session(self, customer_id, return_url):
        """Create a Stripe customer portal session"""
        session = self.stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        logger.info(f"Created portal session for customer: {customer_id}")
        return session

    def cancel_subscription(self, subscription_id, at_period_end=True):
        """Cancel a subscription"""
        if at_period_end:
            subscription = self.stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=True
            )
        else:
            subscription = self.stripe.Subscription.delete(subscription_id)

        logger.info(f"Cancelled subscription: {subscription_id}")
        return subscription

    def reactivate_subscription(self, subscription_id):
        """Reactivate a cancelled subscription"""
        subscription = self.stripe.Subscription.modify(
            subscription_id, cancel_at_period_end=False
        )

        logger.info(f"Reactivated subscription: {subscription_id}")
        return subscription

    def get_subscription(self, subscription_id):
        """Get subscription details from Stripe"""
        return self.stripe.Subscription.retrieve(subscription_id)

    def get_customer_subscriptions(self, customer_id):
        """Get all subscriptions for a customer"""
        return self.stripe.Subscription.list(customer=customer_id)

    def get_upcoming_invoice(self, customer_id):
        """Get the upcoming invoice for a customer"""
        try:
            return self.stripe.Invoice.upcoming(customer=customer_id)
        except stripe.error.InvalidRequestError:
            # No upcoming invoice
            return None

    def create_payment_intent(self, amount, currency="usd", customer_id=None):
        """Create a payment intent for one-time payments"""
        intent_data = {
            "amount": int(amount * 100),  # Convert to cents
            "currency": currency,
            "automatic_payment_methods": {
                "enabled": True,
            },
        }

        if customer_id:
            intent_data["customer"] = customer_id

        return self.stripe.PaymentIntent.create(**intent_data)

    def verify_webhook_signature(self, payload, signature, endpoint_secret):
        """Verify Stripe webhook signature"""
        try:
            return self.stripe.Webhook.construct_event(
                payload, signature, endpoint_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise


class SubscriptionManager:
    """Manager class for subscription business logic"""

    def __init__(self):
        self.stripe_service = StripeService()
        self.payment_manager = PaymentHistoryManager()

    def sync_subscription_from_stripe(self, user):
        """Sync user's subscription data from Stripe"""
        from .models import SubscriptionPlan

        try:
            subscription_plan = SubscriptionPlan.objects.get(user=user)

            if not subscription_plan.stripe_customer_id:
                logger.warning(f"No Stripe customer ID for user: {user.email}")
                return None

            # Get customer's subscriptions from Stripe
            subscriptions = self.stripe_service.get_customer_subscriptions(
                subscription_plan.stripe_customer_id
            )

            if subscriptions.data:
                # Get the most recent active subscription
                active_subscription = None
                for sub in subscriptions.data:
                    if sub.status in ["active", "trialing", "past_due"]:
                        active_subscription = sub
                        break

                if active_subscription:
                    subscription_plan.update_from_stripe_subscription(
                        active_subscription
                    )
                    return subscription_plan
                else:
                    # No active subscription, downgrade to free
                    subscription_plan.plan = "free"
                    subscription_plan.status = "canceled"
                    subscription_plan.save()

            return subscription_plan

        except SubscriptionPlan.DoesNotExist:
            logger.warning(f"No subscription plan found for user: {user.email}")
            return None

    def check_subscription_limits(self, user, action):
        """Check if user can perform an action based on their subscription"""
        from .models import SubscriptionPlan

        try:
            subscription = SubscriptionPlan.objects.get(user=user)
        except SubscriptionPlan.DoesNotExist:
            subscription = SubscriptionPlan.objects.create(user=user)

        if action == "generate_resume":
            return subscription.can_generate_resume()

        # Add more action checks as needed
        return True

    def handle_resume_generation(self, user):
        """Handle resume generation and increment counter"""
        from .models import SubscriptionPlan

        try:
            subscription = SubscriptionPlan.objects.get(user=user)
        except SubscriptionPlan.DoesNotExist:
            subscription = SubscriptionPlan.objects.create(user=user)

        if not subscription.can_generate_resume():
            raise Exception("Resume generation limit exceeded")

        subscription.increment_resume_count()
        return subscription

    def get_subscription_features(self, plan_type):
        """Get features available for a subscription plan"""
        features = {
            "free": {
                "resume_limit": 3,
                "templates": ["basic"],
                "exports": ["pdf"],
                "support": "community",
            },
            "pro": {
                "resume_limit": -1,  # Unlimited
                "templates": ["basic", "premium", "executive"],
                "exports": ["pdf", "docx", "html"],
                "support": "priority",
                "custom_sections": True,
                "analytics": True,
            },
        }

        return features.get(plan_type, features["free"])

    def create_manual_payment_record(
        self, user, amount, description, payment_intent_id=None
    ):
        """Create a manual payment history record"""
        try:
            subscription_plan = SubscriptionPlan.objects.get(user=user)

            payment_history = PaymentHistory.objects.create(
                user=user,
                subscription=(
                    subscription_plan if subscription_plan.plan != "free" else None
                ),
                stripe_payment_intent_id=payment_intent_id or "",
                amount=amount,
                currency="USD",
                status="succeeded",
                description=description,
                payment_date=timezone.now(),
            )

            logger.info(f"Manual payment record created for user: {user.email}")
            return payment_history

        except Exception as e:
            logger.error(f"Error creating manual payment record: {str(e)}")
            raise

    def handle_failed_payment_recovery(self, user):
        """Handle recovery actions when a failed payment is resolved"""
        try:
            subscription_plan = SubscriptionPlan.objects.get(user=user)

            # Reactivate subscription if it was deactivated due to failed payment
            if subscription_plan.status == "past_due":
                # Sync with Stripe to get current status
                self.sync_subscription_from_stripe(user)

                # If now active, reset resume count for new billing period
                if subscription_plan.status == "active":
                    subscription_plan.reset_resume_count()
                    logger.info(f"Subscription reactivated for user: {user.email}")

            return subscription_plan

        except SubscriptionPlan.DoesNotExist:
            logger.warning(f"No subscription plan found for user: {user.email}")
            return None
        except Exception as e:
            logger.error(f"Error handling failed payment recovery: {str(e)}")
            raise


class PaymentHistoryManager:
    """Manager class for payment history operations"""

    def __init__(self):
        self.stripe_service = StripeService()

    def sync_payment_history_from_stripe(self, user, limit=20):
        """Sync payment history from Stripe for a user"""
        try:
            subscription_plan = SubscriptionPlan.objects.get(user=user)

            if not subscription_plan.stripe_customer_id:
                logger.warning(f"No Stripe customer ID for user: {user.email}")
                return []

            # Get customer's payment intents from Stripe
            payment_intents = self.stripe_service.stripe.PaymentIntent.list(
                customer=subscription_plan.stripe_customer_id, limit=limit
            )

            # Get customer's invoices from Stripe
            invoices = self.stripe_service.stripe.Invoice.list(
                customer=subscription_plan.stripe_customer_id, limit=limit
            )

            created_payments = []

            # Process payment intents
            for payment_intent in payment_intents.data:
                payment_history, created = self.create_payment_from_intent(
                    payment_intent, subscription_plan
                )
                if created:
                    created_payments.append(payment_history)

                # Process invoices
            for invoice in invoices.data:
                if invoice.status.lower() == "paid":
                    payment_history, created = self.create_payment_from_invoice(
                        invoice, subscription_plan
                    )
                    if created:
                        created_payments.append(payment_history)

            logger.info(
                f"Synced {len(created_payments)} payment records for user: {user.email}"
            )
            return created_payments

        except SubscriptionPlan.DoesNotExist:
            logger.warning(f"No subscription plan found for user: {user.email}")
            return []
        except Exception as e:
            logger.error(f"Error syncing payment history: {str(e)}")
            return []

    def create_payment_from_intent(self, payment_intent, subscription_plan):
        """Create payment history from PaymentIntent"""
        from datetime import datetime

        try:
            payment_history, created = PaymentHistory.objects.get_or_create(
                stripe_payment_intent_id=payment_intent.id,
                defaults={
                    "user": subscription_plan.user,
                    "subscription": (
                        subscription_plan if payment_intent.get("invoice") else None
                    ),
                    "stripe_invoice_id": payment_intent.get("invoice"),
                    "amount": payment_intent.amount / 100,  # Convert from cents
                    "currency": payment_intent.currency.upper(),
                    "status": self.map_payment_intent_status(payment_intent.status),
                    "description": payment_intent.description or "Payment",
                    "payment_date": datetime.fromtimestamp(
                        payment_intent.created, tz=timezone.utc
                    ),
                },
            )

            return payment_history, created

        except Exception as e:
            logger.error(f"Error creating payment from intent: {str(e)}")
            return None, False

    def create_payment_from_invoice(self, invoice, subscription_plan):
        """Create payment history from Invoice"""
        try:
            # Skip if already exists
            if PaymentHistory.objects.filter(stripe_invoice_id=invoice.id).exists():
                return None, False

            payment_history = PaymentHistory.objects.create(
                user=subscription_plan.user,
                subscription=subscription_plan,
                stripe_payment_intent_id=invoice.payment_intent or "",
                stripe_invoice_id=invoice.id,
                amount=invoice.amount_paid / 100,  # Convert from cents
                currency=invoice.currency.upper(),
                status="succeeded" if invoice.paid else "failed",
                description=self.get_invoice_description(invoice, subscription_plan),
                payment_date=timezone.datetime.fromtimestamp(
                    (
                        invoice.status_transitions.paid_at
                        if invoice.paid
                        else invoice.created
                    ),
                    tz=timezone.utc,
                ),
            )

            return payment_history, True

        except Exception as e:
            logger.error(f"Error creating payment from invoice: {str(e)}")
            return None, False

    def map_payment_intent_status(self, stripe_status):
        """Map Stripe PaymentIntent status to our status choices"""
        status_mapping = {
            "succeeded": "succeeded",
            "processing": "pending",
            "requires_payment_method": "failed",
            "requires_confirmation": "pending",
            "requires_action": "requires_action",
            "canceled": "canceled",
            "requires_capture": "pending",
        }

        return status_mapping.get(stripe_status, "pending")

    def get_invoice_description(self, invoice, subscription_plan):
        """Generate description for invoice-based payment"""
        billing_reason = getattr(invoice, "billing_reason", "unknown")

        descriptions = {
            "subscription_create": f"Initial subscription - {subscription_plan.plan}",
            "subscription_cycle": f"Subscription renewal - {subscription_plan.plan}",
            "subscription_update": f"Subscription change - {subscription_plan.plan}",
            "manual": f"Manual charge - {subscription_plan.plan}",
        }

        return descriptions.get(
            billing_reason, f"Invoice payment - {subscription_plan.plan}"
        )

    def get_payment_summary(self, user, start_date=None, end_date=None):
        """Get payment summary for a user"""
        try:
            queryset = PaymentHistory.objects.filter(user=user)

            if start_date:
                queryset = queryset.filter(payment_date__gte=start_date)
            if end_date:
                queryset = queryset.filter(payment_date__lte=end_date)

            total_payments = queryset.filter(status="succeeded")
            failed_payments = queryset.filter(status="failed")

            summary = {
                "total_amount": sum(p.amount for p in total_payments),
                "successful_payments": total_payments.count(),
                "failed_payments": failed_payments.count(),
                "total_payments": queryset.count(),
                "currency": (
                    total_payments.first().currency
                    if total_payments.exists()
                    else "USD"
                ),
                "date_range": {"start": start_date, "end": end_date},
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting payment summary: {str(e)}")
            return None
