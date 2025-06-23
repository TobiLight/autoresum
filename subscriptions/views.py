# File: subscriptions/views.py
# Author: Oluwatobiloba Light

from datetime import timezone
import logging
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveAPIView


from .models import SubscriptionPlan, PaymentHistory, WebhookEvent
from .serializers import (
    PaymentDetailSerializer,
    PaymentHistorySummarySerializer,
    SubscriptionPlanSerializer,
    PaymentHistorySerializer,
    CreateCheckoutSessionSerializer,
    ManageSubscriptionSerializer,
    SubscriptionStatusSerializer,
)
from .utils import PaymentHistoryManager, StripeService, SubscriptionManager

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionDetailView(RetrieveUpdateAPIView):
    """
    Get or update user's subscription details
    """

    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        subscription, created = SubscriptionPlan.objects.get_or_create(
            user=self.request.user
        )
        if created:
            logger.info(f"Created new subscription for user: {self.request.user.email}")
        return subscription


class CreateCheckoutSessionView(CreateAPIView):
    """
    Create a Stripe checkout session for subscription
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CreateCheckoutSessionSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe_service = StripeService()

            # Use your API endpoints as default success/cancel URLs
            base_url = request.build_absolute_uri("/").rstrip("/")
            default_success_url = f"{base_url}/api/subscription/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
            default_cancel_url = f"{base_url}/api/subscription/payment-cancel"

            session = stripe_service.create_checkout_session(
                user=request.user,
                price_id=serializer.validated_data["price_id"],
                success_url=serializer.validated_data.get(
                    "success_url", default_success_url
                ),
                cancel_url=serializer.validated_data.get(
                    "cancel_url", default_cancel_url
                ),
            )

            return Response(
                {
                    "checkout_url": session.url,
                    "session_id": session.id,
                    "success_url": session.success_url,
                    "cancel_url": session.cancel_url,
                    "verification_endpoint": f"{base_url}/api/subscription/verify-payment?session_id={session.id}",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return Response(
                {"error": "Failed to create checkout session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreatePortalSessionView(APIView):
    """
    Create a Stripe customer portal session for subscription management
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = SubscriptionPlan.objects.get(user=request.user)

            if not subscription.stripe_customer_id:
                return Response(
                    {"error": "No Stripe customer found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            stripe_service = StripeService()
            session = stripe_service.create_portal_session(
                customer_id=subscription.stripe_customer_id,
                return_url=request.data.get(
                    "return_url", "http://localhost:8000/api/subscription"
                ),
            )

            return Response({"portal_url": session.url})

        except SubscriptionPlan.DoesNotExist:
            # Create default free subscription if none exists
            subscription = SubscriptionPlan.objects.create(user=request.user)
            serializer = SubscriptionStatusSerializer(subscription)
            return Response(serializer.data)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    Handle Stripe webhook events
    """

    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            logger.error("Invalid payload in webhook")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return HttpResponse(status=400)

        # Store webhook event for audit purposes
        webhook_event, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event["id"],
            defaults={
                "event_type": event["type"],
                "data": event["data"],
            },
        )

        if not created and webhook_event.processed:
            logger.info(f"Webhook event {event['id']} already processed")
            return HttpResponse(status=200)

        try:
            self.process_webhook_event(event)
            webhook_event.processed = True
            webhook_event.processing_error = None

        except Exception as e:
            logger.error(f"Error processing webhook {event['id']}: {str(e)}")
            webhook_event.processing_error = str(e)
            return HttpResponse(status=500)

        finally:
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

        return HttpResponse(status=200)

    def process_webhook_event(self, event):
        """Process different types of webhook events"""
        from django.utils import timezone

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self.handle_checkout_completed(data)

        elif event_type == "customer.subscription.created":
            self.handle_subscription_created(data)

        elif event_type == "customer.subscription.updated":
            self.handle_subscription_updated(data)

        elif event_type == "customer.subscription.deleted":
            self.handle_subscription_deleted(data)

        elif event_type == "invoice.payment_succeeded":
            self.handle_payment_succeeded(data)

        elif event_type == "invoice.payment_failed":
            self.handle_payment_failed(data)

        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

    def handle_checkout_completed(self, session):
        """Handle completed checkout session"""
        try:
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")

            if subscription_id and customer_id:
                # Retrieve the subscription from Stripe
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)

                # Find user by customer ID or email
                try:
                    subscription_plan = SubscriptionPlan.objects.get(
                        stripe_customer_id=customer_id
                    )
                except SubscriptionPlan.DoesNotExist:
                    # Try to find by email if customer_id lookup fails
                    customer = stripe.Customer.retrieve(customer_id)
                    from users.models import User

                    user = User.objects.get(email=customer.email)
                    subscription_plan = SubscriptionPlan.objects.get(user=user)

                # Update subscription with Stripe data
                subscription_plan.stripe_customer_id = customer_id
                subscription_plan.plan = "pro"
                subscription_plan.update_from_stripe_subscription(stripe_subscription)

                # Determine billing cycle from price
                price_id = stripe_subscription["items"]["data"][0]["price"]["id"]
                if price_id == settings.STRIPE_PRO_MONTHLY_PRICE_ID:
                    subscription_plan.billing_cycle = "monthly"
                elif price_id == settings.STRIPE_PRO_YEARLY_PRICE_ID:
                    subscription_plan.billing_cycle = "yearly"

                subscription_plan.save()

                logger.info(
                    f"Subscription activated for user: {subscription_plan.user.email}"
                )

        except Exception as e:
            logger.error(f"Error handling checkout completed: {str(e)}")
            raise

    def handle_subscription_created(self, subscription):
        """Handle subscription creation"""
        try:
            customer_id = subscription["customer"]
            subscription_plan = SubscriptionPlan.objects.get(
                stripe_customer_id=customer_id
            )
            subscription_plan.plan = "pro"
            subscription_plan.update_from_stripe_subscription(subscription)

            logger.info(
                f"Subscription created for user: {subscription_plan.user.email}"
            )

        except SubscriptionPlan.DoesNotExist:
            logger.warning(f"No subscription plan found for customer: {customer_id}")

    def handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        try:
            subscription_plan = SubscriptionPlan.objects.get(
                stripe_subscription_id=subscription["id"]
            )
            subscription_plan.update_from_stripe_subscription(subscription)

            # If subscription is canceled, downgrade to free
            if subscription["status"] in ["canceled", "unpaid"]:
                subscription_plan.plan = "free"
                subscription_plan.save()

            logger.info(
                f"Subscription updated for user: {subscription_plan.user.email}"
            )

        except SubscriptionPlan.DoesNotExist:
            logger.warning(
                f"No subscription plan found for subscription: {subscription['id']}"
            )

    def handle_subscription_deleted(self, subscription):
        """Handle subscription deletion"""
        try:
            subscription_plan = SubscriptionPlan.objects.get(
                stripe_subscription_id=subscription["id"]
            )
            subscription_plan.plan = "free"
            subscription_plan.status = "canceled"
            subscription_plan.is_active = False
            subscription_plan.stripe_subscription_id = None
            subscription_plan.save()

            logger.info(
                f"Subscription deleted for user: {subscription_plan.user.email}"
            )

        except SubscriptionPlan.DoesNotExist:
            logger.warning(
                f"No subscription plan found for subscription: {subscription['id']}"
            )

    def handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            subscription_id = invoice.get("subscription")
            if subscription_id:
                subscription_plan = SubscriptionPlan.objects.get(
                    stripe_subscription_id=subscription_id
                )

                # Create payment history record
                PaymentHistory.objects.create(
                    user=subscription_plan.user,
                    subscription=subscription_plan,
                    stripe_payment_intent_id=invoice["payment_intent"],
                    stripe_invoice_id=invoice["id"],
                    amount=invoice["amount_paid"] / 100,  # Convert from cents
                    currency=invoice["currency"].upper(),
                    status="succeeded",
                    description=f"Subscription payment - {subscription_plan.plan}",
                    payment_date=timezone.datetime.fromtimestamp(
                        invoice["status_transitions"]["paid_at"], tz=timezone.utc
                    ),
                )

                logger.info(
                    f"Payment succeeded for user: {subscription_plan.user.email}"
                )

        except Exception as e:
            logger.error(f"Error handling payment succeeded: {str(e)}")

    def handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            subscription_id = invoice.get("subscription")
            if subscription_id:
                subscription_plan = SubscriptionPlan.objects.get(
                    stripe_subscription_id=subscription_id
                )

                # Create payment history record
                PaymentHistory.objects.create(
                    user=subscription_plan.user,
                    subscription=subscription_plan,
                    stripe_payment_intent_id=invoice.get("payment_intent", ""),
                    stripe_invoice_id=invoice["id"],
                    amount=invoice["amount_due"] / 100,  # Convert from cents
                    currency=invoice["currency"].upper(),
                    status="failed",
                    description=f"Failed subscription payment - {subscription_plan.plan}",
                    payment_date=timezone.datetime.fromtimestamp(
                        invoice["created"], tz=timezone.utc
                    ),
                )

                logger.warning(
                    f"Payment failed for user: {subscription_plan.user.email}"
                )

        except Exception as e:
            logger.error(f"Error handling payment failed: {str(e)}")
            return Response(
                {"error": "No subscription found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating portal session: {str(e)}")
            return Response(
                {"error": "Failed to create portal session"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ManageSubscriptionView(APIView):
    """
    Manage subscription (cancel, reactivate, etc.)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ManageSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = SubscriptionPlan.objects.get(user=request.user)
            stripe_service = StripeService()
            action = serializer.validated_data["action"]

            if action == "cancel":
                result = stripe_service.cancel_subscription(
                    subscription_id=subscription.stripe_subscription_id,
                    at_period_end=serializer.validated_data.get(
                        "cancel_at_period_end", True
                    ),
                )
                subscription.cancel_at_period_end = result.cancel_at_period_end
                subscription.save()

                return Response(
                    {
                        "message": "Subscription cancelled successfully",
                        "cancel_at_period_end": result.cancel_at_period_end,
                    }
                )

            elif action == "reactivate":
                result = stripe_service.reactivate_subscription(
                    subscription_id=subscription.stripe_subscription_id
                )
                subscription.cancel_at_period_end = False
                subscription.save()

                return Response({"message": "Subscription reactivated successfully"})

            else:
                return Response(
                    {"error": "Action not implemented"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "No subscription found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error managing subscription: {str(e)}")
            return Response(
                {"error": "Failed to manage subscription"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """
    Quick endpoint to check subscription status
    """
    try:
        subscription = SubscriptionPlan.objects.get(user=request.user)
        serializer = SubscriptionStatusSerializer(subscription)
        return Response(serializer.data)
    except SubscriptionPlan.DoesNotExist:
        return Response(
            {"error": "No subscription found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error managing subscription: {str(e)}")
        return Response(
            {"error": "Failed to manage subscription"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Add these views to your views.py file
class VerifyCheckoutSessionView(APIView):
    """
    Verify checkout session status after Stripe redirect
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve the session from Stripe
            session = stripe.checkout.Session.retrieve(
                session_id, expand=["subscription", "customer"]
            )

            # Verify the session belongs to the authenticated user
            subscription_plan = SubscriptionPlan.objects.get(user=request.user)
            # payment_

            if session.customer.id != subscription_plan.stripe_customer_id:
                return Response(
                    {"error": "Session does not belong to authenticated user"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check session status
            if session.payment_status == "paid":
                # Payment successful
                if session.subscription:
                    # Subscription payment
                    stripe_subscription = session.subscription

                    # Update local subscription data
                    subscription_plan.stripe_subscription_id = stripe_subscription.id
                    subscription_plan.plan = "pro"
                    subscription_plan.update_from_stripe_subscription(
                        stripe_subscription
                    )

                    # Determine billing cycle from price
                    price_id = stripe_subscription["items"]["data"][0].price.id
                    if price_id == settings.STRIPE_PRO_MONTHLY_PRODUCT_ID:
                        subscription_plan.billing_cycle = "monthly"
                    elif price_id == settings.STRIPE_PRO_YEARLY_PRODUCT_ID:
                        subscription_plan.billing_cycle = "yearly"

                    subscription_plan.save()

                return Response(
                    {
                        "status": "success",
                        "payment_status": session.payment_status,
                        "subscription_status": (
                            session.subscription.status
                            if session.subscription
                            else None
                        ),
                        "customer_email": session.customer_email,
                        "amount_total": session.amount_total
                        / 100,  # Convert from cents
                        "currency": session.currency,
                        "subscription": SubscriptionPlanSerializer(
                            subscription_plan
                        ).data,
                    }
                )

            elif session.payment_status == "unpaid":
                return Response(
                    {
                        "status": "failed",
                        "payment_status": session.payment_status,
                        "customer_email": session.customer_email,
                        "error": "Payment was not completed",
                    }
                )

            else:
                return Response(
                    {
                        "status": "pending",
                        "payment_status": session.payment_status,
                        "customer_email": session.customer_email,
                    }
                )

        except stripe.error.InvalidRequestError:
            return Response(
                {"error": "Invalid session ID"}, status=status.HTTP_400_BAD_REQUEST
            )
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "No subscription found for user"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error verifying checkout session: {str(e)}")
            return Response(
                {"error": "Failed to verify payment status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentSuccessView(APIView):
    """
    Handle successful payment redirect
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use the verify endpoint logic
            verify_view = VerifyCheckoutSessionView()
            verify_view.request = request
            response = verify_view.get(request)

            if response.status_code == 200 and response.data.get("status") == "success":
                return Response(
                    {
                        "message": "Payment successful! Your subscription has been activated.",
                        "subscription": response.data.get("subscription"),
                        "next_steps": [
                            "Your account has been upgraded to Pro",
                            "You can now access all premium features",
                            "Check your email for payment confirmation",
                        ],
                    }
                )
            else:
                return response

        except Exception as e:
            logger.error(f"Error processing payment success: {str(e)}")
            return Response(
                {"error": "Failed to process successful payment"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentCancelView(APIView):
    """
    Handle cancelled payment redirect
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "status": "cancelled",
                "message": "Payment was cancelled. No charges were made to your account.",
                "subscription": SubscriptionPlanSerializer(
                    SubscriptionPlan.objects.get(user=request.user)
                ).data,
                "next_steps": [
                    "You can try again anytime",
                    "Your current plan remains unchanged",
                    "Contact support if you need assistance",
                ],
            }
        )


class PaymentStatusView(APIView):
    """
    Get current payment/subscription status
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = SubscriptionPlan.objects.get(user=request.user)

            # Sync with Stripe to get latest status
            if subscription.stripe_subscription_id:
                try:
                    stripe_subscription = stripe.Subscription.retrieve(
                        subscription.stripe_subscription_id
                    )
                    subscription.update_from_stripe_subscription(stripe_subscription)
                except stripe.error.InvalidRequestError:
                    logger.warning(
                        f"Invalid Stripe subscription ID: {subscription.stripe_subscription_id}"
                    )

            return Response(
                {
                    "subscription": SubscriptionPlanSerializer(subscription).data,
                    "recent_payments": PaymentHistorySerializer(
                        subscription.payment_history.all()[:5], many=True
                    ).data,
                }
            )

        except SubscriptionPlan.DoesNotExist:
            # Create default subscription if none exists
            subscription = SubscriptionPlan.objects.create(user=request.user)
            return Response(
                {
                    "subscription": SubscriptionPlanSerializer(subscription).data,
                    "recent_payments": [],
                }
            )


class RefreshSubscriptionView(APIView):
    """
    Manually refresh subscription data from Stripe
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription_manager = SubscriptionManager()
            subscription = subscription_manager.sync_subscription_from_stripe(
                request.user
            )

            if subscription:
                return Response(
                    {
                        "message": "Subscription data refreshed successfully",
                        "subscription": SubscriptionPlanSerializer(subscription).data,
                    }
                )
            else:
                return Response(
                    {"error": "No subscription data found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            logger.error(f"Error refreshing subscription: {str(e)}")
            return Response(
                {"error": "Failed to refresh subscription data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentHistoryView(ListAPIView):
    """
    List user's payment history
    """

    serializer_class = PaymentHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentHistory.objects.filter(user=self.request.user)


class PaymentHistorySummaryView(APIView):
    """
    API endpoint to retrieve a summary of the authenticated user's payment history.
    """

    permission_classes = [IsAuthenticated]
    payment_serializer = PaymentHistorySummarySerializer

    def get(self, request):
        try:
            queryset = PaymentHistory.objects.filter(user=request.user)
            serializer = self.payment_serializer(data=request.query_params)

            if serializer.is_valid():
                start_date = serializer.validated_data["start_date"]
                end_date = serializer.validated_data["end_date"]

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

                return Response({**summary}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error getting payment summary: {str(e)}")
            return Response(
                {"error": "Failed to fetch payment summary"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class PaymentDetailView(RetrieveAPIView):
    """
    Retrieve details of a specific payment
    """
    serializer_class = PaymentDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Ensure users can only access their own payments
        return PaymentHistory.objects.filter(user=self.request.user)

    def get_object(self):
        try:
            payment = self.get_queryset().get(id=self.kwargs['id'])
            return payment
        except PaymentHistory.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Payment not found or you don't have permission to view it.")

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add additional payment details"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Add additional details if needed
        payment_data = serializer.data
        
        # You can add more details here like related subscription info
        if instance.subscription:
            payment_data['subscription_details'] = {
                'plan': instance.subscription.plan,
                'billing_cycle': instance.subscription.billing_cycle,
                'status': instance.subscription.status
            }
        
        # Add Stripe invoice URL if available
        print("instance", instance.stripe_invoice_id)
        if instance.stripe_invoice_id:
            try:
                import stripe
                invoice = stripe.Invoice.retrieve(instance.stripe_invoice_id)
                print(invoice)
                payment_data['invoice_pdf'] = invoice.invoice_pdf
                payment_data['invoice_url'] = invoice.hosted_invoice_url
            except Exception as e:
                logger.warning(f"Could not retrieve Stripe invoice details: {str(e)}")
        return Response({
            'payment': payment_data,
            'meta': {
                'can_download_invoice': bool(instance.stripe_invoice_id),
                'payment_method': 'Credit Card',  # You can enhance this based on Stripe data
                'refundable': instance.status == 'succeeded' and instance.subscription and instance.subscription.has_pro_access()
            }
        })


class PaymentInvoiceView(APIView):
    """
    Get invoice details for a specific payment
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = PaymentHistory.objects.get(
                id=payment_id, 
                user=request.user
            )
            
            if not payment.stripe_invoice_id:
                return Response(
                    {"error": "No invoice available for this payment"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Retrieve invoice from Stripe
            invoice = stripe.Invoice.retrieve(payment.stripe_invoice_id)

            
            return Response({
                'invoice_id': invoice.id,
                'invoice_number': invoice.number,
                'invoice_pdf': invoice.invoice_pdf,
                'invoice_url': invoice.hosted_invoice_url,
                'amount_paid': invoice.amount_paid / 100,
                'currency': invoice.currency.upper(),
                'status': invoice.status,
                'created': invoice.created,
                'due_date': invoice.due_date,
                # 'payment_intent': invoice.payment_intent
            })
            
        except PaymentHistory.DoesNotExist:
            return Response(
                {"error": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.InvalidRequestError:
            return Response(
                {"error": "Invoice not found in Stripe"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving invoice: {str(e)}")
            return Response(
                {"error": "Failed to retrieve invoice"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )