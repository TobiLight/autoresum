#!/usr/bin/env python3
# File: subscriptions/models.py
# Author: Oluwatobiloba Light
"""Autoresume Subscription Model"""
from django.db import models
from datetime import timezone as dt_timezone
from django.utils import timezone
from users.models import User


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
    ]

    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("past_due", "Past Due"),
        ("unpaid", "Unpaid"),
        ("incomplete", "Incomplete"),
        ("incomplete_expired", "Incomplete Expired"),
        ("trialing", "Trialing"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")

    billing_cycle = models.CharField(
        max_length=20, choices=BILLING_CYCLE_CHOICES, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    resume_count = models.PositiveIntegerField(default=0)

    # Stripe fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)

    # Subscription dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Legacy field - keeping for backward compatibility
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions_subscriptionplan"
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def has_pro_access(self):
        """Check if user has active pro subscription"""
        if self.plan != "pro":
            return False

        # Check if subscription is active and not expired
        if self.status in ["active", "trialing"]:
            if self.current_period_end:
                return timezone.now() <= self.current_period_end
            return True

        return False

    def can_generate_resume(self):
        """Check if user can generate a resume"""
        if self.has_pro_access():
            return True

        # Free users can generate up to 3 resumes
        return self.resume_count < 3

    def can_generate_resume_count(self):
        """Check if user can generate a resume"""
        return "> 3" if self.has_pro_access() else "3"

    def increment_resume_count(self):
        """Increment the resume count"""
        self.resume_count += 1
        self.save(update_fields=["resume_count", "modified_at"])

    def reset_resume_count(self):
        """Reset resume count (useful for new billing periods)"""
        self.resume_count = 0
        self.save(update_fields=["resume_count", "modified_at"])

    def update_from_stripe_subscription(self, stripe_subscription):
        """Update subscription from Stripe subscription object"""
        self.stripe_subscription_id = stripe_subscription.id
        self.status = stripe_subscription.status
        self.current_period_start = timezone.datetime.fromtimestamp(
            stripe_subscription["items"]["data"][0].current_period_start,
            tz=dt_timezone.utc,
        )
        self.current_period_end = timezone.datetime.fromtimestamp(
            stripe_subscription["items"]["data"][0].current_period_end,
            tz=dt_timezone.utc,
        )
        self.cancel_at_period_end = stripe_subscription.cancel_at_period_end

        if stripe_subscription.canceled_at:
            self.canceled_at = timezone.datetime.fromtimestamp(
                stripe_subscription.canceled_at, tz=dt_timezone.utc
            )

        if stripe_subscription.ended_at:
            self.ended_at = timezone.datetime.fromtimestamp(
                stripe_subscription.ended_at, tz=dt_timezone.utc
            )

        self.is_active = self.status in ["active", "trialing"]

        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.plan} ({self.status})"


class PaymentHistory(models.Model):
    """Track payment history for subscriptions"""

    PAYMENT_STATUS_CHOICES = [
        ("succeeded", "Succeeded"),
        ("pending", "Pending"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
        ("requires_action", "Requires Action"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payment_history"
    )
    subscription = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="payment_history",
        null=True,
        blank=True,
    )

    # Stripe fields
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_invoice_id = models.CharField(max_length=255, null=True, blank=True)

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    description = models.TextField(blank=True, null=True)

    # Timestamps
    payment_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions_paymenthistory"
        verbose_name = "Payment History"
        verbose_name_plural = "Payment Histories"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.user.email} - ${self.amount} ({self.status})"


class WebhookEvent(models.Model):
    """Track Stripe webhook events for debugging and audit purposes"""

    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions_webhookevent"
        verbose_name = "Webhook Event"
        verbose_name_plural = "Webhook Events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"
