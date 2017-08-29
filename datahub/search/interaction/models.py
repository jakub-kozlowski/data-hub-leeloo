from django.conf import settings
from elasticsearch_dsl import Date, DocType, String

from datahub.search import dict_utils, dsl_utils
from datahub.search.models import MapDBModelToDict


class Interaction(DocType, MapDBModelToDict):
    """Elasticsearch representation of Interaction model."""

    id = dsl_utils.KeywordString()
    date = Date()
    company = dsl_utils.id_name_partial_mapping('company')
    contact = dsl_utils.contact_mapping('contact')
    service = dsl_utils.id_name_mapping()
    subject = String()
    dit_adviser = dsl_utils.contact_mapping('dit_adviser')
    notes = String()
    dit_team = dsl_utils.id_name_mapping()
    interaction_type = dsl_utils.id_name_mapping()
    investment_project = dsl_utils.id_name_mapping()
    created_on = Date()
    modified_on = Date()

    MAPPINGS = {
        'id': str,
        'company': dict_utils.id_name_dict,
        'contact': dict_utils.contact_or_adviser_dict,
        'service': dict_utils.id_name_dict,
        'dit_adviser': dict_utils.contact_or_adviser_dict,
        'dit_team': dict_utils.id_name_dict,
        'interaction_type': dict_utils.id_name_dict,
        'investment_project': dict_utils.id_name_dict,
    }

    COMPUTED_MAPPINGS = {}

    IGNORED_FIELDS = (
        'created_by',
        'modified_by',
    )

    SEARCH_FIELDS = [
        'subject',
        'company.name',
        'contact.name',
        'dit_team.name',
        'notes'
    ]

    class Meta:
        """Default document meta data."""

        index = settings.ES_INDEX
        doc_type = 'interaction'