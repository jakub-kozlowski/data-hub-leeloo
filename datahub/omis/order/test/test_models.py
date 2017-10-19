import secrets
from functools import partial
from unittest import mock
import factory
import pytest
from dateutil.parser import parse as dateutil_parse
from django.utils.crypto import get_random_string
from freezegun import freeze_time
from rest_framework.exceptions import ValidationError

from datahub.company.test.factories import AdviserFactory, CompanyFactory, ContactFactory
from datahub.core import constants
from datahub.metadata.test.factories import TeamFactory
from datahub.omis.core.exceptions import Conflict
from datahub.omis.invoice.models import Invoice
from datahub.omis.payment.models import Payment
from datahub.omis.quote.models import Quote

from .factories import (
    OrderAssigneeFactory,
    OrderFactory,
    OrderWithAcceptedQuoteFactory,
    OrderWithOpenQuoteFactory,
)

from ..constants import OrderStatus


pytestmark = pytest.mark.django_db


class OrderWithRandomPublicTokenFactory(OrderFactory):
    """OrderFactory with an already populated public_token field."""

    public_token = factory.LazyFunction(partial(secrets.token_urlsafe, 37))


class OrderWithRandomReferenceFactory(OrderFactory):
    """OrderFactory with an already populated reference field."""

    reference = factory.LazyFunction(get_random_string)


class TestOrderGenerateReference:
    """Tests for the generate reference logic."""

    @freeze_time('2017-07-12 13:00:00.000000+00:00')
    @mock.patch('datahub.omis.order.models.get_random_string')
    def test_generates_reference_if_doesnt_exist(self, mock_get_random_string):
        """
        Test that if an Order is saved without reference, the system generates one automatically.
        """
        mock_get_random_string.side_effect = [
            'ABC', '123', 'CBA', '321'
        ]

        # create 1st
        order = OrderWithRandomPublicTokenFactory()
        assert order.reference == 'ABC123/17'

        # create 2nd
        order = OrderWithRandomPublicTokenFactory()
        assert order.reference == 'CBA321/17'

    @freeze_time('2017-07-12 13:00:00.000000+00:00')
    @mock.patch('datahub.omis.order.models.get_random_string')
    def test_doesnt_generate_reference_if_present(self, mock_get_random_string):
        """
        Test that when creating a new Order, if the system generates a reference that already
        exists, it skips it and generates the next one.
        """
        # create existing Order with ref == 'ABC123/17'
        OrderWithRandomPublicTokenFactory(reference='ABC123/17')

        mock_get_random_string.side_effect = [
            'ABC', '123', 'CBA', '321'
        ]

        # ABC123/17 already exists so create CBA321/17 instead
        order = OrderWithRandomPublicTokenFactory()
        assert order.reference == 'CBA321/17'

    @freeze_time('2017-07-12 13:00:00.000000+00:00')
    @mock.patch('datahub.omis.order.models.get_random_string')
    def test_cannot_generate_reference(self, mock_get_random_string):
        """
        Test that if there are more than 10 collisions, the generator algorithm raises a
        RuntimeError.
        """
        max_retries = 10
        OrderWithRandomPublicTokenFactory(reference='ABC123/17')

        mock_get_random_string.side_effect = ['ABC', '123'] * max_retries

        with pytest.raises(RuntimeError):
            for index in range(max_retries):
                OrderWithRandomPublicTokenFactory()


class TestOrderGeneratePublicToken:
    """Tests for the generate public token logic."""

    @mock.patch('datahub.omis.order.models.secrets')
    def test_generates_public_token_if_doesnt_exist(self, mock_secrets):
        """
        Test that if an order is saved without public_token,
        the system generates one automatically.
        """
        mock_secrets.token_urlsafe.side_effect = ['9999', '8888']

        # create 1st
        order = OrderWithRandomReferenceFactory()
        assert order.public_token == '9999'

        # create 2nd
        order = OrderWithRandomReferenceFactory()
        assert order.public_token == '8888'

    @mock.patch('datahub.omis.order.models.secrets')
    def test_look_for_unused_public_token(self, mock_secrets):
        """
        Test that when creating a new order, if the system generates a public token
        that already exists, it skips it and generates the next one.
        """
        # create existing order with public_token == '9999'
        OrderWithRandomReferenceFactory(public_token='9999')

        mock_secrets.token_urlsafe.side_effect = ['9999', '8888']

        # 9999 already exists so create 8888 instead
        order = OrderWithRandomReferenceFactory()
        assert order.public_token == '8888'

    @mock.patch('datahub.omis.order.models.secrets')
    def test_cannot_generate_public_token(self, mock_secrets):
        """
        Test that if there are more than 10 collisions, the generator algorithm raises a
        RuntimeError.
        """
        max_retries = 10
        OrderWithRandomReferenceFactory(public_token='9999')

        mock_secrets.token_urlsafe.side_effect = ['9999'] * max_retries

        with pytest.raises(RuntimeError):
            for index in range(max_retries):
                OrderWithRandomReferenceFactory()


