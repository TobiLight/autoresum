from django.test import TestCase
from django.utils import timezone
from users.models import User
from .models import SubscriptionPlan, PaymentHistory, WebhookEvent
from datetime import timedelta


class SubscriptionPlanModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass", username="testuser"
        )
        self.plan = SubscriptionPlan.objects.create(
            user=self.user, plan="pro", status="active"
        )

    def test_str_representation(self):
        self.assertIn(self.user.email, str(self.plan))
        self.assertIn("pro", str(self.plan))
        self.assertIn("active", str(self.plan))

    def test_has_pro_access_active(self):
        self.plan.current_period_end = timezone.now() + timedelta(days=1)
        self.plan.save()
        self.assertTrue(self.plan.has_pro_access())

    def test_has_pro_access_expired(self):
        self.plan.current_period_end = timezone.now() - timedelta(days=1)
        self.plan.save()
        self.assertFalse(self.plan.has_pro_access())

    def test_can_generate_resume_free_limit(self):
        self.plan.plan = "free"
        self.plan.resume_count = 2
        self.plan.save()
        self.assertTrue(self.plan.can_generate_resume())
        self.plan.resume_count = 3
        self.plan.save()
        self.assertFalse(self.plan.can_generate_resume())

    def test_increment_resume_count(self):
        initial = self.plan.resume_count
        self.plan.increment_resume_count()
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.resume_count, initial + 1)

    def test_reset_resume_count(self):
        self.plan.resume_count = 2
        self.plan.save()
        self.plan.reset_resume_count()
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.resume_count, 0)


class PaymentHistoryModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="pay@example.com", password="testpass", username="tobii"
        )
        self.plan = SubscriptionPlan.objects.create(
            user=self.user, plan="pro", status="active"
        )
        self.payment_date = timezone.now()

    def test_create_payment_history(self):
        payment = PaymentHistory.objects.create(
            user=self.user,
            subscription=self.plan,
            stripe_payment_intent_id="pi_123",
            amount=5.00,
            currency="EUR",
            status="succeeded",
            payment_date=self.payment_date,
        )
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.subscription, self.plan)
        self.assertEqual(payment.amount, 5.00)
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(payment.currency, "EUR")
        self.assertEqual(payment.payment_date, self.payment_date)

    def test_payment_status_choices(self):
        statuses = ["succeeded", "pending", "failed", "canceled", "requires_action"]
        for idx, status in enumerate(statuses):
            payment = PaymentHistory.objects.create(
                user=self.user,
                subscription=self.plan,
                stripe_payment_intent_id=f"pi_{idx}",
                amount=10.00 + idx,
                currency="USD",
                status=status,
                payment_date=self.payment_date,
            )
            self.assertEqual(payment.status, status)

    def test_str_representation(self):
        payment = PaymentHistory.objects.create(
            user=self.user,
            subscription=self.plan,
            stripe_payment_intent_id="pi_str",
            amount=20.0,
            currency="USD",
            status="succeeded",
            payment_date=self.payment_date,
        )
        self.assertIn(self.user.email, str(payment))
        self.assertIn("20.0", str(payment))
        self.assertIn("succeeded", str(payment))
        self.assertTrue(self.plan.has_pro_access())

    def test_has_pro_access_pro_active(self):
        self.plan.current_period_end = timezone.now() + timedelta(days=1)
        self.plan.save()
        self.assertTrue(self.plan.has_pro_access())

    def test_has_pro_access_pro_expired(self):
        self.plan.current_period_end = timezone.now() - timedelta(days=1)
        self.plan.save()
        self.assertFalse(self.plan.has_pro_access())

    def test_has_pro_access_pro_trialing(self):
        self.plan.status = "trialing"
        self.plan.current_period_end = timezone.now() + timedelta(days=1)
        self.plan.save()
        self.assertTrue(self.plan.has_pro_access())

    def test_can_generate_resume_free_limit(self):
        self.plan.plan = "free"
        self.plan.resume_count = 2
        self.plan.save()
        self.assertTrue(self.plan.can_generate_resume())
        self.plan.resume_count = 3
        self.plan.save()
        self.assertFalse(self.plan.can_generate_resume())

    def test_can_generate_resume_pro(self):
        self.plan.current_period_end = timezone.now() + timedelta(days=1)
        self.plan.save()
        self.assertTrue(self.plan.can_generate_resume())

    def test_increment_resume_count(self):
        initial = self.plan.resume_count
        self.plan.increment_resume_count()
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.resume_count, initial + 1)

    def test_reset_resume_count(self):
        self.plan.resume_count = 2
        self.plan.save()
        self.plan.reset_resume_count()
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.resume_count, 0)


