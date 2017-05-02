import pytest

from datahub.company.models import Company
from datahub.company.test.factories import AdvisorFactory, CompanyFactory
from datahub.core import constants

# mark the whole module for db use
pytestmark = pytest.mark.django_db


def test_company_model_sets_classification_to_undefined():
    """Test setting classification to undef by default."""
    company = CompanyFactory()  # Calls save
    assert company.classification_id == constants.CompanyClassification.undefined.value.id


def test_company_can_have_one_list_owner_assigned():
    """Test that company can have one list owner assigned."""
    company = CompanyFactory()
    advisor = AdvisorFactory()

    assert company.one_list_account_owner is None  # Test that it's nullable

    company.one_list_account_owner = advisor
    company.save()

    # re-fetch object for completeness
    company_refetch = Company.objects.get(pk=str(company.pk))

    assert str(company_refetch.one_list_account_owner_id) == str(advisor.pk)


def test_company_can_have_hierarchy():
    """Test that company can have hierarchy."""
    first_company = CompanyFactory()
    second_company = CompanyFactory()

    assert first_company.parent is None
    assert first_company.subsidiaries.count() == 0
    assert second_company.parent is None
    assert second_company.subsidiaries.count() == 0

    second_company.parent = first_company
    second_company.save()

    first_company.refresh_from_db()
    second_company.refresh_from_db()

    assert second_company.parent is first_company
    assert second_company in first_company.subsidiaries.all()