class TestGenerateQuote:
    """Tests for the generate quote logic."""

    @mock.patch('datahub.omis.order.models.validators')
    def test_fails_with_incomplete_fields(self, validators):
        """Test raises ValidationError if the order is incomplete."""
        validators.OrderDetailsFilledInValidator.side_effect = ValidationError('error')

        order = OrderFactory()
        with pytest.raises(ValidationError):
            order.generate_quote(by=None)

    @mock.patch('datahub.omis.order.models.validators')
    def test_fails_if_theres_already_an_active_quote(self, validators):
        """Test raises Conflict if there's already an active quote."""
        validators.NoOtherActiveQuoteExistsValidator.side_effect = Conflict('error')

        order = OrderFactory()
        with pytest.raises(Conflict):
            order.generate_quote(by=None)

    @pytest.mark.parametrize(
        'disallowed_status',
        (
            OrderStatus.quote_awaiting_acceptance,
            OrderStatus.quote_accepted,
            OrderStatus.paid,
            OrderStatus.complete,
            OrderStatus.cancelled,
        )
    )
    def test_fails_if_order_not_in_draft(self, disallowed_status):
        """Test that if the order is not in `draft`, a quote cannot be generated."""
        order = OrderFactory(status=disallowed_status)
        with pytest.raises(Conflict):
            order.generate_quote(by=None)

    def test_atomicity(self):
        """Test that if there's a problem with saving the order, the quote is not saved either."""
        order = OrderFactory()
        with mock.patch.object(order, 'save') as mocked_save:
            mocked_save.side_effect = Exception()

            with pytest.raises(Exception):
                order.generate_quote(by=None)
            assert not Quote.objects.count()

    def test_success(self):
        """Test that a quote can be generated."""
        company = CompanyFactory(
            registered_address_1='Reg address 1',
            registered_address_2='Reg address 2',
            registered_address_town='Reg address town',
            registered_address_county='Reg address county',
            registered_address_postcode='Reg address postcode',
            registered_address_country_id=constants.Country.japan.value.id
        )
        order = OrderFactory(
            company=company,
            billing_contact_name='',
            billing_email='',
            billing_phone='',
            billing_address_1='',
            billing_address_2='',
            billing_address_town='',
            billing_address_county='',
            billing_address_postcode='',
            billing_address_country_id=None
        )
        adviser = AdviserFactory()
        order.generate_quote(by=adviser)

        # quote created and populated
        assert order.quote.pk
        assert order.quote.reference
        assert order.quote.content
        assert order.quote.created_by == adviser

        # status changed
        assert order.status == OrderStatus.quote_awaiting_acceptance

        # billing fields populated
        assert order.billing_contact_name == order.contact.name
        assert order.billing_email == order.contact.email
        assert order.billing_phone == order.contact.telephone_number
        assert order.billing_address_1 == company.registered_address_1
        assert order.billing_address_2 == company.registered_address_2
        assert order.billing_address_county == company.registered_address_county
        assert order.billing_address_town == company.registered_address_town
        assert order.billing_address_postcode == company.registered_address_postcode
        assert order.billing_address_country == company.registered_address_country

    def test_without_committing(self):
        """Test that a quote can be generated without saving its changes."""
        order = OrderFactory()
        order.generate_quote(by=AdviserFactory(), commit=False)

        assert order.quote.reference
        assert order.quote.content
        assert order.status == OrderStatus.quote_awaiting_acceptance

        order.refresh_from_db()
        assert not order.quote
        assert not Quote.objects.count()
        assert order.status == OrderStatus.draft