class WebhookEventModelTest(TestCase):
    def test_str_representation(self):
        event = WebhookEvent.objects.create(
            stripe_event_id="evt_123",
            event_type="invoice.payment_succeeded",
            data={"foo": "bar"},
        )
        self.assertIn("invoice.payment_succeeded", str(event))
        self.assertIn("evt_123", str(event))


# # File: subscriptions/tests/test_models.py
# # Author: Oluwatobiloba Light
# """Unit tests for subscription models"""

# import json
# from datetime import timedelta
# from decimal import Decimal
# from unittest.mock import Mock, patch

# from django.test import TestCase
# from django.utils import timezone
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError

# from subscriptions.models import SubscriptionPlan, PaymentHistory, WebhookEvent

# User = get_user_model()


# class SubscriptionPlanModelTest(TestCase):
#     """Test cases for SubscriptionPlan model"""

#     def setUp(self):
#         """Set up test data"""
#         self.user = User.objects.create_user(
#             email="test@example.com",
#             password="testpass123"
#         )
#         self.subscription = SubscriptionPlan.objects.create(
#             user=self.user,
#             plan="free"
#         )

#     def test_create_subscription_plan(self):
#         """Test creating a subscription plan"""
#         self.assertEqual(self.subscription.user, self.user)
#         self.assertEqual(self.subscription.plan, "free")
#         self.assertEqual(self.subscription.status, "active")
#         self.assertEqual(self.subscription.resume_count, 0)
#         self.assertTrue(self.subscription.is_active)
#         self.assertIsNotNone(self.subscription.created_at)
#         self.assertIsNotNone(self.subscription.modified_at)

#     def test_subscription_plan_choices(self):
#         """Test plan choices validation"""
#         # Valid choices
#         valid_plans = ["free", "pro"]
#         for plan in valid_plans:
#             subscription = SubscriptionPlan(user=self.user, plan=plan)
#             subscription.full_clean()  # Should not raise ValidationError

#     def test_billing_cycle_choices(self):
#         """Test billing cycle choices validation"""
#         valid_cycles = ["monthly", "yearly", None]
#         for cycle in valid_cycles:
#             subscription = SubscriptionPlan(
#                 user=self.user,
#                 plan="pro",
#                 billing_cycle=cycle
#             )
#             subscription.full_clean()  # Should not raise ValidationError

#     def test_status_choices(self):
#         """Test status choices validation"""
#         valid_statuses = [
#             "active", "canceled", "past_due", "unpaid",
#             "incomplete", "incomplete_expired", "trialing"
#         ]
#         for status in valid_statuses:
#             subscription = SubscriptionPlan(
#                 user=self.user,
#                 plan="pro",
#                 status=status
#             )
#             subscription.full_clean()  # Should not raise ValidationError

#     def test_has_pro_access_with_active_pro_plan(self):
#         """Test has_pro_access returns True for active pro subscription"""
#         self.subscription.plan = "pro"
#         self.subscription.status = "active"
#         self.subscription.current_period_end = timezone.now() + timedelta(days=30)
#         self.subscription.save()

#         self.assertTrue(self.subscription.has_pro_access())

#     def test_has_pro_access_with_trialing_pro_plan(self):
#         """Test has_pro_access returns True for trialing pro subscription"""
#         self.subscription.plan = "pro"
#         self.subscription.status = "trialing"
#         self.subscription.current_period_end = timezone.now() + timedelta(days=7)
#         self.subscription.save()

