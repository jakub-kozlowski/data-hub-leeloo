from datetime import date
from itertools import chain

import pytest
from rest_framework import status
from rest_framework.reverse import reverse
from reversion.models import Version

from datahub.company.test.factories import AdviserFactory, CompanyFactory, ContactFactory
from datahub.core.constants import Service, Team
from datahub.core.reversion import EXCLUDED_BASE_MODEL_FIELDS
from datahub.core.test_utils import APITestMixin, create_test_user, random_obj_for_model
from datahub.investment.test.factories import InvestmentProjectFactory
from datahub.metadata.test.factories import TeamFactory
from ..factories import CompanyInteractionFactory, EventServiceDeliveryFactory
from ...models import CommunicationChannel, Interaction, InteractionPermission


NON_RESTRICTED_READ_PERMISSIONS = (
    (
        InteractionPermission.read_all,
    ),
    (
        InteractionPermission.read_all,
        InteractionPermission.read_associated_investmentproject,
    )
)


NON_RESTRICTED_CHANGE_PERMISSIONS = (
    (
        InteractionPermission.change_all,
    ),
    (
        InteractionPermission.change_all,
        InteractionPermission.change_associated_investmentproject,
    )
)


class TestGetInteraction(APITestMixin):
    """Base tests for the get interaction view."""

    def test_fails_without_permissions(self):
        """Should return 403"""
        interaction = CompanyInteractionFactory()
        user = create_test_user(dit_team=TeamFactory())
        api_client = self.create_api_client(user=user)
        url = reverse('api-v3:interaction:item', kwargs={'pk': interaction.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateInteraction(APITestMixin):
    """Base tests for the update interaction view."""

    def test_cannot_update_read_only_fields(self):
        """Test updating read-only fields."""
        interaction = CompanyInteractionFactory(
            archived_documents_url_path='old_path',
        )

        url = reverse('api-v3:interaction:item', kwargs={'pk': interaction.pk})
        response = self.api_client.patch(url, format='json', data={
            'archived_documents_url_path': 'new_path'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['archived_documents_url_path'] == 'old_path'

    def test_date_validation(self):
        """Test validation when an invalid date is provided."""
        interaction = CompanyInteractionFactory()

        url = reverse('api-v3:interaction:item', kwargs={'pk': interaction.pk})
        response = self.api_client.patch(url, {
            'date': 'abcd-de-fe',
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data['date'] == [
            'Datetime has wrong format. Use one of these formats instead: YYYY-MM-DD.'
        ]


class TestListInteractions(APITestMixin):
    """Tests for the list interactions view."""

    def test_filtered_by_company(self):
        """List of interactions filtered by company"""
        company1 = CompanyFactory()
        company2 = CompanyFactory()

        CompanyInteractionFactory.create_batch(3, company=company1)
        interactions = CompanyInteractionFactory.create_batch(2, company=company2)

        url = reverse('api-v3:interaction:collection')
        response = self.api_client.get(url, {'company_id': company2.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert {i['id'] for i in response.data['results']} == {str(i.id) for i in interactions}

    def test_filtered_by_contact(self):
        """List of interactions filtered by contact"""
        contact1 = ContactFactory()
        contact2 = ContactFactory()

        CompanyInteractionFactory.create_batch(3, contact=contact1)
        interactions = CompanyInteractionFactory.create_batch(2, contact=contact2)

        url = reverse('api-v3:interaction:collection')
        response = self.api_client.get(url, {'contact_id': contact2.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert {i['id'] for i in response.data['results']} == {str(i.id) for i in interactions}

    def test_filtered_by_investment_project(self):
        """List of interactions filtered by investment project"""
        contact = ContactFactory()
        project = InvestmentProjectFactory()
        company = CompanyFactory()

        CompanyInteractionFactory.create_batch(3, contact=contact)
        CompanyInteractionFactory.create_batch(3, company=company)
        project_interactions = CompanyInteractionFactory.create_batch(
            2, investment_project=project
        )

        url = reverse('api-v3:interaction:collection')
        response = self.api_client.get(url, {
            'investment_project_id': project.id
        })

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == 2
        actual_ids = {i['id'] for i in response_data['results']}
        expected_ids = {str(i.id) for i in project_interactions}
        assert actual_ids == expected_ids

    @pytest.mark.parametrize('permissions', NON_RESTRICTED_READ_PERMISSIONS)
    def test_non_restricted_user_can_only_list_relevant_interactions(self, permissions):
        """Test that a non-restricted user can list all interactions"""
        requester = create_test_user(permission_codenames=permissions)
        api_client = self.create_api_client(user=requester)

        project = InvestmentProjectFactory()
        company = CompanyFactory()
        company_interactions = CompanyInteractionFactory.create_batch(3, company=company)
        project_interactions = CompanyInteractionFactory.create_batch(
            3, investment_project=project
        )

        url = reverse('api-v3:interaction:collection')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == 6
        actual_ids = {i['id'] for i in response_data['results']}
        expected_ids = {str(i.id) for i in chain(project_interactions, company_interactions)}
        assert actual_ids == expected_ids

    def test_restricted_user_can_only_list_associated_interactions(self):
        """
        Test that a restricted user can only list interactions for associated investment
        projects.
        """
        creator = AdviserFactory()
        requester = create_test_user(
            permission_codenames=[InteractionPermission.read_associated_investmentproject],
            dit_team=creator.dit_team
        )
        api_client = self.create_api_client(user=requester)

        company = CompanyFactory()
        non_associated_project = InvestmentProjectFactory()
        associated_project = InvestmentProjectFactory(created_by=creator)

        CompanyInteractionFactory.create_batch(3, company=company)
        CompanyInteractionFactory.create_batch(
            3, investment_project=non_associated_project
        )
        associated_project_interactions = CompanyInteractionFactory.create_batch(
            2, investment_project=associated_project
        )

        url = reverse('api-v3:interaction:collection')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == 2
        actual_ids = {i['id'] for i in response_data['results']}
        expected_ids = {str(i.id) for i in associated_project_interactions}
        assert actual_ids == expected_ids


class TestInteractionVersioning(APITestMixin):
    """
    Tests for versions created when interacting with the interaction endpoints.
    """

    def test_add_creates_a_new_version(self):
        """Test that creating an interaction creates a new version."""
        assert Version.objects.count() == 0

        response = self.api_client.post(
            reverse('api-v3:interaction:collection'),
            data={
                'kind': Interaction.KINDS.interaction,
                'communication_channel': random_obj_for_model(CommunicationChannel).pk,
                'subject': 'whatever',
                'date': date.today().isoformat(),
                'dit_adviser': AdviserFactory().pk,
                'notes': 'hello',
                'company': CompanyFactory().pk,
                'contact': ContactFactory().pk,
                'service': Service.trade_enquiry.value.id,
                'dit_team': Team.healthcare_uk.value.id
            },
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['subject'] == 'whatever'

        interaction = Interaction.objects.get(pk=response.data['id'])

        # check version created
        assert Version.objects.get_for_object(interaction).count() == 1
        version = Version.objects.get_for_object(interaction).first()
        assert version.revision.user == self.user
        assert version.field_dict['subject'] == 'whatever'
        assert not any(set(version.field_dict) & set(EXCLUDED_BASE_MODEL_FIELDS))

    def test_add_400_doesnt_create_a_new_version(self):
        """Test that if the endpoint returns 400, no version is created."""
        assert Version.objects.count() == 0

        response = self.api_client.post(
            reverse('api-v3:interaction:collection'),
            data={
                'kind': Interaction.KINDS.interaction,
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Version.objects.count() == 0

    def test_update_creates_a_new_version(self):
        """Test that updating an interaction creates a new version."""
        service_delivery = EventServiceDeliveryFactory()

        assert Version.objects.get_for_object(service_delivery).count() == 0

        response = self.api_client.patch(
            reverse('api-v3:interaction:item', kwargs={'pk': service_delivery.pk}),
            data={'subject': 'new subject'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['subject'] == 'new subject'

        # check version created
        assert Version.objects.get_for_object(service_delivery).count() == 1
        version = Version.objects.get_for_object(service_delivery).first()
        assert version.revision.user == self.user
        assert version.field_dict['subject'] == 'new subject'

    def test_update_400_doesnt_create_a_new_version(self):
        """Test that if the endpoint returns 400, no version is created."""
        service_delivery = EventServiceDeliveryFactory()

        assert Version.objects.get_for_object(service_delivery).count() == 0

        response = self.api_client.patch(
            reverse('api-v3:interaction:item', kwargs={'pk': service_delivery.pk}),
            data={'kind': 'invalid'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Version.objects.get_for_object(service_delivery).count() == 0
