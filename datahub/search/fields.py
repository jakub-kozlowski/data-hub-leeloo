from functools import partial

from elasticsearch_dsl import Keyword, Object, Text

from datahub.search.elasticsearch import lowercase_asciifolding_normalizer

# Keyword with normalisation to improve sorting (by keeping e, E, è, ê etc. together).
NormalizedKeyword = partial(
    Keyword,
    normalizer=lowercase_asciifolding_normalizer,
)
TrigramText = partial(Text, analyzer='trigram_analyzer')
EnglishText = partial(Text, analyzer='english_analyzer')


class TextWithKeyword(Text):
    """
    Text field with keyword sub-field.

    This definition is in line with the data type Elasticsearch uses for dynamically mapped text
    fields, and is intended to be used to explicitly define fields that were previously
    implicitly added to the ES mapping.
    """

    # The default value Elasticsearch uses for ignore_above when dynamically mapping text fields
    ES_DEFAULT_IGNORE_ABOVE = 256

    def __init__(self, *args, **kwargs):
        """Initialises the field, creating a keyword sub-field."""
        super().__init__(
            *args,
            **kwargs,
            fields={
                'keyword': Keyword(ignore_above=self.ES_DEFAULT_IGNORE_ABOVE),
            },
        )


def contact_or_adviser_field(include_dit_team=False):
    """Object field for advisers and contacts."""
    props = {
        'id': Keyword(),
        'first_name': NormalizedKeyword(),
        'last_name': NormalizedKeyword(),
        'name': Text(
            fields={
                'keyword': NormalizedKeyword(),
                'trigram': TrigramText(),
            },
        ),
    }

    if include_dit_team:
        props['dit_team'] = id_name_field()

    return Object(properties=props)


def id_name_field():
    """Object field with id and name sub-fields."""
    return Object(
        properties={
            'id': Keyword(),
            'name': NormalizedKeyword(),
        },
    )


def id_unindexed_name_field():
    """Object field with id and unindexed name sub-fields."""
    return Object(
        properties={
            'id': Keyword(),
            'name': Keyword(index=False),
        },
    )


def id_name_partial_field():
    """Object field with id and name sub-fields, and with partial matching on name."""
    return Object(
        properties={
            'id': Keyword(),
            'name': Text(
                fields={
                    'keyword': NormalizedKeyword(),
                    'trigram': TrigramText(),
                },
            ),
        },
    )


def company_field():
    """Company field with id, name, trading_names and trigrams."""
    return Object(
        properties={
            'id': Keyword(),
            'name': Text(
                fields={
                    'trigram': TrigramText(),
                    'keyword': NormalizedKeyword(),
                },
            ),
            'trading_names': Text(
                fields={
                    'trigram': TrigramText(),
                },
            ),
        },
    )


def country_field():
    """Country field with id, name and trigram."""
    return Object(
        properties={
            'id': Keyword(),
            'name': Text(
                fields={
                    'trigram': TrigramText(),
                },
            ),
        },
    )


def address_field(index_country=True):
    """Address field as nested object."""
    if index_country:
        nested_country_field = country_field()
    else:
        nested_country_field = Object(
            properties={
                'id': Keyword(index=False),
                'name': Text(index=False),
            },
        )

    return Object(
        properties={
            'line_1': Text(index=False),
            'line_2': Text(index=False),
            'town': Text(index=False),
            'county': Text(index=False),
            'postcode': Text(
                fields={
                    'trigram': TrigramText(),
                },
            ),
            'country': nested_country_field,
        },
    )


def ch_company_field():
    """Object field with id and company_number sub-fields."""
    return Object(properties={
        'id': Keyword(),
        'company_number': NormalizedKeyword(),
    })


def sector_field():
    """Sector field."""
    ancestors = Object(
        properties={
            'id': Keyword(),
        },
    )

    return Object(
        properties={
            'id': Keyword(),
            'name': NormalizedKeyword(),
            'ancestors': ancestors,
        },
    )


def object_field(*fields):
    """This is a mapping that reflects how Elasticsearch auto-creates mappings for objects."""
    return Object(
        properties={field: TextWithKeyword() for field in fields},
    )