#         self.assertTrue(self.subscription.has_pro_access())

#     def test_has_pro_access_with_expired_pro_plan(self):
#         """Test has_pro_access returns False for expired pro subscription"""
#         self.subscription.plan = "pro"
#         self.subscription.status = "active"
#         self.subscription.current_period_end = timezone.now() - timedelta(days=1)
#         self.subscription.save()

#         self.assertFalse(self.subscription.has_pro_access())

#     def test_has_pro_access_with_free_plan(self):
#         """Test has_pro_access returns False for free plan"""
#         self.assertFalse(self.subscription.has_pro_access())

#     def test_has_pro_access_with_canceled_plan(self):
#         """Test has_pro_access returns False for canceled subscription"""
#         self.subscription.plan = "pro"
#         self.subscription.status = "canceled"
#         self.subscription.save()

#         self.assertFalse(self.subscription.has_pro_access())

#     def test_can_generate_resume_with_pro_access(self):
#         """Test can_generate_resume returns True for pro users"""
#         with patch.object(self.subscription, 'has_pro_access', return_value=True):
#             self.assertTrue(self.subscription.can_generate_resume())

#     def test_can_generate_resume_free_user_under_limit(self):
#         """Test can_generate_resume returns True for free users under limit"""
#         self.subscription.resume_count = 2
#         self.subscription.save()

#         self.assertTrue(self.subscription.can_generate_resume())

#     def test_can_generate_resume_free_user_at_limit(self):
#         """Test can_generate_resume returns False for free users at limit"""
#         self.subscription.resume_count = 3
#         self.subscription.save()

#         self.assertFalse(self.subscription.can_generate_resume())

#     def test_can_generate_resume_free_user_over_limit(self):
#         """Test can_generate_resume returns False for free users over limit"""
#         self.subscription.resume_count = 5
#         self.subscription.save()

#         self.assertFalse(self.subscription.can_generate_resume())

#     def test_can_generate_resume_count_pro(self):
#         """Test can_generate_resume_count returns '>3' for pro users"""
#         with patch.object(self.subscription, 'has_pro_access', return_value=True):
#             self.assertEqual(self.subscription.can_generate_resume_count(), "> 3")

#     def test_can_generate_resume_count_free(self):
#         """Test can_generate_resume_count returns '3' for free users"""
#         self.assertEqual(self.subscription.can_generate_resume_count(), "3")

#     def test_increment_resume_count(self):
#         """Test incrementing resume count"""
#         initial_count = self.subscription.resume_count
#         self.subscription.increment_resume_count()

#         self.subscription.refresh_from_db()
#         self.assertEqual(self.subscription.resume_count, initial_count + 1)

#     def test_reset_resume_count(self):
#         """Test resetting resume count"""
#         self.subscription.resume_count = 5
#         self.subscription.save()

#         self.subscription.reset_resume_count()

#         self.subscription.refresh_from_db()
#         self.assertEqual(self.subscription.resume_count, 0)

#     @patch('subscriptions.models.timezone')
#     def test_update_from_stripe_subscription(self, mock_timezone):
#         """Test updating subscription from Stripe data"""
#         mock_now = timezone.now()
#         mock_timezone.datetime.fromtimestamp.side_effect = [
#             mock_now,  # current_period_start
#             mock_now + timedelta(days=30),  # current_period_end
#             mock_now - timedelta(days=1),  # canceled_at
#             mock_now + timedelta(days=1),  # ended_at
#         ]

#         # Mock Stripe subscription object
#         stripe_subscription = Mock()
#         stripe_subscription.id = "sub_test123"
#         stripe_subscription.status = "active"
#         stripe_subscription.cancel_at_period_end = True
#         stripe_subscription.canceled_at = 1234567890
#         stripe_subscription.ended_at = 1234567891
#         stripe_subscription.__getitem__ = lambda self, key: {
#             "items": {
#                 "data": [{
#                     "current_period_start": 1234567890,
#                     "current_period_end": 1234567920
#                 }]
#             }
#         }[key]

