from unittest import mock
import pytest

from freezegun import freeze_time
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from datahub.company.test.factories import AdviserFactory
from datahub.core import constants
from datahub.core.test_utils import APITestMixin
from datahub.omis.order.models import Order
from datahub.omis.order.test.factories import OrderAssigneeFactory, OrderFactory, \
    OrderSubscriberFactory

from ..views import PaginatedAPIMixin


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    """Sets up data for the tests."""
    with freeze_time('2017-01-01 13:00:00'):
        order = OrderFactory(
            reference='ref1',
            primary_market_id=constants.Country.japan.value.id
        )
        OrderSubscriberFactory(
            order=order,
            adviser=AdviserFactory(dit_team_id=constants.Team.healthcare_uk.value.id)
        )
        OrderAssigneeFactory(
            order=order,
            adviser=AdviserFactory(dit_team_id=constants.Team.tees_valley_lep.value.id)
        )

    with freeze_time('2017-02-01 13:00:00'):
        order = OrderFactory(
            reference='ref2',
            primary_market_id=constants.Country.france.value.id
        )
        OrderSubscriberFactory(
            order=order,
            adviser=AdviserFactory(dit_team_id=constants.Team.td_events_healthcare.value.id)
        )
        OrderAssigneeFactory(
            order=order,
            adviser=AdviserFactory(dit_team_id=constants.Team.food_from_britain.value.id)
        )


class TestSearchOrder(APITestMixin):
    """Test specific search for orders."""

    def test_get_all(self, setup_es, setup_data):
        """
        Test that if the querystring is empty and no other params are set,
        it returns all the orders ordered by created_on DESC.
        """
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 2
        assert [
            item['reference'] for item in response.json()['results']
        ] == ['ref2', 'ref1']

    def test_pagination(self, setup_es, setup_data):
        """Test that the pagination works when speficied as param."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        # get second page with page size = 1
        response = self.api_client.post(url, {
            'limit': 1,
            'offset': 1,
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref1'

    def test_filter_by_primary_market(self, setup_es, setup_data):
        """Test that results can be filtered by primary market."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'primary_market': constants.Country.france.value.id
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref2'

    def test_no_result_with_invalid_primary_market(self, setup_es, setup_data):
        """
        Test that if an invalid primary market is specified, the search returns 0 results.
        """
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'primary_market': 'invalid'
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 0

    def test_filter_by_created_on_range(self, setup_es, setup_data):
        """Test that results can be filtered by a range of date for created_on."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'created_on_before': '2017-02-02',
            'created_on_after': '2017-02-01'
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref2'

    def test_filter_by_created_on_before_only(self, setup_es, setup_data):
        """Test that results can be filtered by created_on_before."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'created_on_before': '2017-01-15',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref1'

    def test_filter_by_created_on_after_only(self, setup_es, setup_data):
        """Test that results can be filtered by created_on_after."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'created_on_after': '2017-01-15',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref2'

    def test_incorrect_dates_raise_validation_error(self, setup_es, setup_data):
        """Test that if the dates are not in a valid format, the API return a validation error."""
        setup_es.indices.refresh()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'created_on_before': 'invalid',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {'non_field_errors': 'Date(s) in incorrect format.'}

    def test_filter_by_assigned_to_assignee_adviser(self, setup_es, setup_data):
        """Test that results can be filtered by assignee."""
        setup_es.indices.refresh()

        assignee = Order.objects.get(reference='ref2').assignees.first()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'assigned_to_adviser': assignee.adviser.pk
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref2'

    def test_filter_by_assigned_to_assignee_adviser_team(self, setup_es, setup_data):
        """Test that results can be filtered by the assignee's team."""
        setup_es.indices.refresh()

        assignee = Order.objects.get(reference='ref2').assignees.first()

        url = reverse('api-v3:search:order')

        response = self.api_client.post(url, {
            'assigned_to_team': assignee.adviser.dit_team.pk
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()['results']) == 1
        assert response.json()['results'][0]['reference'] == 'ref2'


class TestPaginatedAPIMixin:
    """Tests related to the paginated API mixin."""

    def test_limit_as_valid_param(self):
        """Test that get_limit returns the int value of the param if valid."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: '3'
            }
        )

        assert mixin.get_limit(request) == 3

    def test_limit_as_non_int_defaults(self):
        """Test that get_limit returns the default value if the param is not an int."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: 'non-int'
            }
        )

        assert mixin.get_limit(request) == PaginatedAPIMixin.default_limit

    def test_limit_as_negative_int_defaults(self):
        """Test that get_limit returns the default value if param is a negative value."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: '-1'
            }
        )

        assert mixin.get_limit(request) == PaginatedAPIMixin.default_limit

    def test_limit_as_zero_defaults(self):
        """Test that get_limit returns the default value if param is 0."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: '0'
            }
        )

        assert mixin.get_limit(request) == PaginatedAPIMixin.default_limit

    def test_offset_as_valid_param(self):
        """Test that get_offset returns the int value if the param is valid."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.offset_query_param: '4'
            }
        )

        assert mixin.get_offset(request) == 4

    def test_offset_as_non_int_defaults(self):
        """Test that get_offset returns the default value if the param is not an int."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.offset_query_param: 'non-int'
            }
        )

        assert mixin.get_offset(request) == 0

    def test_pagination_params_within_limit(self):
        """Test that if the result window (offset + limit) is within limit, everything is OK."""
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: '100',
                PaginatedAPIMixin.offset_query_param: '9900',
            }
        )

        limit, offset = mixin.get_pagination_values(request)

        assert limit == 100
        assert offset == 9900

    def test_pagination_params_outside_limit(self):
        """
        Test that if the result window (offset + limit) is too large,
        a validator error is returned.
        """
        mixin = PaginatedAPIMixin()

        request = mock.MagicMock(
            data={
                PaginatedAPIMixin.limit_query_param: '100',
                PaginatedAPIMixin.offset_query_param: '9901',
            }
        )

        with pytest.raises(ValidationError):
            mixin.get_pagination_values(request)