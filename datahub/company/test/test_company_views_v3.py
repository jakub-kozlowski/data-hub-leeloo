import uuid
from datetime import datetime

import factory
import pytest
import reversion
from django.forms.models import model_to_dict
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from reversion.models import Version

from datahub.company.constants import BusinessTypeConstant
from datahub.company.models import Company, OneListTier
from datahub.company.serializers import CompanySerializerV3
from datahub.company.test.factories import (
    AdviserFactory,
    CompaniesHouseCompanyFactory,
    CompanyFactory,
    DuplicateCompanyFactory,
    OneListCoreTeamMemberFactory,
)
from datahub.core.constants import Country, EmployeeRange, HeadquarterType, TurnoverRange, UKRegion
from datahub.core.reversion import EXCLUDED_BASE_MODEL_FIELDS
from datahub.core.test_utils import (
    APITestMixin,
    create_test_user,
    format_date_or_datetime,
    random_obj_for_model,
)
from datahub.metadata.models import Sector
from datahub.metadata.test.factories import TeamFactory


class TestListCompanies(APITestMixin):
    """Tests for listing companies."""

    def test_companies_list_no_permissions(self):
        """Should return 403"""
        user = create_test_user(dit_team=TeamFactory())
        api_client = self.create_api_client(user=user)
        url = reverse('api-v3:company:collection')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_companies(self):
        """List the companies."""
        CompanyFactory.create_batch(2)
        url = reverse('api-v3:company:collection')
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['count'] == 2

    def test_filter_by_global_headquarters(self):
        """Test filtering by global_headquarters_id."""
        ghq = CompanyFactory()
        subsidiaries = CompanyFactory.create_batch(2, global_headquarters=ghq)
        CompanyFactory.create_batch(2)

        url = reverse('api-v3:company:collection')
        response = self.api_client.get(
            url,
            data={
                'global_headquarters_id': ghq.pk,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(subsidiaries)
        expected_ids = {str(subsidiary.pk) for subsidiary in subsidiaries}
        actual_ids = {result['id'] for result in response_data['results']}
        assert expected_ids == actual_ids

    def test_sort_by_name(self):
        """Test sorting by name."""
        companies = CompanyFactory.create_batch(
            5,
            name=factory.Iterator(
                (
                    'Mercury Ltd',
                    'Venus Ltd',
                    'Mars Components Ltd',
                    'Exports Ltd',
                    'Lambda Plc',
                ),
            ),
        )

        url = reverse('api-v3:company:collection')
        response = self.api_client.get(
            url,
            data={'sortby': 'name'},
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(companies)

        actual_names = [result['name'] for result in response_data['results']]
        assert actual_names == [
            'Exports Ltd',
            'Lambda Plc',
            'Mars Components Ltd',
            'Mercury Ltd',
            'Venus Ltd',
        ]

    def test_sort_by_created_on(self):
        """Test sorting by created_on."""
        creation_times = [
            datetime(2015, 1, 1),
            datetime(2016, 1, 1),
            datetime(2019, 1, 1),
            datetime(2020, 1, 1),
            datetime(2005, 1, 1),
        ]
        for creation_time in creation_times:
            with freeze_time(creation_time):
                CompanyFactory()

        url = reverse('api-v3:company:collection')
        response = self.api_client.get(
            url,
            data={
                'sortby': 'created_on',
            },
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == len(creation_times)
        expected_timestamps = [
            format_date_or_datetime(creation_time)
            for creation_time in sorted(creation_times)
        ]
        actual_timestamps = [result['created_on'] for result in response_data['results']]
        assert expected_timestamps == actual_timestamps

    def test_list_companies_without_view_document_permission(self):
        """List the companies by user without view document permission."""
        CompanyFactory.create_batch(5, archived_documents_url_path='hello world')

        user = create_test_user(
            permission_codenames=(
                'view_company',
            ),
        )
        api_client = self.create_api_client(user=user)
        url = reverse('api-v3:company:collection')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == 5
        assert all(
            'archived_documents_url_path' not in company
            for company in response_data['results']
        )

    def test_list_companies_with_view_document_permission(self):
        """List the companies by user with view document permission."""
        CompanyFactory.create_batch(5, archived_documents_url_path='hello world')

        user = create_test_user(
            permission_codenames=(
                'view_company',
                'view_company_document',
            ),
        )
        api_client = self.create_api_client(user=user)
        url = reverse('api-v3:company:collection')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['count'] == 5
        assert all(
            company['archived_documents_url_path'] == 'hello world'
            for company in response_data['results']
        )


class TestGetCompany(APITestMixin):
    """Tests for getting a company."""

    def test_get_company_without_view_document_permission(self):
        """Tests the company item view without view document permission."""
        company = CompanyFactory(
            archived_documents_url_path='http://some-documents',
        )
        user = create_test_user(
            permission_codenames=(
                'view_company',
            ),
        )
        api_client = self.create_api_client(user=user)

        url = reverse('api-v3:company:item', kwargs={'pk': company.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'archived_documents_url_path' not in response.json()

    def test_get_company_with_company_number(self):
        """Tests the company item view for a company with a company number."""
        ch_company = CompaniesHouseCompanyFactory(
            company_number='123',
        )
        ghq = CompanyFactory(
            global_headquarters=None,
            one_list_tier=OneListTier.objects.first(),
            one_list_account_owner=AdviserFactory(),
        )
        company = CompanyFactory(
            company_number='123',
            trading_names=['Xyz trading', 'Abc trading'],
            global_headquarters=ghq,
            one_list_tier=None,
            one_list_account_owner=None,
        )
        user = create_test_user(
            permission_codenames=(
                'view_company',
                'view_company_document',
            ),
        )
        api_client = self.create_api_client(user=user)

        url = reverse('api-v3:company:item', kwargs={'pk': company.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            'id': str(company.pk),
            'companies_house_data': {
                'id': ch_company.id,
                'company_number': ch_company.company_number,
                'company_category': ch_company.company_category,
                'company_status': ch_company.company_status,
                'incorporation_date': format_date_or_datetime(ch_company.incorporation_date),
                'name': ch_company.name,
                'registered_address_1': ch_company.registered_address_1,
                'registered_address_2': ch_company.registered_address_2,
                'registered_address_town': ch_company.registered_address_town,
                'registered_address_county': ch_company.registered_address_county,
                'registered_address_postcode': ch_company.registered_address_postcode,
                'registered_address_country': {
                    'id': str(ch_company.registered_address_country.id),
                    'name': ch_company.registered_address_country.name,
                },
                'sic_code_1': ch_company.sic_code_1,
                'sic_code_2': ch_company.sic_code_2,
                'sic_code_3': ch_company.sic_code_3,
                'sic_code_4': ch_company.sic_code_4,
                'uri': ch_company.uri,
            },
            'created_on': format_date_or_datetime(company.created_on),
            'modified_on': format_date_or_datetime(company.modified_on),
            'name': company.name,
            'reference_code': company.reference_code,
            'company_number': company.company_number,
            'vat_number': company.vat_number,
            'duns_number': company.duns_number,
            'trading_names': company.trading_names,
            'registered_address_1': company.registered_address_1,
            'registered_address_2': company.registered_address_2,
            'registered_address_town': company.registered_address_town,
            'registered_address_county': company.registered_address_county,
            'registered_address_postcode': company.registered_address_postcode,
            'registered_address_country': {
                'id': str(Country.united_kingdom.value.id),
                'name': Country.united_kingdom.value.name,
            },
            'trading_address_1': company.trading_address_1,
            'trading_address_2': company.trading_address_2,
            'trading_address_country': {
                'id': str(company.trading_address_country.id),
                'name': company.trading_address_country.name,
            },
            'trading_address_county': company.trading_address_county,
            'trading_address_postcode': company.trading_address_postcode,
            'trading_address_town': company.trading_address_town,
            'uk_based': (
                company.address_country.id == uuid.UUID(Country.united_kingdom.value.id)
            ),
            'uk_region': {
                'id': str(company.uk_region.id),
                'name': company.uk_region.name,
            },
            'business_type': {
                'id': str(company.business_type.id),
                'name': company.business_type.name,
            },
            'contacts': [],
            'description': company.description,
            'employee_range': {
                'id': str(company.employee_range.id),
                'name': company.employee_range.name,
            },
            'number_of_employees': company.number_of_employees,
            'is_number_of_employees_estimated': company.is_number_of_employees_estimated,
            'export_experience_category': {
                'id': str(company.export_experience_category.id),
                'name': company.export_experience_category.name,
            },
            'export_to_countries': [],
            'future_interest_countries': [],
            'headquarter_type': company.headquarter_type,
            'sector': {
                'id': str(company.sector.id),
                'name': company.sector.name,
            },
            'turnover_range': {
                'id': str(company.turnover_range.id),
                'name': company.turnover_range.name,
            },
            'turnover': company.turnover,
            'is_turnover_estimated': company.is_turnover_estimated,
            'website': company.website,
            'global_headquarters': {
                'id': str(ghq.id),
                'name': ghq.name,
            },
            'one_list_group_tier': {
                'id': str(ghq.one_list_tier.id),
                'name': ghq.one_list_tier.name,
            },
            'one_list_group_global_account_manager': {
                'id': str(ghq.one_list_account_owner.pk),
                'name': ghq.one_list_account_owner.name,
                'first_name': ghq.one_list_account_owner.first_name,
                'last_name': ghq.one_list_account_owner.last_name,
                'dit_team': {
                    'id': str(ghq.one_list_account_owner.dit_team.id),
                    'name': ghq.one_list_account_owner.dit_team.name,
                    'uk_region': {
                        'id': str(ghq.one_list_account_owner.dit_team.uk_region.pk),
                        'name': ghq.one_list_account_owner.dit_team.uk_region.name,
                    },
                    'country': {
                        'id': str(ghq.one_list_account_owner.dit_team.country.pk),
                        'name': ghq.one_list_account_owner.dit_team.country.name,
                    },
                },
            },
            'archived_documents_url_path': company.archived_documents_url_path,
            'archived': False,
            'archived_by': None,
            'archived_on': None,
            'archived_reason': None,
            'transferred_by': None,
            'transferred_on': None,
            'transferred_to': None,
            'transfer_reason': '',
        }

    def test_get_company_without_company_number(self):
        """Tests the company item view for a company without a company number."""
        company = CompanyFactory()

        url = reverse('api-v3:company:item', kwargs={'pk': company.id})
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['companies_house_data'] is None

    def test_get_company_without_country(self):
        """
        Tests the company item view for a company without a country.

        Checks that the endpoint returns 200 and the uk_based attribute is
        set to None.
        """
        company = CompanyFactory(
            address_country_id=None,
        )

        url = reverse('api-v3:company:item', kwargs={'pk': company.id})
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['uk_based'] is None

    @pytest.mark.parametrize(
        'input_website,expected_website',
        (
            ('www.google.com', 'http://www.google.com'),
            ('http://www.google.com', 'http://www.google.com'),
            ('https://www.google.com', 'https://www.google.com'),
            ('', ''),
            (None, None),
        ),
    )
    def test_get_company_with_website(self, input_website, expected_website):
        """
        Test that if the website field on a company doesn't have any scheme
        specified, the endpoint adds it automatically.
        """
        company = CompanyFactory(
            website=input_website,
        )
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['website'] == expected_website

    @pytest.mark.parametrize(
        'build_company',
        (
            # subsidiary with Global Headquarters on the One List
            lambda one_list_tier: CompanyFactory(
                one_list_tier=None,
                global_headquarters=CompanyFactory(one_list_tier=one_list_tier),
            ),
            # subsidiary with Global Headquarters not on the One List
            lambda one_list_tier: CompanyFactory(
                one_list_tier=None,
                global_headquarters=CompanyFactory(one_list_tier=None),
            ),
            # single company on the One List
            lambda one_list_tier: CompanyFactory(
                one_list_tier=one_list_tier,
                global_headquarters=None,
            ),
            # single company not on the One List
            lambda one_list_tier: CompanyFactory(
                one_list_tier=None,
                global_headquarters=None,
            ),
        ),
        ids=(
            'as_subsidiary_of_one_list_company',
            'as_subsidiary_of_non_one_list_company',
            'as_one_list_company',
            'as_non_one_list_company',
        ),
    )
    def test_one_list_group_tier(self, build_company):
        """
        Test that the endpoint includes the One List Tier
        of the Global Headquarters in the group.
        """
        one_list_tier = OneListTier.objects.first()
        company = build_company(one_list_tier)

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        group_global_headquarters = company.global_headquarters or company

        actual_one_list_group_tier = response.json()['one_list_group_tier']
        if not group_global_headquarters.one_list_tier:
            assert not actual_one_list_group_tier
        else:
            assert actual_one_list_group_tier == {
                'id': str(one_list_tier.id),
                'name': one_list_tier.name,
            }

    @pytest.mark.parametrize(
        'build_company',
        (
            # subsidiary with Global Headquarters on the One List
            lambda one_list_tier, gam: CompanyFactory(
                one_list_tier=None,
                global_headquarters=CompanyFactory(
                    one_list_tier=one_list_tier,
                    one_list_account_owner=gam,
                ),
            ),
            # subsidiary with Global Headquarters not on the One List
            lambda one_list_tier, gam: CompanyFactory(
                one_list_tier=None,
                global_headquarters=CompanyFactory(
                    one_list_tier=None,
                    one_list_account_owner=None,
                ),
            ),
            # single company on the One List
            lambda one_list_tier, gam: CompanyFactory(
                one_list_tier=one_list_tier,
                one_list_account_owner=gam,
                global_headquarters=None,
            ),
            # single company not on the One List
            lambda one_list_tier, gam: CompanyFactory(
                one_list_tier=None,
                global_headquarters=None,
                one_list_account_owner=None,
            ),
        ),
        ids=(
            'as_subsidiary_of_one_list_company',
            'as_subsidiary_of_non_one_list_company',
            'as_one_list_company',
            'as_non_one_list_company',
        ),
    )
    def test_one_list_group_global_account_manager(self, build_company):
        """
        Test that the endpoint includes the One List Global Account Manager
        of the Global Headquarters in the group.
        """
        global_account_manager = AdviserFactory()
        one_list_tier = OneListTier.objects.first()
        company = build_company(one_list_tier, global_account_manager)

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        group_global_headquarters = company.global_headquarters or company

        actual_global_account_manager = response.json()['one_list_group_global_account_manager']
        if not group_global_headquarters.one_list_account_owner:
            assert not actual_global_account_manager
        else:
            assert actual_global_account_manager == {
                'id': str(global_account_manager.pk),
                'name': global_account_manager.name,
                'first_name': global_account_manager.first_name,
                'last_name': global_account_manager.last_name,
                'dit_team': {
                    'id': str(global_account_manager.dit_team.id),
                    'name': global_account_manager.dit_team.name,
                    'uk_region': {
                        'id': str(global_account_manager.dit_team.uk_region.pk),
                        'name': global_account_manager.dit_team.uk_region.name,
                    },
                    'country': {
                        'id': str(global_account_manager.dit_team.country.pk),
                        'name': global_account_manager.dit_team.country.name,
                    },

                },
            }


class TestUpdateCompany(APITestMixin):
    """Tests for updating a single company."""

    def test_update_company(self):
        """Test company update."""
        company = CompanyFactory(
            name='Foo ltd.',
            trading_names=['name 1', 'name 2'],
        )

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'name': 'Acme',
                'trading_names': ['new name'],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['name'] == 'Acme'
        assert response_data['trading_names'] == ['new name']

    def test_update_company_with_company_number(self):
        """
        Test updating a company that has a corresponding Companies House record.

        Updates to the name and registered address should be allowed.
        """
        CompaniesHouseCompanyFactory(
            company_number=123,
            name='Foo Ltd',
            registered_address_1='Hello St',
            registered_address_town='Fooland',
            registered_address_country_id=Country.united_states.value.id,
        )
        company = CompanyFactory(
            company_number=123,
            name='Bar Ltd',
            registered_address_1='Goodbye St',
            registered_address_town='Barland',
            registered_address_country_id=Country.united_kingdom.value.id,
        )

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})

        update_data = {
            'name': 'New name',
            'registered_address_1': 'New address 1',
            'registered_address_town': 'New town',
            'registered_address_country': Country.united_states.value.id,
        }

        response = self.api_client.patch(url, data=update_data)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['name'] == update_data['name']
        assert response_data['registered_address_1'] == update_data['registered_address_1']
        assert response_data['registered_address_town'] == update_data['registered_address_town']
        assert response_data['registered_address_country']['id'] == Country.united_states.value.id

    def test_cannot_update_read_only_fields(self):
        """Test updating read-only fields."""
        one_list_tier, different_one_list_tier = OneListTier.objects.all()[:2]
        one_list_gam, different_one_list_gam = AdviserFactory.create_batch(2)
        company = CompanyFactory(
            reference_code='ORG-345645',
            archived_documents_url_path='old_path',
            one_list_tier=one_list_tier,
            one_list_account_owner=one_list_gam,
            duns_number=None,
            turnover=100,
            is_turnover_estimated=False,
            number_of_employees=95,
            is_number_of_employees_estimated=False,
        )

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'reference_code': 'XYZ',
                'archived_documents_url_path': 'new_path',
                'one_list_group_tier': different_one_list_tier.id,
                'one_list_group_global_account_manager': different_one_list_gam.id,
                'duns_number': '000000002',
                'turnover': 101,
                'is_turnover_estimated': True,
                'number_of_employees': 96,
                'is_number_of_employees_estimated': True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['reference_code'] == 'ORG-345645'
        assert response_data['archived_documents_url_path'] == 'old_path'
        assert response_data['one_list_group_tier'] == {
            'id': str(company.one_list_tier.id),
            'name': company.one_list_tier.name,
        }
        assert response_data['one_list_group_global_account_manager']['id'] == str(one_list_gam.id)
        assert response_data['duns_number'] is None
        assert response_data['turnover'] == 100
        assert not response_data['is_turnover_estimated']
        assert response_data['number_of_employees'] == 95
        assert not response_data['is_number_of_employees_estimated']

    def test_none_address_fields_are_converted_to_blank(self):
        """
        Tests that address charfields are converted to empty strings
        if None values are used in data.
        """
        company = CompanyFactory(
            registered_address_1='lorem',
            registered_address_2='lorem',
            registered_address_town='lorem',
            registered_address_county='lorem',
            registered_address_postcode='lorem',
            registered_address_country_id=Country.united_states.value.id,
            trading_address_1='lorem',
            trading_address_2='lorem',
            trading_address_town='lorem',
            trading_address_county='lorem',
            trading_address_postcode='lorem',
            trading_address_country_id=Country.united_states.value.id,
        )

        none_fields_expected_to_become_blank = [
            'registered_address_2',
            'registered_address_county',
            'registered_address_postcode',
            'trading_address_1',
            'trading_address_2',
            'trading_address_town',
            'trading_address_county',
            'trading_address_postcode',
        ]

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                **{
                    field: None
                    for field in none_fields_expected_to_become_blank
                },
                'trading_address_country': None,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        company.refresh_from_db()

        # check that model fields are empty (not None)
        actual_model_fields = model_to_dict(
            company,
            fields=none_fields_expected_to_become_blank,
        )
        expected_model_fields = {
            field: ''
            for field in none_fields_expected_to_become_blank
        }
        assert actual_model_fields == expected_model_fields

        # check that the response fields are empty strings (not None)
        response_data = response.json()
        actual_response_fields = {
            field: response_data[field]
            for field in none_fields_expected_to_become_blank
        }
        expected_response_fields = expected_model_fields
        assert actual_response_fields == expected_response_fields

    def test_cannot_update_dnb_readonly_fields_if_duns_number_is_set(self):
        """
        Test that if company.duns_number is not blank, the client cannot update the
        fields defined by CompanySerializerV3.Meta.dnb_read_only_fields.
        """
        company = CompanyFactory(
            duns_number='012345678',
            name='name',
            trading_names=['a', 'b', 'c'],
            company_number='company number',
            vat_number='vat number',
            registered_address_1='registered address 1',
            registered_address_2='registered address 2',
            registered_address_town='registered address town',
            registered_address_county='registered address county',
            registered_address_postcode='registered address postcode',
            registered_address_country_id=Country.anguilla.value.id,
            website='website',
            trading_address_1='trading address 1',
            trading_address_2='trading address 2',
            trading_address_town='trading address town',
            trading_address_county='trading address county',
            trading_address_postcode='trading address postcode',
            trading_address_country_id=Country.argentina.value.id,
            business_type_id=BusinessTypeConstant.charity.value.id,
            employee_range_id=EmployeeRange.range_10_to_49.value.id,
            turnover_range_id=TurnoverRange.range_1_34_to_6_7.value.id,
            headquarter_type_id=HeadquarterType.ehq.value.id,
            global_headquarters_id=CompanyFactory(
                headquarter_type_id=HeadquarterType.ghq.value.id,
            ).id,
        )

        data = {
            'name': 'new name',
            'trading_names': ['new trading name'],
            'company_number': 'new company number',
            'vat_number': 'new vat number',
            'registered_address_1': 'new registered address 1',
            'registered_address_2': 'new registered address 2',
            'registered_address_town': 'new registered address town',
            'registered_address_county': 'new registered address county',
            'registered_address_postcode': 'new registered address postcode',
            'registered_address_country': Country.azerbaijan.value.id,
            'website': 'new website',
            'trading_address_1': 'new trading address 1',
            'trading_address_2': 'new trading address 2',
            'trading_address_town': 'new trading address town',
            'trading_address_county': 'new trading address county',
            'trading_address_postcode': 'new trading address postcode',
            'trading_address_country': Country.canada.value.id,
            'business_type': BusinessTypeConstant.community_interest_company.value.id,
            'employee_range': EmployeeRange.range_1_to_9.value.id,
            'turnover_range': TurnoverRange.range_33_5_plus.value.id,
            'headquarter_type': HeadquarterType.ghq.value.id,
            'global_headquarters': company.id,
        }

        assert set(data.keys()) == set(CompanySerializerV3.Meta.dnb_read_only_fields), (
            'It looks like you have changed CompanySerializerV3.Meta.dnb_read_only_fields, '
            'please update this test accordingly.'
        )

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        for field, value in data.items():
            assert response_data[field] != value

    @pytest.mark.parametrize(
        'data,expected_error',
        (
            # trading names too long
            (
                {'trading_names': ['a' * 600]},
                {'trading_names': {'0': ['Ensure this field has no more than 255 characters.']}},
            ),
            # sector cannot become nullable
            (
                {'sector': None},
                {'sector': ['This field is required.']},
            ),
        ),
    )
    def test_validation_error(self, data, expected_error):
        """Test validation scenarios."""
        company = CompanyFactory()

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data=data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_error

    @pytest.mark.parametrize('field', ('sector',))
    def test_update_null_field_to_null(self, field):
        """
        Tests setting fields to null that are currently null, and are allowed to be null
        when already null.
        """
        company = CompanyFactory(**{f'{field}_id': None})

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                field: None,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()[field] is None

    @pytest.mark.parametrize(
        'hq,is_valid',
        (
            (HeadquarterType.ehq.value.id, False),
            (HeadquarterType.ukhq.value.id, False),
            (HeadquarterType.ghq.value.id, True),
            (None, False),
        ),
    )
    def test_update_company_global_headquarters_with_not_a_global_headquarters(self, hq, is_valid):
        """
        Tests if adding company that is not a Global HQ as a Global HQ
        will fail or if added company is a Global HQ then it will pass.
        """
        company = CompanyFactory()
        headquarter = CompanyFactory(headquarter_type_id=hq)

        # now update it
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'global_headquarters': headquarter.id,
            },
        )
        response_data = response.json()
        if is_valid:
            assert response.status_code == status.HTTP_200_OK
            if hq is not None:
                assert response_data['global_headquarters']['id'] == str(headquarter.id)
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            error = ['Company to be linked as global headquarters must be a global headquarters.']
            assert response_data['global_headquarters'] == error

    def test_remove_global_headquarters_link(self):
        """Tests that we can remove global headquarter link."""
        global_headquarters = CompanyFactory(
            headquarter_type_id=HeadquarterType.ghq.value.id,
        )
        company = CompanyFactory(global_headquarters=global_headquarters)

        assert global_headquarters.subsidiaries.count() == 1

        # now update it
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'global_headquarters': None,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['global_headquarters'] is None

        assert global_headquarters.subsidiaries.count() == 0

    def test_cannot_point_company_to_itself_as_global_headquarters(self):
        """Test that you cannot point company as its own global headquarters."""
        company = CompanyFactory(
            headquarter_type_id=HeadquarterType.ghq.value.id,
        )

        # now update it
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'global_headquarters': company.id,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = ['Global headquarters cannot point to itself.']
        assert response.json()['global_headquarters'] == error

    def test_subsidiary_cannot_become_a_global_headquarters(self):
        """Tests that subsidiary cannot become a global headquarter."""
        global_headquarters = CompanyFactory(
            headquarter_type_id=HeadquarterType.ghq.value.id,
        )
        company = CompanyFactory(
            headquarter_type_id=None,
            global_headquarters=global_headquarters,
        )

        assert global_headquarters.subsidiaries.count() == 1

        # now update it
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'headquarter_type': HeadquarterType.ghq.value.id,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = ['A company cannot both be and have a global headquarters.']
        assert response.json()['headquarter_type'] == error

    @pytest.mark.parametrize(
        'headquarter_type_id,changed_to,has_subsidiaries,is_valid',
        (
            (HeadquarterType.ghq.value.id, None, True, False),
            (HeadquarterType.ghq.value.id, HeadquarterType.ehq.value.id, True, False),
            (HeadquarterType.ghq.value.id, HeadquarterType.ehq.value.id, False, True),
            (HeadquarterType.ghq.value.id, None, False, True),
        ),
    )
    def test_update_headquarter_type(
        self,
        headquarter_type_id,
        changed_to,
        has_subsidiaries,
        is_valid,
    ):
        """Test updating headquarter type."""
        company = CompanyFactory(
            headquarter_type_id=headquarter_type_id,
        )
        if has_subsidiaries:
            CompanyFactory(global_headquarters=company)
            assert company.subsidiaries.count() == 1

        # now update it
        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(
            url,
            data={
                'headquarter_type': changed_to,
            },
        )

        response_data = response.json()
        if is_valid:
            assert response.status_code == status.HTTP_200_OK
            assert response_data['id'] == str(company.id)
            company.refresh_from_db()
            assert str(company.headquarter_type_id) == str(changed_to)
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            error = ['Subsidiaries have to be unlinked before changing headquarter type.']
            assert response_data['headquarter_type'] == error


class TestAddressesForCompany(APITestMixin):
    """
    Tests related to saving the value of address fields from trading or registered address fields.

    TODO: delete after the migration to address and registered address is completed
    """

    @pytest.mark.parametrize(
        'data,expected_model_values',
        (
            # with trading address
            (
                {
                    'registered_address_1': '75',
                    'registered_address_2': 'Stramford Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Clapham',
                    'registered_address_postcode': 'SW4 0BG',
                    'registered_address_country': Country.united_kingdom.value.id,

                    'trading_address_1': '1',
                    'trading_address_2': 'Hello st.',
                    'trading_address_town': 'Muckamore',
                    'trading_address_county': 'Antrim',
                    'trading_address_postcode': 'BT41 4QE',
                    'trading_address_country': {'id': Country.ireland.value.id},
                },
                {
                    'address_1': '1',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': uuid.UUID(Country.ireland.value.id),
                },
            ),

            # with None values for trading address
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country': {'id': Country.united_kingdom.value.id},

                    'trading_address_1': None,
                    'trading_address_2': None,
                    'trading_address_town': None,
                    'trading_address_county': None,
                    'trading_address_postcode': None,
                    'trading_address_country': None,
                },
                {
                    'address_1': '2',
                    'address_2': 'Main Road',
                    'address_town': 'London',
                    'address_county': 'Greenwich',
                    'address_postcode': 'SE10 9NN',
                    'address_country_id': uuid.UUID(Country.united_kingdom.value.id),
                },
            ),

            # without trading address
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country': {'id': Country.united_kingdom.value.id},
                },
                {
                    'address_1': '2',
                    'address_2': 'Main Road',
                    'address_town': 'London',
                    'address_county': 'Greenwich',
                    'address_postcode': 'SE10 9NN',
                    'address_country_id': uuid.UUID(Country.united_kingdom.value.id),
                },
            ),
        ),
    )
    def test_add_company_saves_address_correctly(self, data, expected_model_values):
        """
        Test that the value of address fields are populated from trading address or
        registered address whichever is defined.
        """
        post_data = {
            'name': 'Acme',
            'business_type': BusinessTypeConstant.company.value.id,
            'sector': random_obj_for_model(Sector).id,
            'uk_region': UKRegion.england.value.id,
            **data,
        }

        url = reverse('api-v3:company:collection')
        response = self.api_client.post(url, data=post_data)

        assert response.status_code == status.HTTP_201_CREATED
        company = Company.objects.get(pk=response.json()['id'])
        for field, value in expected_model_values.items():
            assert getattr(company, field) == value

    @pytest.mark.parametrize(
        'initial_model_values,data,expected_model_values',
        (
            # address fields populated from trading address fields in data
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country_id': Country.united_kingdom.value.id,

                    'trading_address_1': '',
                    'trading_address_2': '',
                    'trading_address_town': '',
                    'trading_address_county': '',
                    'trading_address_postcode': '',
                    'trading_address_country_id': None,
                },
                {
                    'trading_address_1': '1',
                    'trading_address_2': 'Hello st.',
                    'trading_address_town': 'Muckamore',
                    'trading_address_county': 'Antrim',
                    'trading_address_postcode': 'BT41 4QE',
                    'trading_address_country': {'id': Country.ireland.value.id},
                },
                {
                    'address_1': '1',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': uuid.UUID(Country.ireland.value.id),
                },
            ),

            # address fields populated from registered address fields in data
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country_id': Country.united_kingdom.value.id,

                    'trading_address_1': '',
                    'trading_address_2': '',
                    'trading_address_town': '',
                    'trading_address_county': '',
                    'trading_address_postcode': '',
                    'trading_address_country_id': None,
                },
                {
                    'registered_address_1': '1',
                    'registered_address_2': 'Hello st.',
                    'registered_address_town': 'Muckamore',
                    'registered_address_county': 'Antrim',
                    'registered_address_postcode': 'BT41 4QE',
                    'registered_address_country': {'id': Country.ireland.value.id},
                },
                {
                    'address_1': '1',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': uuid.UUID(Country.ireland.value.id),
                },
            ),

            # address fields populated from trading address fields in the model
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country_id': Country.united_kingdom.value.id,

                    'trading_address_1': '1',
                    'trading_address_2': 'Hello st.',
                    'trading_address_town': 'Muckamore',
                    'trading_address_county': 'Antrim',
                    'trading_address_postcode': 'BT41 4QE',
                    'trading_address_country_id': Country.ireland.value.id,
                },
                {
                    'registered_address_1': '3',
                },
                {
                    'address_1': '1',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': uuid.UUID(Country.ireland.value.id),
                },
            ),

            # address fields populated from registered address fields in the model
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country_id': Country.united_kingdom.value.id,

                    'trading_address_1': '1',
                    'trading_address_2': 'Hello st.',
                    'trading_address_town': 'Muckamore',
                    'trading_address_county': 'Antrim',
                    'trading_address_postcode': 'BT41 4QE',
                    'trading_address_country_id': Country.ireland.value.id,
                },
                {
                    'trading_address_1': '',
                    'trading_address_2': '',
                    'trading_address_town': '',
                    'trading_address_county': '',
                    'trading_address_postcode': '',
                    'trading_address_country': None,
                },
                {
                    'address_1': '2',
                    'address_2': 'Main Road',
                    'address_town': 'London',
                    'address_county': 'Greenwich',
                    'address_postcode': 'SE10 9NN',
                    'address_country_id': uuid.UUID(Country.united_kingdom.value.id),
                },
            ),

            # address is not overridden as no address field was passed in
            (
                {
                    'registered_address_1': '2',
                    'registered_address_2': 'Main Road',
                    'registered_address_town': 'London',
                    'registered_address_county': 'Greenwich',
                    'registered_address_postcode': 'SE10 9NN',
                    'registered_address_country_id': Country.united_kingdom.value.id,

                    'trading_address_1': '',
                    'trading_address_2': '',
                    'trading_address_town': '',
                    'trading_address_county': '',
                    'trading_address_postcode': '',
                    'trading_address_country_id': None,

                    'address_1': '11',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': Country.ireland.value.id,
                },
                {
                    'name': 'other name',
                },
                {

                    'address_1': '11',
                    'address_2': 'Hello st.',
                    'address_town': 'Muckamore',
                    'address_county': 'Antrim',
                    'address_postcode': 'BT41 4QE',
                    'address_country_id': uuid.UUID(Country.ireland.value.id),
                },
            ),
        ),
    )
    def test_update_company_saves_address_correctly(
        self,
        initial_model_values,
        data,
        expected_model_values,
    ):
        """
        Test that the value of address fields are populated from trading address or
        registered address whichever is defined.
        """
        company = CompanyFactory(**initial_model_values)

        url = reverse('api-v3:company:item', kwargs={'pk': company.pk})
        response = self.api_client.patch(url, data=data)

        assert response.status_code == status.HTTP_200_OK
        company.refresh_from_db()
        for field, value in expected_model_values.items():
            assert getattr(company, field) == value