#         self.subscription.update_from_stripe_subscription(stripe_subscription)

#         self.subscription.refresh_from_db()
#         self.assertEqual(self.subscription.stripe_subscription_id, "sub_test123")
#         self.assertEqual(self.subscription.status, "active")
#         self.assertTrue(self.subscription.cancel_at_period_end)
#         self.assertTrue(self.subscription.is_active)

#     def test_str_representation(self):
#         """Test string representation of subscription"""
#         expected = f"{self.user.email} - {self.subscription.plan} ({self.subscription.status})"
#         self.assertEqual(str(self.subscription), expected)

#     def test_meta_options(self):
#         """Test model meta options"""
#         self.assertEqual(SubscriptionPlan._meta.db_table, "subscriptions_subscriptionplan")
#         self.assertEqual(SubscriptionPlan._meta.verbose_name, "Subscription Plan")
#         self.assertEqual(SubscriptionPlan._meta.verbose_name_plural, "Subscription Plans")

#     def test_one_to_one_relationship_with_user(self):
#         """Test one-to-one relationship with user"""
#         # Try to create another subscription for the same user
#         with self.assertRaises(Exception):  # Should raise IntegrityError
#             SubscriptionPlan.objects.create(user=self.user, plan="pro")


# class PaymentHistoryModelTest(TestCase):
#     """Test cases for PaymentHistory model"""

#     def setUp(self):
#         """Set up test data"""
#         self.user = User.objects.create_user(
#             email="test@example.com",
#             password="testpass123"
#         )
#         self.subscription = SubscriptionPlan.objects.create(
#             user=self.user,
#             plan="pro"
#         )
#         self.payment = PaymentHistory.objects.create(
#             user=self.user,
#             subscription=self.subscription,
#             stripe_payment_intent_id="pi_test123",
#             amount=Decimal("29.99"),
#             currency="USD",
#             status="succeeded",
#             payment_date=timezone.now()
#         )

#     def test_create_payment_history(self):
#         """Test creating payment history"""
#         self.assertEqual(self.payment.user, self.user)
#         self.assertEqual(self.payment.subscription, self.subscription)
#         self.assertEqual(self.payment.stripe_payment_intent_id, "pi_test123")
#         self.assertEqual(self.payment.amount, Decimal("29.99"))
#         self.assertEqual(self.payment.currency, "USD")
#         self.assertEqual(self.payment.status, "succeeded")
#         self.assertIsNotNone(self.payment.payment_date)
#         self.assertIsNotNone(self.payment.created_at)

#     def test_payment_status_choices(self):
#         """Test payment status choices validation"""
#         valid_statuses = [
#             "succeeded", "pending", "failed", "canceled", "requires_action"
#         ]
#         for status in valid_statuses:
#             payment = PaymentHistory(
#                 user=self.user,
#                 stripe_payment_intent_id=f"pi_{status}",
#                 amount=Decimal("10.00"),
#                 currency="USD",
#                 status=status,
#                 payment_date=timezone.now()
#             )
#             payment.full_clean()  # Should not raise ValidationError

#     def test_foreign_key_relationships(self):
#         """Test foreign key relationships"""
#         self.assertEqual(self.payment.user, self.user)
#         self.assertEqual(self.payment.subscription, self.subscription)

#         # Test reverse relationships
#         self.assertIn(self.payment, self.user.payment_history.all())
#         self.assertIn(self.payment, self.subscription.payment_history.all())

#     def test_payment_without_subscription(self):
#         """Test creating payment without subscription"""
#         payment = PaymentHistory.objects.create(
#             user=self.user,
#             stripe_payment_intent_id="pi_no_sub",
#             amount=Decimal("5.00"),
#             currency="USD",
#             status="succeeded",
#             payment_date=timezone.now()
#         )

#         self.assertIsNone(payment.subscription)
#         self.assertEqual(payment.user, self.user)

#     def test_str_representation(self):
#         """Test string representation of payment"""
#         expected = f"{self.user.email} - ${self.payment.amount} ({self.payment.status})"
#         self.assertEqual(str(self.payment), expected)