class TestReopen:
    """Tests for when an order is reopened."""

    @pytest.mark.parametrize(
        'allowed_status',
        (
            OrderStatus.quote_awaiting_acceptance,
            OrderStatus.quote_accepted,
        )
    )
    def test_ok_if_order_in_allowed_status(self, allowed_status):
        """
        Test that an order can be reopened if it's in one of the allowed statuses.
        """
        order = OrderFactory(status=allowed_status)

        try:
            order.reopen(by=AdviserFactory())
        except Exception:
            pytest.fail('Should not raise a validator error.')

        assert order.status == OrderStatus.draft

    def test_with_active_quote(self):
        """
        Test that if an order with an active quote is reopened, the quote is cancelled.
        """
        order = OrderWithOpenQuoteFactory()
        assert not order.quote.is_cancelled()

        adviser = AdviserFactory()

        with freeze_time('2017-07-12 13:00') as mocked_now:
            order.reopen(by=adviser)

            assert order.quote.is_cancelled()
            assert order.quote.cancelled_by == adviser
            assert order.quote.cancelled_on == mocked_now()
            assert order.status == OrderStatus.draft

    @pytest.mark.parametrize(
        'disallowed_status',
        (
            OrderStatus.draft,
            OrderStatus.paid,
            OrderStatus.complete,
            OrderStatus.cancelled,
        )
    )
    def test_fails_if_order_not_in_allowed_status(self, disallowed_status):
        """Test that if the order is in a disallowed status, it cannot be reopened."""
        order = OrderFactory(status=disallowed_status)
        with pytest.raises(Conflict):
            order.reopen(by=None)

        assert order.status == disallowed_status


class TestAcceptQuote:
    """Tests for when a quote is accepted."""

    @pytest.mark.parametrize(
        'allowed_status',
        (OrderStatus.quote_awaiting_acceptance,)
    )
    def test_ok_if_order_in_allowed_status(self, allowed_status):
        """
        Test that the quote of an order can be accepted if the order is
        in one of the allowed statuses.
        """
        order = OrderWithOpenQuoteFactory(status=allowed_status)
        contact = ContactFactory()

        try:
            order.accept_quote(by=contact)
        except Exception:
            pytest.fail('Should not raise a validator error.')

        order.refresh_from_db()
        assert order.status == OrderStatus.quote_accepted
        assert order.quote.accepted_on
        assert order.quote.accepted_by == contact
        assert order.invoice

    @pytest.mark.parametrize(
        'disallowed_status',
        (
            OrderStatus.quote_accepted,
            OrderStatus.paid,
            OrderStatus.complete,
            OrderStatus.cancelled,
        )
    )
    def test_fails_if_order_not_in_allowed_status(self, disallowed_status):
        """Test that if the order is in a disallowed status, the quote cannot be accepted."""
        order = OrderFactory(status=disallowed_status)
        with pytest.raises(Conflict):
            order.accept_quote(by=None)

        assert order.status == disallowed_status

    def test_atomicity(self):
        """Test that if there's a problem with saving the order, the quote is not saved either."""
        order = OrderWithOpenQuoteFactory()
        with mock.patch.object(order, 'save') as mocked_save:
            mocked_save.side_effect = Exception()

            with pytest.raises(Exception):
                order.accept_quote(by=None)

            quote = order.quote
            order.refresh_from_db()
            quote.refresh_from_db()
            assert not quote.is_accepted()
            assert not order.invoice
            assert not Invoice.objects.count()