class TestAddCompany(APITestMixin):
    """Tests for adding a company."""

    @pytest.mark.parametrize(
        'data,expected_response',
        (
            # uk company
            (
                {
                    'name': 'Acme',
                    'trading_names': ['Trading name'],
                    'business_type': {'id': BusinessTypeConstant.company.value.id},
                    'registered_address_country': {
                        'id': Country.united_kingdom.value.id,
                    },
                    'registered_address_1': '75 Stramford Road',
                    'registered_address_town': 'London',
                    'uk_region': {'id': UKRegion.england.value.id},
                    'headquarter_type': {'id': HeadquarterType.ghq.value.id},
                },
                {
                    'name': 'Acme',
                    'trading_names': ['Trading name'],
                    'business_type': {
                        'id': BusinessTypeConstant.company.value.id,
                        'name': BusinessTypeConstant.company.value.name,
                    },
                    'registered_address_country': {
                        'id': Country.united_kingdom.value.id,
                        'name': Country.united_kingdom.value.name,
                    },
                    'registered_address_1': '75 Stramford Road',
                    'registered_address_town': 'London',
                    'uk_region': {
                        'id': UKRegion.england.value.id,
                        'name': UKRegion.england.value.name,
                    },
                    'headquarter_type': {
                        'id': HeadquarterType.ghq.value.id,
                        'name': HeadquarterType.ghq.value.name,
                    },
                },
            ),
            # non-UK
            (
                {
                    'registered_address_country': {'id': Country.united_states.value.id},
                    'registered_address_1': '75 Stramford Road',
                    'registered_address_town': 'Cordova',
                },
                {
                    'registered_address_country': {
                        'id': Country.united_states.value.id,
                        'name': Country.united_states.value.name,
                    },
                    'registered_address_1': '75 Stramford Road',
                    'registered_address_town': 'Cordova',
                },
            ),
            # promote a CH company
            (
                {
                    'company_number': '1234567890',
                    'business_type': BusinessTypeConstant.company.value.id,
                },
                {'company_number': '1234567890'},
            ),
            # no special validation on company_number is done for non UK establishment companies
            (
                {
                    'business_type': BusinessTypeConstant.company.value.id,
                    'company_number': 'sc000444é',
                },
                {'company_number': 'sc000444é'},
            ),
            # UK establishment with correct company_number format
            (
                {
                    'business_type': {'id': BusinessTypeConstant.uk_establishment.value.id},
                    'company_number': 'BR000006',
                },
                {'company_number': 'BR000006'},
            ),
            # http:// is prepended to the website if a scheme is not present
            (
                {'website': 'www.google.com'},
                {'website': 'http://www.google.com'},
            ),
            # website is not converted if it includes an http scheme
            (
                {'website': 'http://www.google.com'},
                {'website': 'http://www.google.com'},
            ),
            # website is not converted if it includes an http scheme
            (
                {'website': 'https://www.google.com'},
                {'website': 'https://www.google.com'},
            ),
            # website is not converted if it's empty
            (
                {'website': ''},
                {'website': ''},
            ),
            # website is not converted if it's None
            (
                {'website': None},
                {'website': None},
            ),
            # trading address is saved
            (
                {
                    'trading_address_country': {'id': Country.ireland.value.id},
                    'trading_address_1': '1 Hello st.',
                    'trading_address_town': 'Dublin',
                },
                {
                    'trading_address_country': {
                        'id': Country.ireland.value.id,
                        'name': Country.ireland.value.name,
                    },
                    'trading_address_1': '1 Hello st.',
                    'trading_address_town': 'Dublin',
                },
            ),
        ),
    )
    def test_success_cases(self, data, expected_response):
        """Test success scenarios."""
        post_data = {
            'name': 'Acme',
            'business_type': BusinessTypeConstant.company.value.id,
            'sector': random_obj_for_model(Sector).id,
            'registered_address_1': '75 Stramford Road',
            'registered_address_town': 'London',
            'registered_address_country': Country.united_kingdom.value.id,
            'uk_region': UKRegion.england.value.id,
        }
        post_data.update(data)

        url = reverse('api-v3:company:collection')
        response = self.api_client.post(
            url,
            data=post_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        for field, value in expected_response.items():
            assert response_data[field] == value

    def test_none_address_fields_are_converted_to_blank(self):
        """
        Tests that address charfields are converted to empty strings
        if None values are used in data.
        """
        none_fields_expected_to_become_blank = [
            'registered_address_2',
            'registered_address_county',
            'registered_address_postcode',
            'trading_address_1',
            'trading_address_2',
            'trading_address_town',
            'trading_address_county',
            'trading_address_postcode',
        ]

        url = reverse('api-v3:company:collection')
        response = self.api_client.post(
            url,
            data={
                'name': 'Acme',
                'business_type': BusinessTypeConstant.company.value.id,
                'sector': random_obj_for_model(Sector).id,
                'registered_address_1': '75 Stramford Road',
                'registered_address_town': 'London',
                'registered_address_country': Country.united_kingdom.value.id,
                'trading_address_country': None,
                'uk_region': UKRegion.england.value.id,

                **{
                    field: None
                    for field in none_fields_expected_to_become_blank
                },
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()

        company = Company.objects.get(pk=response_data['id'])

        # check that model fields are empty strings (not None)
        actual_model_fields = model_to_dict(
            company,
            fields=none_fields_expected_to_become_blank,
        )
        expected_model_fields = {
            field: ''
            for field in none_fields_expected_to_become_blank
        }
        assert actual_model_fields == expected_model_fields

        # check that the response fields are empty strings (not None)
        response_data = response.json()
        actual_response_fields = {
            field: response_data[field]
            for field in none_fields_expected_to_become_blank
        }
        expected_response_fields = expected_model_fields
        assert actual_response_fields == expected_response_fields

    def test_required_fields(self):
        """Test required fields."""
        url = reverse('api-v3:company:collection')
        response = self.api_client.post(
            url,
            data={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            'name': ['This field is required.'],
            'registered_address_1': ['This field is required.'],
            'registered_address_town': ['This field is required.'],
            'registered_address_country': ['This field is required.'],
        }

    @pytest.mark.parametrize(
        'data,expected_error',
        (
            # uk_region is required
            (
                {'uk_region': None},
                {'uk_region': ['This field is required.']},
            ),
            # partial trading address, other trading fields are required
            (
                {'trading_address_1': 'test'},
                {
                    'trading_address_town': ['This field is required.'],
                    'trading_address_country': ['This field is required.'],
                },
            ),
            # registered address cannot be null
            (
                {
                    'registered_address_1': None,
                    'registered_address_town': None,
                    'registered_address_country': None,
                },
                {
                    'registered_address_1': ['This field may not be null.'],
                    'registered_address_town': ['This field may not be null.'],
                    'registered_address_country': ['This field may not be null.'],
                },
            ),
            # company_number required if business type == uk establishment
            (
                {
                    'business_type': {'id': BusinessTypeConstant.uk_establishment.value.id},
                    'registered_address_country': Country.united_kingdom.value.id,
                    'company_number': '',
                },
                {
                    'company_number': ['This field is required.'],
                },
            ),
            # country should be UK if business type == uk establishment
            (
                {
                    'business_type': {'id': BusinessTypeConstant.uk_establishment.value.id},
                    'registered_address_country': {'id': Country.united_states.value.id},
                    'company_number': 'BR1234',
                },
                {
                    'registered_address_country':
                        ['A UK establishment (branch of non-UK company) must be in the UK.'],
                },
            ),
            # company_number should start with BR if business type == uk establishment
            (
                {
                    'business_type': {'id': BusinessTypeConstant.uk_establishment.value.id},
                    'registered_address_country': Country.united_kingdom.value.id,
                    'company_number': '123',
                },
                {
                    'company_number':
                        ['This must be a valid UK establishment number, beginning with BR.'],
                },
            ),
            # company_number shouldn't have invalid characters
            (
                {
                    'business_type': {'id': BusinessTypeConstant.uk_establishment.value.id},
                    'registered_address_country': Country.united_kingdom.value.id,
                    'company_number': 'BR000444é',
                },
                {
                    'company_number':
                        [
                            'This field can only contain the letters A to Z and numbers '
                            '(no symbols, punctuation or spaces).',
                        ],
                },
            ),
        ),
    )
    def test_validation_error(self, data, expected_error):
        """Test validation scenarios."""
        post_data = {
            'name': 'Acme',
            'business_type': BusinessTypeConstant.company.value.id,
            'sector': random_obj_for_model(Sector).id,
            'registered_address_1': '75 Stramford Road',
            'registered_address_town': 'London',
            'registered_address_country': Country.united_kingdom.value.id,
            'uk_region': UKRegion.england.value.id,
        }
        post_data.update(data)

        url = reverse('api-v3:company:collection')
        response = self.api_client.post(
            url,
            data=post_data,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == expected_error


class TestArchiveCompany(APITestMixin):
    """Archive company tests."""

    def test_archive_company_no_reason(self):
        """Test company archive."""
        company = CompanyFactory()
        url = reverse('api-v3:company:archive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            'reason': ['This field is required.'],
        }

    def test_archive_company_reason(self):
        """Test company archive."""
        company = CompanyFactory()
        url = reverse('api-v3:company:archive', kwargs={'pk': company.id})
        response = self.api_client.post(url, data={'reason': 'foo'})

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['archived']
        assert response_data['archived_reason'] == 'foo'
        assert response_data['id'] == str(company.id)

    def test_archive_company_invalid_address(self):
        """
        Test archiving a company when the company has an invalid trading address and missing
        UK region.
        """
        company = CompanyFactory(
            registered_address_country_id=Country.united_kingdom.value.id,
            trading_address_town='',
            uk_region_id=None,
        )
        url = reverse('api-v3:company:archive', kwargs={'pk': company.id})
        response = self.api_client.post(url, data={'reason': 'foo'})

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['archived']
        assert response_data['archived_reason'] == 'foo'


class TestUnarchiveCompany(APITestMixin):
    """Unarchive company tests."""

    def test_unarchive_company_invalid_address(self):
        """
        Test unarchiving a company when the company has an invalid trading address and missing
        UK region.
        """
        company = CompanyFactory(
            registered_address_country_id=Country.united_kingdom.value.id,
            trading_address_town='',
            uk_region_id=None,
            archived=True,
            archived_reason='Dissolved',
        )
        url = reverse('api-v3:company:unarchive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert not response.json()['archived']

    def test_unarchive_company(self):
        """Unarchive a company."""
        company = CompanyFactory(
            archived=True, archived_on=now(), archived_reason='foo',
        )
        url = reverse('api-v3:company:unarchive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert not response_data['archived']
        assert response_data['archived_reason'] == ''
        assert response_data['id'] == str(company.id)

    def test_cannot_unarchive_duplicate_company(self):
        """Test that a duplicate company cannot be unarchived."""
        company = DuplicateCompanyFactory()
        url = reverse('api-v3:company:unarchive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            api_settings.NON_FIELD_ERRORS_KEY:
                [
                    'This record is no longer in use and its data has been transferred to another '
                    'record for the following reason: Duplicate record.',
                ],
        }


class TestCompanyVersioning(APITestMixin):
    """
    Tests for versions created when interacting with the company endpoints.
    """

    def test_add_creates_a_new_version(self):
        """Test that creating a company creates a new version."""
        assert Version.objects.count() == 0

        response = self.api_client.post(
            reverse('api-v3:company:collection'),
            data={
                'name': 'Acme',
                'trading_names': ['Trading name'],
                'business_type': {'id': BusinessTypeConstant.company.value.id},
                'sector': {'id': random_obj_for_model(Sector).id},
                'registered_address_country': {
                    'id': Country.united_kingdom.value.id,
                },
                'registered_address_1': '75 Stramford Road',
                'registered_address_town': 'London',
                'uk_region': {'id': UKRegion.england.value.id},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data['name'] == 'Acme'
        assert response_data['trading_names'] == ['Trading name']

        company = Company.objects.get(pk=response_data['id'])

        # check version created
        assert Version.objects.get_for_object(company).count() == 1
        version = Version.objects.get_for_object(company).first()
        assert version.revision.user == self.user
        assert version.field_dict['name'] == 'Acme'
        assert version.field_dict['trading_names'] == ['Trading name']
        assert not any(set(version.field_dict) & set(EXCLUDED_BASE_MODEL_FIELDS))

    def test_promoting_a_ch_company_creates_a_new_version(self):
        """Test that promoting a CH company to full company creates a new version."""
        assert Version.objects.count() == 0
        CompaniesHouseCompanyFactory(company_number=1234567890)

        response = self.api_client.post(
            reverse('api-v3:company:collection'),
            data={
                'name': 'Acme',
                'company_number': 1234567890,
                'business_type': BusinessTypeConstant.company.value.id,
                'sector': random_obj_for_model(Sector).id,
                'registered_address_country': Country.united_kingdom.value.id,
                'registered_address_1': '75 Stramford Road',
                'registered_address_town': 'London',
                'uk_region': UKRegion.england.value.id,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        company = Company.objects.get(pk=response.json()['id'])

        # check version created
        assert Version.objects.get_for_object(company).count() == 1
        version = Version.objects.get_for_object(company).first()
        assert version.field_dict['company_number'] == '1234567890'

    def test_add_400_doesnt_create_a_new_version(self):
        """Test that if the endpoint returns 400, no version is created."""
        assert Version.objects.count() == 0

        response = self.api_client.post(
            reverse('api-v3:company:collection'),
            data={'name': 'Acme'},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Version.objects.count() == 0

    def test_update_creates_a_new_version(self):
        """Test that updating a company creates a new version."""
        company = CompanyFactory(name='Foo ltd.')

        assert Version.objects.get_for_object(company).count() == 0

        response = self.api_client.patch(
            reverse('api-v3:company:item', kwargs={'pk': company.pk}),
            data={'name': 'Acme'},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['name'] == 'Acme'

        # check version created
        assert Version.objects.get_for_object(company).count() == 1
        version = Version.objects.get_for_object(company).first()
        assert version.revision.user == self.user
        assert version.field_dict['name'] == 'Acme'

    def test_update_400_doesnt_create_a_new_version(self):
        """Test that if the endpoint returns 400, no version is created."""
        company = CompanyFactory()

        response = self.api_client.patch(
            reverse('api-v3:company:item', kwargs={'pk': company.pk}),
            data={'trading_names': ['a' * 600]},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Version.objects.get_for_object(company).count() == 0

    def test_archive_creates_a_new_version(self):
        """Test that archiving a company creates a new version."""
        company = CompanyFactory()
        assert Version.objects.get_for_object(company).count() == 0

        url = reverse('api-v3:company:archive', kwargs={'pk': company.id})
        response = self.api_client.post(url, data={'reason': 'foo'})

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['archived']
        assert response_data['archived_reason'] == 'foo'

        # check version created
        assert Version.objects.get_for_object(company).count() == 1
        version = Version.objects.get_for_object(company).first()
        assert version.revision.user == self.user
        assert version.field_dict['archived']
        assert version.field_dict['archived_reason'] == 'foo'

    def test_archive_400_doesnt_create_a_new_version(self):
        """Test that if the endpoint returns 400, no version is created."""
        company = CompanyFactory()
        assert Version.objects.get_for_object(company).count() == 0

        url = reverse('api-v3:company:archive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Version.objects.get_for_object(company).count() == 0

    def test_unarchive_creates_a_new_version(self):
        """Test that unarchiving a company creates a new version."""
        company = CompanyFactory(
            archived=True, archived_on=now(), archived_reason='foo',
        )
        assert Version.objects.get_for_object(company).count() == 0

        url = reverse('api-v3:company:unarchive', kwargs={'pk': company.id})
        response = self.api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert not response_data['archived']
        assert response_data['archived_reason'] == ''

        # check version created
        assert Version.objects.get_for_object(company).count() == 1
        version = Version.objects.get_for_object(company).first()
        assert version.revision.user == self.user
        assert not version.field_dict['archived']


class TestAuditLogView(APITestMixin):
    """Tests for the audit log view."""

    def test_audit_log_view(self):
        """Test retrieval of audit log."""
        initial_datetime = now()
        with reversion.create_revision():
            company = CompanyFactory(
                description='Initial desc',
            )

            reversion.set_comment('Initial')
            reversion.set_date_created(initial_datetime)
            reversion.set_user(self.user)

        changed_datetime = now()
        with reversion.create_revision():
            company.description = 'New desc'
            company.save()

            reversion.set_comment('Changed')
            reversion.set_date_created(changed_datetime)
            reversion.set_user(self.user)

        versions = Version.objects.get_for_object(company)
        version_id = versions[0].id
        url = reverse('api-v3:company:audit-item', kwargs={'pk': company.pk})

        response = self.api_client.get(url)
        response_data = response.json()['results']

        # No need to test the whole response
        assert len(response_data) == 1
        entry = response_data[0]

        assert entry['id'] == version_id
        assert entry['user']['name'] == self.user.name
        assert entry['comment'] == 'Changed'
        assert entry['timestamp'] == format_date_or_datetime(changed_datetime)
        assert entry['changes']['description'] == ['Initial desc', 'New desc']
        assert not set(EXCLUDED_BASE_MODEL_FIELDS) & entry['changes'].keys()


class TestOneListGroupCoreTeam(APITestMixin):
    """Tests for getting the One List Core Team of a company's group."""

    @pytest.mark.parametrize(
        'build_company',
        (
            # as subsidiary
            lambda: CompanyFactory(
                global_headquarters=CompanyFactory(one_list_account_owner=None),
            ),
            # as single company
            lambda: CompanyFactory(
                global_headquarters=None,
                one_list_account_owner=None,
            ),
        ),
        ids=('as_subsidiary', 'as_non_subsidiary'),
    )
    def test_empty_list(self, build_company):
        """
        Test that if there's no Global Account Manager and no Core Team
        member for a company's Global Headquarters, the endpoint returns
        an empty list.
        """
        company = build_company()

        url = reverse(
            'api-v3:company:one-list-group-core-team',
            kwargs={'pk': company.pk},
        )
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.parametrize(
        'build_company',
        (
            # as subsidiary
            lambda gam: CompanyFactory(
                global_headquarters=CompanyFactory(one_list_account_owner=gam),
            ),
            # as single company
            lambda gam: CompanyFactory(
                global_headquarters=None,
                one_list_account_owner=gam,
            ),
        ),
        ids=('as_subsidiary', 'as_non_subsidiary'),
    )
    def test_with_only_global_account_manager(self, build_company):
        """
        Test that if there is a Global Account Manager but no Core Team
        member for a company's Global Headquarters, the endpoint returns
        a list with only that adviser in it.
        """
        global_account_manager = AdviserFactory()
        company = build_company(global_account_manager)

        url = reverse(
            'api-v3:company:one-list-group-core-team',
            kwargs={'pk': company.pk},
        )
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [
            {
                'adviser': {
                    'id': str(global_account_manager.pk),
                    'name': global_account_manager.name,
                    'first_name': global_account_manager.first_name,
                    'last_name': global_account_manager.last_name,
                    'dit_team': {
                        'id': str(global_account_manager.dit_team.pk),
                        'name': global_account_manager.dit_team.name,
                        'uk_region': {
                            'id': str(global_account_manager.dit_team.uk_region.pk),
                            'name': global_account_manager.dit_team.uk_region.name,
                        },
                        'country': {
                            'id': str(global_account_manager.dit_team.country.pk),
                            'name': global_account_manager.dit_team.country.name,
                        },
                    },
                },
                'is_global_account_manager': True,
            },
        ]

    @pytest.mark.parametrize(
        'build_company',
        (
            # as subsidiary
            lambda gam: CompanyFactory(
                global_headquarters=CompanyFactory(one_list_account_owner=gam),
            ),
            # as single company
            lambda gam: CompanyFactory(
                global_headquarters=None,
                one_list_account_owner=gam,
            ),
        ),
        ids=('as_subsidiary', 'as_non_subsidiary'),
    )
    @pytest.mark.parametrize(
        'with_global_account_manager',
        (True, False),
        ids=lambda val: f'{"With" if val else "Without"} global account manager',
    )
    def test_with_core_team_members(self, build_company, with_global_account_manager):
        """
        Test that if there are Core Team members for a company's Global Headquarters,
        the endpoint returns a list with these advisers in it.
        """
        team_member_advisers = AdviserFactory.create_batch(
            3,
            first_name=factory.Iterator(
                ('Adam', 'Barbara', 'Chris'),
            ),
        )
        global_account_manager = team_member_advisers[0] if with_global_account_manager else None

        company = build_company(global_account_manager)
        group_global_headquarters = company.global_headquarters or company
        OneListCoreTeamMemberFactory.create_batch(
            len(team_member_advisers),
            company=group_global_headquarters,
            adviser=factory.Iterator(team_member_advisers),
        )

        url = reverse(
            'api-v3:company:one-list-group-core-team',
            kwargs={'pk': company.pk},
        )
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [
            {
                'adviser': {
                    'id': str(adviser.pk),
                    'name': adviser.name,
                    'first_name': adviser.first_name,
                    'last_name': adviser.last_name,
                    'dit_team': {
                        'id': str(adviser.dit_team.pk),
                        'name': adviser.dit_team.name,
                        'uk_region': {
                            'id': str(adviser.dit_team.uk_region.pk),
                            'name': adviser.dit_team.uk_region.name,
                        },
                        'country': {
                            'id': str(adviser.dit_team.country.pk),
                            'name': adviser.dit_team.country.name,
                        },
                    },
                },
                'is_global_account_manager': adviser is global_account_manager,
            }
            for adviser in team_member_advisers
        ]

    def test_404_with_invalid_company(self):
        """
        Test that if the company doesn't exist, the endpoint returns 404.
        """
        url = reverse(
            'api-v3:company:one-list-group-core-team',
            kwargs={'pk': '00000000-0000-0000-0000-000000000000'},
        )
        response = self.api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