#     def test_meta_options(self):
#         """Test model meta options"""
#         self.assertEqual(PaymentHistory._meta.db_table, "subscriptions_paymenthistory")
#         self.assertEqual(PaymentHistory._meta.verbose_name, "Payment History")
#         self.assertEqual(PaymentHistory._meta.verbose_name_plural, "Payment Histories")
#         self.assertEqual(PaymentHistory._meta.ordering, ["-payment_date"])

#     def test_unique_stripe_payment_intent_id(self):
#         """Test unique constraint on stripe_payment_intent_id"""
#         with self.assertRaises(Exception):  # Should raise IntegrityError
#             PaymentHistory.objects.create(
#                 user=self.user,
#                 stripe_payment_intent_id="pi_test123",  # Same as existing
#                 amount=Decimal("10.00"),
#                 currency="USD",
#                 status="succeeded",
#                 payment_date=timezone.now()
#             )

#     def test_decimal_precision(self):
#         """Test decimal field precision"""
#         payment = PaymentHistory.objects.create(
#             user=self.user,
#             stripe_payment_intent_id="pi_precision",
#             amount=Decimal("999999.99"),  # Max for 10 digits, 2 decimal places
#             currency="USD",
#             status="succeeded",
#             payment_date=timezone.now()
#         )

#         self.assertEqual(payment.amount, Decimal("999999.99"))

#     def test_cascade_delete_user(self):
#         """Test cascade delete when user is deleted"""
#         payment_id = self.payment.id
#         self.user.delete()

#         with self.assertRaises(PaymentHistory.DoesNotExist):
#             PaymentHistory.objects.get(id=payment_id)

#     def test_cascade_delete_subscription(self):
#         """Test cascade delete when subscription is deleted"""
#         payment_id = self.payment.id
#         self.subscription.delete()

#         with self.assertRaises(PaymentHistory.DoesNotExist):
#             PaymentHistory.objects.get(id=payment_id)


# class WebhookEventModelTest(TestCase):
#     """Test cases for WebhookEvent model"""

#     def setUp(self):
#         """Set up test data"""
#         self.webhook_data = {
#             "id": "evt_test123",
#             "object": "event",
#             "type": "customer.subscription.created",
#             "data": {"object": {"id": "sub_test"}}
#         }

#         self.webhook = WebhookEvent.objects.create(
#             stripe_event_id="evt_test123",
#             event_type="customer.subscription.created",
#             data=self.webhook_data
#         )

#     def test_create_webhook_event(self):
#         """Test creating webhook event"""
#         self.assertEqual(self.webhook.stripe_event_id, "evt_test123")
#         self.assertEqual(self.webhook.event_type, "customer.subscription.created")
#         self.assertEqual(self.webhook.data, self.webhook_data)
#         self.assertFalse(self.webhook.processed)
#         self.assertIsNone(self.webhook.processing_error)
#         self.assertIsNone(self.webhook.processed_at)
#         self.assertIsNotNone(self.webhook.created_at)

#     def test_json_field_storage(self):
#         """Test JSON field storage and retrieval"""
#         complex_data = {
#             "nested": {"key": "value"},
#             "array": [1, 2, 3],
#             "boolean": True,
#             "null": None
#         }

#         webhook = WebhookEvent.objects.create(
#             stripe_event_id="evt_complex",
#             event_type="test.event",
#             data=complex_data
#         )

#         webhook.refresh_from_db()
#         self.assertEqual(webhook.data, complex_data)

#     def test_processed_webhook(self):
#         """Test marking webhook as processed"""
#         self.webhook.processed = True
#         self.webhook.processed_at = timezone.now()
#         self.webhook.save()

#         self.webhook.refresh_from_db()
#         self.assertTrue(self.webhook.processed)
#         self.assertIsNotNone(self.webhook.processed_at)

#     def test_webhook_with_error(self):
#         """Test webhook with processing error"""
#         error_message = "Test processing error"
#         self.webhook.processing_error = error_message
#         self.webhook.processed = False
#         self.webhook.save()

