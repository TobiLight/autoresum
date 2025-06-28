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


