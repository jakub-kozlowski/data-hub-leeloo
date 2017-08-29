from unittest import mock
import pytest

from django.conf import settings

from datahub.core.test_utils import synchronous_executor_submit
from datahub.omis.market.models import Market
from datahub.omis.order.test.factories import OrderFactory

from ..client import Notify


pytestmark = pytest.mark.django_db


@pytest.mark.skipif(
    not settings.OMIS_NOTIFICATION_TEST_API_KEY,
    reason='`settings.OMIS_NOTIFICATION_TEST_API_KEY` not set (optional).'
)
@mock.patch('datahub.core.utils.executor.submit', synchronous_executor_submit)
class TestTemplates:
    """
    These tests are going to be run only if `OMIS_NOTIFICATION_TEST_API_KEY` is set
    and it's meant to check that the templates in GOV.UK notifications have not been
    changed.

    If `OMIS_NOTIFICATION_TEST_API_KEY` is not set they will not run as they are
    not strictly mandatory.
    """

    def test_order_created(self, settings):
        """
        Test the order created template.
        If the template variables have been changed in GOV.UK notifications this
        is going to raise an exception.
        """
        settings.OMIS_NOTIFICATION_API_KEY = settings.OMIS_NOTIFICATION_TEST_API_KEY
        notify = Notify()

        market = Market.objects.first()
        market.manager_email = 'test@test.com'
        market.save()

        order = OrderFactory(primary_market_id=market.country.pk)

        notify.order_created(order)

    def test_order_info(self, settings):
        """
        Test the order info template.
        If the template variables have been changed in GOV.UK notifications this
        is going to raise an exception.
        """
        settings.OMIS_NOTIFICATION_API_KEY = settings.OMIS_NOTIFICATION_TEST_API_KEY
        notify = Notify()

        notify.order_info(OrderFactory(), what_happened='', why='')