#         self.webhook.refresh_from_db()
#         self.assertEqual(self.webhook.processing_error, error_message)
#         self.assertFalse(self.webhook.processed)

#     def test_str_representation(self):
#         """Test string representation of webhook"""
#         expected = f"{self.webhook.event_type} - {self.webhook.stripe_event_id}"
#         self.assertEqual(str(self.webhook), expected)

#     def test_meta_options(self):
#         """Test model meta options"""
#         self.assertEqual(WebhookEvent._meta.db_table, "subscriptions_webhookevent")
#         self.assertEqual(WebhookEvent._meta.verbose_name, "Webhook Event")
#         self.assertEqual(WebhookEvent._meta.verbose_name_plural, "Webhook Events")
#         self.assertEqual(WebhookEvent._meta.ordering, ["-created_at"])

#     def test_unique_stripe_event_id(self):
#         """Test unique constraint on stripe_event_id"""
#         with self.assertRaises(Exception):  # Should raise IntegrityError
#             WebhookEvent.objects.create(
#                 stripe_event_id="evt_test123",  # Same as existing
#                 event_type="duplicate.event",
#                 data={"test": "data"}
#             )

#     def test_webhook_event_types(self):
#         """Test various webhook event types"""
#         event_types = [
#             "checkout.session.completed",
#             "customer.subscription.created",
#             "customer.subscription.updated",
#             "customer.subscription.deleted",
#             "invoice.payment_succeeded",
#             "invoice.payment_failed"
#         ]

#         for i, event_type in enumerate(event_types):
#             webhook = WebhookEvent.objects.create(
#                 stripe_event_id=f"evt_{i}",
#                 event_type=event_type,
#                 data={"test": "data"}
#             )
#             self.assertEqual(webhook.event_type, event_type)


# class ModelRelationshipTest(TestCase):
#     """Test relationships between models"""

#     def setUp(self):
#         """Set up test data"""
#         self.user = User.objects.create_user(
#             email="test@example.com",
#             password="testpass123"
#         )
#         self.subscription = SubscriptionPlan.objects.create(
#             user=self.user,
#             plan="pro"
#         )

#     def test_user_subscription_relationship(self):
#         """Test user-subscription one-to-one relationship"""
#         # Test forward relationship
#         self.assertEqual(self.subscription.user, self.user)

#         # Test reverse relationship
#         self.assertEqual(self.user.subscription, self.subscription)

#     def test_payment_history_relationships(self):
#         """Test payment history relationships"""
#         payment1 = PaymentHistory.objects.create(
#             user=self.user,
#             subscription=self.subscription,
#             stripe_payment_intent_id="pi_1",
#             amount=Decimal("29.99"),
#             currency="USD",
#             status="succeeded",
#             payment_date=timezone.now()
#         )

#         payment2 = PaymentHistory.objects.create(
#             user=self.user,
#             subscription=self.subscription,
#             stripe_payment_intent_id="pi_2",
#             amount=Decimal("29.99"),
#             currency="USD",
#             status="succeeded",
#             payment_date=timezone.now()
#         )

#         # Test user relationship
#         user_payments = self.user.payment_history.all()
#         self.assertIn(payment1, user_payments)
#         self.assertIn(payment2, user_payments)

#         # Test subscription relationship
#         subscription_payments = self.subscription.payment_history.all()
#         self.assertIn(payment1, subscription_payments)
#         self.assertIn(payment2, subscription_payments)

#     def test_related_name_usage(self):
#         """Test related name usage"""
#         # Create some payments
#         for i in range(3):
#             PaymentHistory.objects.create(
#                 user=self.user,
#                 subscription=self.subscription,
#                 stripe_payment_intent_id=f"pi_{i}",
#                 amount=Decimal("10.00"),
#                 currency="USD",
#                 status="succeeded",
#                 payment_date=timezone.now()
#             )

#         # Test related names work correctly
#         self.assertEqual(self.user.payment_history.count(), 3)
#         self.assertEqual(self.subscription.payment_history.count(), 3)
#         self.assertEqual(self.user.subscription, self.subscription)
