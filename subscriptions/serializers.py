# File: subscriptions/serializers.py
# Author: Oluwatobiloba Light
"""STRIPE SUBSCRIPTION SERIALIZER"""

from rest_framework import serializers
from .models import SubscriptionPlan, PaymentHistory


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    has_pro_access = serializers.ReadOnlyField()
    can_generate_resume = serializers.ReadOnlyField()
    days_until_renewal = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "plan",
            "billing_cycle",
            "status",
            "resume_count",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "has_pro_access",
            "can_generate_resume",
            "can_generate_resume_count",
            "days_until_renewal",
            "created_at",
            "modified_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "resume_count",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "created_at",
            "modified_at",
        ]

    def get_days_until_renewal(self, obj):
        """Calculate days until next billing cycle"""
        if obj.current_period_end:
            from django.utils import timezone

            delta = obj.current_period_end - timezone.now()
            return delta.days if delta.days > 0 else 0
        return None


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = [
            "id",
            "amount",
            "currency",
            "status",
            "description",
            "payment_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentHistorySummarySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError("start_date must be before end_date.")
        return data


class CreateCheckoutSessionSerializer(serializers.Serializer):
    """Serializer for creating Stripe checkout sessions"""

    price_id = serializers.CharField(max_length=255, required=True)
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)

    def validate_price_id(self, value):
        """Validate that the price_id is one of our valid subscription prices"""
        from django.conf import settings

        valid_price_ids = [
            settings.STRIPE_PRO_MONTHLY_PRODUCT_ID,
            settings.STRIPE_PRO_YEARLY_PRODUCT_ID,
        ]

        if value not in valid_price_ids:
            raise serializers.ValidationError("Invalid price ID..")

        return value


class ManageSubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription management actions"""

    action = serializers.ChoiceField(
        choices=[
            ("cancel", "Cancel Subscription"),
            ("reactivate", "Reactivate Subscription"),
            ("update_payment_method", "Update Payment Method"),
        ]
    )

    cancel_at_period_end = serializers.BooleanField(required=False, default=True)


class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """Minimal serializer for subscription status checks"""

    has_pro_access = serializers.ReadOnlyField()
    can_generate_resume = serializers.ReadOnlyField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "plan",
            "status",
            "resume_count",
            "has_pro_access",
            "can_generate_resume",
            "can_generate_resume_count",
        ]


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual payment view"""
    
    subscription_plan = serializers.CharField(source='subscription.plan', read_only=True)
    subscription_billing_cycle = serializers.CharField(source='subscription.billing_cycle', read_only=True)
    subscription_status = serializers.CharField(source='subscription.status', read_only=True)
    days_since_payment = serializers.SerializerMethodField()
    formatted_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentHistory
        fields = [
            "id",
            "amount",
            "formatted_amount",
            "currency",
            "status",
            "description",
            "payment_date",
            "days_since_payment",
            "stripe_payment_intent_id",
            "stripe_invoice_id",
            "subscription_plan",
            "subscription_billing_cycle", 
            "subscription_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_days_since_payment(self, obj):
        """Calculate days since payment"""
        from django.utils import timezone
        if obj.payment_date:
            delta = timezone.now() - obj.payment_date
            return delta.days
        return None

    def get_formatted_amount(self, obj):
        """Format amount with currency symbol"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'NGN': '₦'
        }
        symbol = currency_symbols.get(obj.currency, obj.currency + ' ')
        return f"{symbol}{obj.amount:.2f}"


class PaymentSearchSerializer(serializers.Serializer):
    """Serializer for payment search/filter parameters"""
    
    status = serializers.ChoiceField(
        choices=[
            ("succeeded", "Succeeded"),
            ("pending", "Pending"),
            ("failed", "Failed"),
            ("canceled", "Canceled"),
            ("requires_action", "Requires Action"),
        ],
        required=False
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    min_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        min_amount = data.get('min_amount')
        max_amount = data.get('max_amount')
        
        if start and end and start > end:
            raise serializers.ValidationError("start_date must be before end_date.")
            
        if min_amount and max_amount and min_amount > max_amount:
            raise serializers.ValidationError("min_amount must be less than max_amount.")
            
        return data