class TestMarkOrderAsPaid:
    """Tests for when an order is marked as paid."""

    @pytest.mark.parametrize(
        'allowed_status',
        (OrderStatus.quote_accepted,)
    )
    def test_ok_if_order_in_allowed_status(self, allowed_status):
        """
        Test that the order can be marked as paid if the order is in one of the allowed statuses.
        """
        order = OrderWithAcceptedQuoteFactory(status=allowed_status)
        adviser = AdviserFactory()

        try:
            order.mark_as_paid(
                by=adviser,
                payments_data=[
                    {
                        'amount': 1,
                        'received_on': dateutil_parse('2017-01-01 13:00:00')
                    },
                    {
                        'amount': order.total_cost - 1,
                        'received_on': dateutil_parse('2017-01-02 13:00:00')
                    },
                ]
            )
        except Exception:
            pytest.fail('Should not raise a validator error.')

        order.refresh_from_db()
        assert order.status == OrderStatus.paid
        assert list(
            order.payments.order_by('received_on').values_list('amount', 'received_on')
        ) == [
            (1, dateutil_parse('2017-01-01 13:00:00')),
            (order.total_cost - 1, dateutil_parse('2017-01-02 13:00:00')),
        ]

    @pytest.mark.parametrize(
        'disallowed_status',
        (
            OrderStatus.draft,
            OrderStatus.quote_awaiting_acceptance,
            OrderStatus.paid,
            OrderStatus.complete,
            OrderStatus.cancelled,
        )
    )
    def test_fails_if_order_not_in_allowed_status(self, disallowed_status):
        """
        Test that if the order is in a disallowed status, the order cannot be marked as paid.
        """
        order = OrderFactory(status=disallowed_status)
        with pytest.raises(Conflict):
            order.mark_as_paid(by=None, payments_data=[])

        assert order.status == disallowed_status

    def test_atomicity(self):
        """
        Test that if there's a problem with saving the order, the payments are not saved either.
        """
        order = OrderWithAcceptedQuoteFactory()
        with mock.patch.object(order, 'save') as mocked_save:
            mocked_save.side_effect = Exception()

            with pytest.raises(Exception):
                order.mark_as_paid(
                    by=None,
                    payments_data=[{
                        'amount': order.total_cost,
                        'received_on': dateutil_parse('2017-01-02 13:00:00')
                    }]
                )

            order.refresh_from_db()
            assert order.status == OrderStatus.quote_accepted
            assert not Payment.objects.count()

    def test_validation_error_if_amounts_less_then_total_cost(self):
        """
        Test that if the sum of the amounts is < order.total_cose, the call fails.
        """
        order = OrderWithAcceptedQuoteFactory()
        with pytest.raises(ValidationError):
            order.mark_as_paid(
                by=None,
                payments_data=[
                    {
                        'amount': order.total_cost - 1,
                        'received_on': dateutil_parse('2017-01-02 13:00:00')
                    }
                ]
            )


class TestOrderAssignee:
    """Tests for the OrderAssignee model."""

    def test_set_team_country_on_create(self):
        """
        Tests that when creating a new OrderAssignee, the `team` and `country`
        properties get populated automatically.
        """
        # adviser belonging to a team with a country
        team = TeamFactory(country_id=constants.Country.france.value.id)
        adviser = AdviserFactory(dit_team=team)
        assignee = OrderAssigneeFactory(adviser=adviser)

        assert assignee.team == team
        assert str(assignee.country_id) == constants.Country.france.value.id

        # adviser belonging to a team without country
        team = TeamFactory(country=None)
        adviser = AdviserFactory(dit_team=team)
        assignee = OrderAssigneeFactory(adviser=adviser)

        assert assignee.team == team
        assert not assignee.country

        # adviser not belonging to any team
        adviser = AdviserFactory(dit_team=None)
        assignee = OrderAssigneeFactory(adviser=adviser)

        assert not assignee.team
        assert not assignee.country

    def test_team_country_dont_change_after_creation(self):
        """
        Tests that after creating an OrderAssignee, the `team` and `country`
        properties don't change with further updates.
        """
        team_france = TeamFactory(country_id=constants.Country.france.value.id)
        adviser = AdviserFactory(dit_team=team_france)
        assignee = OrderAssigneeFactory(adviser=adviser)

        # the adviser moves to another team
        adviser.dit_team = TeamFactory(country_id=constants.Country.italy.value.id)
        adviser.save()

        assignee.estimated_time = 1000
        assignee.save()
        assignee.refresh_from_db()

        # the assignee is still linking to the original team and country
        assert assignee.team == team_france
        assert str(assignee.country_id) == constants.Country.france.value.id

    def test_cannot_change_adviser_after_creation(self):
        """After creating an OrderAssignee, the related adviser cannot be changed."""
        adviser = AdviserFactory()
        assignee = OrderAssigneeFactory(adviser=adviser)

        with pytest.raises(ValueError):
            assignee.adviser = AdviserFactory()
            assignee.save()
