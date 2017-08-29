import pytest

from datahub.interaction.test.factories import InteractionFactory
from datahub.investment.test.factories import InvestmentProjectFactory
from datahub.search.interaction.models import Interaction

pytestmark = pytest.mark.django_db


def test_interaction_to_dict():
    """Test converting an interaction to a dict."""
    interaction = InteractionFactory(
        investment_project=InvestmentProjectFactory()
    )

    result = Interaction.dbmodel_to_dict(interaction)

    assert result == {
        'id': str(interaction.pk),
        'date': interaction.date,
        'company': {
            'id': str(interaction.company.pk),
            'name': interaction.company.name,
        },
        'contact': {
            'id': str(interaction.contact.pk),
            'first_name': interaction.contact.first_name,
            'name': interaction.contact.name,
            'last_name': interaction.contact.last_name,
        },
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
        'interaction_type': {
            'id': str(interaction.interaction_type.pk),
            'name': interaction.interaction_type.name,
        },
        'investment_project': {
            'id': str(interaction.investment_project.pk),
            'name': interaction.investment_project.name,
        },
        'created_on': interaction.created_on,
        'modified_on': interaction.modified_on,
    }


def test_interactions_to_es_documents():
    """Test converting 2 orders to Elasticsearch documents."""
    interactions = InteractionFactory.create_batch(2)

    result = Interaction.dbmodels_to_es_documents(interactions)

    assert {item['_id'] for item in result} == {str(item.pk) for item in interactions}