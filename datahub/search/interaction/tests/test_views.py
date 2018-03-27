from collections import Counter
from datetime import datetime
from uuid import UUID

import factory
import pytest
from dateutil.parser import parse as dateutil_parse
from django.utils.timezone import utc
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse

from datahub.company.test.factories import AdviserFactory, CompanyFactory, ContactFactory
from datahub.core import constants
from datahub.core.test_utils import APITestMixin, create_test_user, random_obj_for_queryset
from datahub.interaction.constants import CommunicationChannel
from datahub.interaction.models import Interaction
from datahub.interaction.test.factories import (
    CompanyInteractionFactory, InvestmentProjectInteractionFactory, ServiceDeliveryFactory,
)
from datahub.investment.test.factories import ActiveInvestmentProjectFactory
from datahub.metadata.models import Sector
from datahub.metadata.test.factories import TeamFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def interactions(setup_es):
    """Sets up data for the tests."""
    data = []
    with freeze_time('2017-01-01 13:00:00'):
        data.extend([
            CompanyInteractionFactory(
                subject='Exports meeting',
                date=dateutil_parse('2017-10-30T00:00:00Z')
            ),
            CompanyInteractionFactory(
                subject='a coffee',
                date=dateutil_parse('2017-04-05T00:00:00Z')
            ),
            CompanyInteractionFactory(
                subject='Email about exhibition',
                date=dateutil_parse('2016-09-02T00:00:00Z')
            ),
            CompanyInteractionFactory(
                subject='talking about cats',
                date=dateutil_parse('2018-02-01T00:00:00Z')
            ),
            CompanyInteractionFactory(
                subject='Event at HQ',
                date=dateutil_parse('2018-01-01T00:00:00Z')
            ),
        ])

    setup_es.indices.refresh()

    yield data


