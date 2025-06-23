# File: subscriptions/urls.py
# Author: Oluwatobiloba Light
"""Subscription URL"""
from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    # Subscription management
    path("", views.SubscriptionDetailView.as_view(), name="subscription_detail"),
    path("status", views.subscription_status, name="subscription_status"),
    path("manage", views.ManageSubscriptionView.as_view(), name="manage_subscription"),
    # Stripe integration
    path(
        "create-checkout-session",
        views.CreateCheckoutSessionView.as_view(),
        name="create_checkout_session",
    ),
    path(
        "create-portal-session",
        views.CreatePortalSessionView.as_view(),
        name="create_portal_session",
    ),
    path("webhook", views.StripeWebhookView.as_view(), name="stripe_webhook"),
    # Payment verification endpoints
    path(
        "verify-payment",
        views.VerifyCheckoutSessionView.as_view(),
        name="verify_payment",
    ),
    path("payment-success", views.PaymentSuccessView.as_view(), name="payment_success"),
    path("payment-cancel", views.PaymentCancelView.as_view(), name="payment_cancel"),
    path("payment-status", views.PaymentStatusView.as_view(), name="payment_status"),
    path(
        "refresh-subscription",
        views.RefreshSubscriptionView.as_view(),
        name="refresh_subscription",
    ),
    # Payment history
    path("payments", views.PaymentHistoryView.as_view(), name="payment_history"),
    path("payments/<int:id>", views.PaymentDetailView.as_view(), name="payment_detail"),
    path("payments/<int:payment_id>/invoice", views.PaymentInvoiceView.as_view(), name="payment_invoice"),
    path("payments/summary", views.PaymentHistorySummaryView.as_view(), name="payment_history_summary"),
]
