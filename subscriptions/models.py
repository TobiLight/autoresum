# File: subscriptions/models.py
# Author: Oluwatobiloba Light
"""Autoresume Subscription Model"""
from django.db import models
from users.models import User


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    resume_count = models.PositiveIntegerField(default=0)

    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def has_pro_access(self):
        return self.plan == "pro" and self.is_active

    def can_generate_resume(self):
        if self.plan == "pro" and self.is_active:
            return True
        return self.resume_count < 3

    def increment_resume_count(self):
        self.resume_count += 1
        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.plan}"