class TestViews(APITestMixin):
    """Tests interaction search views."""

    def test_interaction_search_no_permissions(self):
        """Should return 403"""
        user = create_test_user(dit_team=TeamFactory())
        api_client = self.create_api_client(user=user)
        url = reverse('api-v3:search:interaction')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_all(self, interactions):
        """
        Tests that all interactions are returned with an empty POST body.
        """
        url = reverse('api-v3:search:interaction')

        response = self.api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(interactions)
        expected_ids = Counter(str(interaction.id) for interaction in interactions)
        assert Counter([item['id'] for item in response_data['results']]) == expected_ids

    def test_limit(self, interactions):
        """Tests that results can be limited."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'limit': 1
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data['results']) == 1

    def test_offset(self, interactions):
        """Tests that results can be offset."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'offset': 1
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data['results']) == 4

    def test_default_sort(self, setup_es):
        """Tests default sorting of results by date (descending)."""
        url = reverse('api-v3:search:interaction')

        dates = (
            datetime(2017, 2, 4, 13, 15, 0, tzinfo=utc),
            datetime(2017, 1, 4, 11, 23, 10, tzinfo=utc),
            datetime(2017, 9, 29, 3, 25, 15, tzinfo=utc),
            datetime(2017, 7, 5, 11, 44, 33, tzinfo=utc),
            datetime(2017, 2, 1, 18, 15, 1, tzinfo=utc),
        )
        CompanyInteractionFactory.create_batch(
            len(dates),
            date=factory.Iterator(dates)
        )
        setup_es.indices.refresh()

        response = self.api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        sorted_dates = sorted(dates, reverse=True)
        expected_dates = [d.isoformat() for d in sorted_dates]
        assert response_data['count'] == len(dates)
        assert [item['date'] for item in response_data['results']] == expected_dates

    def test_sort_by_subject_asc(self, interactions):
        """Tests sorting of results by subject (ascending)."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'sortby': 'subject:asc'
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(interactions)
        subjects = (interaction.subject for interaction in interactions)
        expected_subjects = list(sorted(subjects, key=lambda s: s.lower()))
        assert [item['subject'] for item in response_data['results']] == expected_subjects

    def test_sort_by_subject_desc(self, interactions):
        """Tests sorting of results by subject (ascending)."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'sortby': 'subject:desc'
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(interactions)
        subjects = (interaction.subject for interaction in interactions)
        expected_subjects = list(sorted(subjects, key=lambda s: s.lower(), reverse=True))
        assert [item['subject'] for item in response_data['results']] == expected_subjects

    def test_sort_by_invalid_field(self, setup_es):
        """Tests attempting to sort by an invalid field and direction."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'sortby': 'gyratory:backwards'
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data == {
            'sortby': [
                "'sortby' field is not one of ('company.name', 'contact.name', 'date'"
                ", 'dit_adviser.name', 'dit_team.name', 'id', 'subject').",
                "Invalid sort direction 'backwards', must be one of ('asc', 'desc')",
            ]
        }

    @pytest.mark.parametrize('term', ('exports', 'meeting', 'exports meeting'))
    def test_search_original_query(self, interactions, term):
        """Tests searching across fields for a particular interaction."""
        url = reverse('api-v3:search:interaction')

        request_data = {
            'original_query': term
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        interaction = interactions[0]
        assert response_data['count'] == 1
        assert response_data['results'] == [{
            'id': str(interaction.pk),
            'kind': interaction.kind,
            'date': interaction.date.isoformat(),
            'company': {
                'id': str(interaction.company.pk),
                'name': interaction.company.name,
            },
            'company_sector': {
                'id': str(interaction.company.sector.pk),
                'name': interaction.company.sector.name,
                'ancestors': [{
                    'id': str(ancestor.pk),
                } for ancestor in interaction.company.sector.get_ancestors()],
            },
            'contact': {
                'id': str(interaction.contact.pk),
                'first_name': interaction.contact.first_name,
                'name': interaction.contact.name,
                'last_name': interaction.contact.last_name,
            },
            'is_event': None,
            'event': None,
            'service': {
                'id': str(interaction.service.pk),
                'name': interaction.service.name,
            },
            'subject': interaction.subject,
            'dit_adviser': {
                'id': str(interaction.dit_adviser.pk),
                'first_name': interaction.dit_adviser.first_name,
                'name': interaction.dit_adviser.name,
                'last_name': interaction.dit_adviser.last_name,
            },
            'notes': interaction.notes,
            'dit_team': {
                'id': str(interaction.dit_team.pk),
                'name': interaction.dit_team.name,
            },
            'communication_channel': {
                'id': str(interaction.communication_channel.pk),
                'name': interaction.communication_channel.name,
            },
            'investment_project': None,
            'investment_project_sector': None,
            'service_delivery_status': None,
            'grant_amount_offered': None,
            'net_company_receipt': None,
            'created_on': interaction.created_on.isoformat(),
            'modified_on': interaction.modified_on.isoformat(),
        }]

    def test_filter_by_kind(self, setup_es):
        """Tests filtering interaction by kind."""
        CompanyInteractionFactory.create_batch(10),
        service_deliveries = ServiceDeliveryFactory.create_batch(10)

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'kind': Interaction.KINDS.service_delivery,
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 10

        results = response_data['results']
        service_delivery_ids = {str(interaction.id) for interaction in service_deliveries}
        assert {result['id'] for result in results} == service_delivery_ids

    def test_filter_by_company_id(self, setup_es):
        """Tests filtering interaction by company id."""
        companies = CompanyFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(companies),
            company=factory.Iterator(companies)
        )
        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'company': companies[5].id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 1

        results = response_data['results']
        assert results[0]['company']['id'] == str(companies[5].id)

    def test_filter_by_company_name(self, setup_es):
        """Tests filtering interaction by company name."""
        companies = CompanyFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(companies),
            company=factory.Iterator(companies)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'company_name': companies[5].name
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] > 0

        results = response_data['results']
        # multiple records can match our filter, let's make sure at least one is exact match
        assert any(result['company']['id'] == str(companies[5].id) for result in results)
        assert any(result['company']['name'] == companies[5].name for result in results)

    def test_filter_by_contact_id(self, setup_es):
        """Tests filtering interaction by contact id."""
        contacts = ContactFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(contacts),
            contact=factory.Iterator(contacts)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'contact': contacts[5].id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 1

        results = response_data['results']
        assert results[0]['contact']['id'] == str(contacts[5].id)

    def test_filter_by_contact_name(self, setup_es):
        """Tests filtering interaction by contact name."""
        contacts = ContactFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(contacts),
            contact=factory.Iterator(contacts)
        )
        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'contact_name': contacts[5].name
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] > 0

        results = response_data['results']
        # multiple records can match our filter, let's make sure at least one is exact match
        assert any(result['contact']['id'] == str(contacts[5].id) for result in results)
        assert any(result['contact']['name'] == contacts[5].name for result in results)

    @pytest.mark.parametrize(
        'created_on_exists',
        (True, False)
    )
    def test_filter_by_created_on_exists(self, setup_es, created_on_exists):
        """Tests filtering interaction by created_on exists."""
        CompanyInteractionFactory.create_batch(3)
        no_created_on = CompanyInteractionFactory.create_batch(3)
        for interaction in no_created_on:
            interaction.created_on = None
            interaction.save()

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'created_on_exists': created_on_exists,
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        results = response_data['results']
        assert response_data['count'] == 3
        assert all((not result['created_on'] is None) == created_on_exists
                   for result in results)

    def test_filter_by_dit_adviser_id(self, setup_es):
        """Tests filtering interaction by dit adviser id."""
        advisers = AdviserFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(advisers),
            dit_adviser=factory.Iterator(advisers)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'dit_adviser': advisers[5].id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 1

        results = response_data['results']

        assert results[0]['dit_adviser']['id'] == str(advisers[5].id)
        assert results[0]['dit_adviser']['name'] == advisers[5].name

    def test_filter_by_dit_adviser_name(self, setup_es):
        """Tests filtering interaction by dit adviser name."""
        advisers = AdviserFactory.create_batch(10)
        CompanyInteractionFactory.create_batch(
            len(advisers),
            dit_adviser=factory.Iterator(advisers)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'dit_adviser_name': advisers[5].name
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] > 0

        results = response_data['results']
        # multiple records can match our filter, let's make sure at least one is exact match
        assert any(result['dit_adviser']['id'] == str(advisers[5].id) for result in results)
        assert any(result['dit_adviser']['name'] == advisers[5].name for result in results)

    def test_filter_by_dit_team(self, setup_es):
        """Tests filtering interaction by dit team."""
        CompanyInteractionFactory.create_batch(5, dit_team_id=constants.Team.crm.value.id)
        dit_team_id = constants.Team.td_events_healthcare.value.id
        CompanyInteractionFactory.create_batch(5, dit_team_id=dit_team_id)

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'dit_team': dit_team_id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 5

        results = response_data['results']
        assert {result['dit_team']['id'] for result in results} == {str(dit_team_id)}

    def test_filter_by_communication_channel(self, setup_es):
        """Tests filtering interaction by interaction type."""
        CompanyInteractionFactory.create_batch(
            5,
            communication_channel_id=CommunicationChannel.email_website.value.id
        )
        communication_channel_id = CommunicationChannel.social_media.value.id
        CompanyInteractionFactory.create_batch(
            5,
            communication_channel_id=communication_channel_id
        )
        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'original_query': '',
            'communication_channel': communication_channel_id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 5

        results = response_data['results']
        result_ids = {result['communication_channel']['id'] for result in results}
        assert result_ids == {str(communication_channel_id)}

    def test_filter_by_service(self, setup_es):
        """Tests filtering interaction by service."""
        CompanyInteractionFactory.create_batch(
            5,
            service_id=constants.Service.trade_enquiry.value.id
        )
        service_id = constants.Service.account_management.value.id
        CompanyInteractionFactory.create_batch(
            5,
            service_id=service_id
        )
        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        request_data = {
            'service': service_id
        }
        response = self.api_client.post(url, request_data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        assert response_data['count'] == 5

        results = response_data['results']
        result_ids = {result['service']['id'] for result in results}
        assert result_ids == {str(service_id)}

    @pytest.mark.parametrize(
        'data,results',
        (
            (
                {
                    'date_after': '2017-12-01'
                },
                {
                    'talking about cats',
                    'Event at HQ',
                }
            ),
            (
                {
                    'date_after': '2017-12-01',
                    'date_before': '2018-01-02'
                },
                {
                    'Event at HQ',
                }
            ),
            (
                {
                    'date_before': '2017-01-01'
                },
                {
                    'Email about exhibition',
                }
            ),
        )
    )
    def test_filter_by_date(self, interactions, data, results):
        """Tests filtering interaction by date."""
        url = reverse('api-v3:search:interaction')
        response = self.api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        names = {result['subject'] for result in response_data['results']}
        assert names == results

    @pytest.mark.parametrize(
        'sector_level',
        (0, 1, 2),
    )
    def test_sector_descends_filter_for_company_interaction(
            self,
            hierarchical_sectors,
            setup_es,
            sector_level,
    ):
        """Test the sector_descends filter with company interactions."""
        num_sectors = len(hierarchical_sectors)
        sectors_ids = [sector.pk for sector in hierarchical_sectors]

        companies = CompanyFactory.create_batch(
            num_sectors,
            sector_id=factory.Iterator(sectors_ids)
        )
        company_interactions = CompanyInteractionFactory.create_batch(
            3,
            company=factory.Iterator(companies)
        )

        other_companies = CompanyFactory.create_batch(
            3,
            sector=factory.LazyFunction(lambda: random_obj_for_queryset(
                Sector.objects.exclude(pk__in=sectors_ids)
            ))
        )
        CompanyInteractionFactory.create_batch(
            3,
            company=factory.Iterator(other_companies)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        body = {
            'sector_descends': hierarchical_sectors[sector_level].pk
        }
        response = self.api_client.post(url, body)
        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data['count'] == num_sectors - sector_level

        actual_ids = {UUID(interaction['id']) for interaction in response_data['results']}
        expected_ids = {interaction.pk for interaction in company_interactions[sector_level:]}
        assert actual_ids == expected_ids

    @pytest.mark.parametrize(
        'sector_level',
        (0, 1, 2),
    )
    def test_sector_descends_filter_for_investment_project_interaction(
            self,
            hierarchical_sectors,
            setup_es,
            sector_level,
    ):
        """Test the sector_descends filter with investment project interactions."""
        num_sectors = len(hierarchical_sectors)
        sectors_ids = [sector.pk for sector in hierarchical_sectors]

        projects = ActiveInvestmentProjectFactory.create_batch(
            num_sectors,
            sector_id=factory.Iterator(sectors_ids)
        )
        investment_project_interactions = InvestmentProjectInteractionFactory.create_batch(
            3,
            investment_project=factory.Iterator(projects)
        )

        other_projects = ActiveInvestmentProjectFactory.create_batch(
            3,
            sector=factory.LazyFunction(lambda: random_obj_for_queryset(
                Sector.objects.exclude(pk__in=sectors_ids)
            ))
        )
        InvestmentProjectInteractionFactory.create_batch(
            3,
            investment_project=factory.Iterator(other_projects)
        )

        setup_es.indices.refresh()

        url = reverse('api-v3:search:interaction')
        body = {
            'sector_descends': hierarchical_sectors[sector_level].pk
        }
        response = self.api_client.post(url, body)
        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data['count'] == num_sectors - sector_level

        actual_ids = {UUID(interaction['id']) for interaction in response_data['results']}
        expected_ids = {
            interaction.pk for interaction in investment_project_interactions[sector_level:]
        }
        assert actual_ids == expected_ids
