from collections import defaultdict
from itertools import chain

from django.conf import settings
from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import Bool, MatchPhrase, MultiMatch, Query, Term

from datahub.search.apps import EXCLUDE_ALL, get_search_apps

MAX_RESULTS = 10000


class MatchNone(Query):
    """match_none query. This isn't defined in the Elasticsearch DSL library."""

    name = 'match_none'


def delete_document(model, document_id):
    """Deletes specified model's document."""
    doc = model.get(id=document_id, index=settings.ES_INDEX)
    doc.delete()


def get_basic_search_query(
        term,
        entities=None,
        permission_filters_by_entity=None,
        field_order=None,
        ignored_entities=(),
        offset=0,
        limit=100
):
    """Performs basic search looking for name and then SEARCH_FIELDS in entity.

    Also returns number of results in other entities.

    :param permission_filters_by_entity: List of pairs of entities and corresponding permission
                                         filters. Only entities in this list are included in the
                                         results, and those are entities are also filtered using
                                         the corresponding permission filters.
    """
    limit = _clip_limit(offset, limit)

    all_models = (search_app.es_model for search_app in get_search_apps())
    fields = set(chain.from_iterable(entity.SEARCH_FIELDS for entity in all_models))

    # Sort the fields so that this function is deterministic
    # and the same query is always generated with the same inputs
    fields = sorted(fields)

    query = _get_search_term_query(term, fields=fields)
    s = Search(index=settings.ES_INDEX).query(query)

    permission_query = _get_global_permission_query(permission_filters_by_entity)
    if permission_query:
        s = s.filter(permission_query)

    s = s.post_filter(
        Q('bool', should=[
            Q('term', _type=entity._doc_type.name) for entity in entities
            if entity._doc_type.name not in ignored_entities
        ])
    )

    s = _get_sort_query(s, field_order=field_order)
    s.aggs.bucket(
        'count_by_type', 'terms', field='_type'
    )

    return s[offset:offset + limit]


def get_search_by_entity_query(
        term=None,
        filter_data=None,
        composite_filters=None,
        permission_filters=None,
        entity=None,
        field_order=None,
        aggregations=None
):
    """
    Perform filtered search for given terms in given entity.

    :param permission_filters: dict of field names and values. These represent rules that records
                               must match one of to be included in the results.
    """
    query = [Q('term', _type=entity._doc_type.name)]
    if term != '':
        query.append(_get_search_term_query(term, fields=entity.SEARCH_FIELDS))

    filters, ranges = _split_date_range_fields(filter_data)

    # document must match all filters in the list (and)
    must_filter = _get_must_filter_query(filters, composite_filters, ranges)

    s = Search(index=settings.ES_INDEX).query('bool', must=query)

    permission_query = _get_entity_permission_query(permission_filters)
    if permission_query:
        s = s.filter(permission_query)

    s = _get_sort_query(s, field_order=field_order)

    s = s.post_filter('bool', must=must_filter)

    if aggregations:
        _apply_aggs_query(s, aggregations)

    return s


def limit_search_query(query, offset=0, limit=100):
    """Limits search query to the page defined by offset and limit."""
    limit = _clip_limit(offset, limit)
    return query[offset:offset + limit]


def _split_date_range_fields(fields):
    """Finds and format range fields."""
    filters = {}
    ranges = defaultdict(dict)

    for k, v in fields.items():
        if k.endswith('_before') or k.endswith('_after'):
            range_key = k[:k.rindex('_')]

            if k.endswith('_before'):
                ranges[range_key]['lte'] = fields[k]
            if k.endswith('_after'):
                ranges[range_key]['gte'] = fields[k]

            continue

        filters.update({k: v})

    return filters, ranges


def _clip_limit(offset, limit):
    return max(min(limit, MAX_RESULTS - offset), 0)


def _get_global_permission_query(permission_filters_by_entity):
    """
    Returns the filter query to use to enforce permissions in global search.

    See also:
        get_basic_search_query()

    """
    # None means that permissions aren't in effect for the current query. None is returned to
    # indicate that a filter query should not be applied.
    if permission_filters_by_entity is None:
        return None

    subqueries = list(_get_global_permission_subqueries(permission_filters_by_entity))
    # Check if there are any should subqueries (of which at least one should be matched).
    # If there are no conditions, return MatchNone() to ensure that all results are filtered out
    #  (as you can't meet at least one condition when there are no conditions).
    if len(subqueries) > 0:
        return Bool(
            should=subqueries,
        )
    return MatchNone()


def _get_global_permission_subqueries(permission_filters_by_entity):
    for entity, filter_args in permission_filters_by_entity.items():
        query = Term(_type=entity)
        entity_condition = _get_entity_permission_query(filter_args)

        if entity_condition is not None:
            query &= entity_condition

        yield query


def _get_entity_permission_query(permission_filters):
    """Gets the filter query to apply to enforce permissions for a model."""
    # None is used when there is no filtering to apply for the entity,
    # Returns None to indicate that no filter query should be used.
    if permission_filters is None:
        return None

    if permission_filters is EXCLUDE_ALL:
        return MatchNone()

    subqueries = [Term(**{field: value}) for field, value in permission_filters.items()]

    # Check if there are any should subqueries (of which at least one should be matched).
    # If there are no conditions, return MatchNone() to ensure that all results are filtered out
    #  (as you can't meet at least one condition when there are no conditions).
    if len(subqueries) > 0:
        return Bool(
            should=subqueries
        )
    return MatchNone()


def _get_search_term_query(term, fields=None):
    """Returns search term query."""
    if term == '':
        return Q('match_all')

    should_query = [
        # Promote exact name match
        MatchPhrase(name_keyword={'query': term, 'boost': 2}),
        # Exact match by id
        MatchPhrase(id=term),
        # Cross match fields
        MultiMatch(
            query=term,
            fields=fields,
            type='cross_fields',
            operator='and',
        )
    ]

    return Q('bool', should=should_query)


def _remap_sort_field(field):
    """Replaces fields to aliases suitable for sorting."""
    name_map = {
        'name': 'name_keyword',
    }
    return name_map.get(field, field)


def _get_sort_query(qs, field_order=None):
    """Attaches sort query."""
    if field_order is None:
        return qs.sort('_score', 'id')

    tokens = field_order.rsplit(':', maxsplit=1)
    order = tokens[1] if len(tokens) > 1 else 'asc'

    sort_params = {
        'order': order,
        'missing': '_first' if order == 'asc' else '_last'
    }

    # check if we sort by field in nested document (example: 'stage.name')
    if '.' in tokens[0]:
        # extract and add path to nested document (example: 'stage')
        sort_params['nested_path'] = tokens[0].split('.', 1)[0]

    qs = qs.sort({
        _remap_sort_field(tokens[0]): sort_params
    }, 'id')
    return qs


def _get_basic_field_query(field, value):
    """Gets field query depending on field suffix."""
    if any(field.endswith(suffix) for suffix in ('.id', '_keyword')):
        return Q('match_phrase', **{field: value})

    if field.endswith('_exists'):
        return _get_exists_query(field, value)

    field_query = {
        'query': value,
        'operator': 'and',
    }
    return Q('match', **{field: field_query})


def _get_field_query(field, value):
    """Gets field query."""
    if value is None:
        return _get_exists_query(
            f"{field.rsplit('.', maxsplit=1)[0]}_exists",
            False
        )

    query = _get_basic_field_query(field, value)
    if '.' not in field:
        return query

    return Q('nested', path=field.rsplit('.', maxsplit=1)[0], query=query)


def _get_exists_query(field, value):
    """Gets exists query."""
    real_field = field[:field.rindex('_')]

    kind = 'must' if value else 'must_not'
    query = {
        kind: Q('exists', field=real_field)
    }
    return Q('bool', **query)


def _apply_aggs_query(search, aggregates):
    """Applies aggregates query to the search."""
    for aggregate in aggregates:
        # skip range and "search" filters as we can't aggregate them
        if any(aggregate.endswith(x) for x in ('_before', '_after', '_trigram', '_exists')):
            continue

        search_aggs = search.aggs
        if '.' in aggregate:
            search_aggs = search_aggs.bucket(
                aggregate,
                'nested',
                path=aggregate.split('.', 1)[0]
            )

        search_aggs.bucket(aggregate, 'terms', field=aggregate)


def _get_filter_query(key, value):
    """Gets filter query."""
    if isinstance(value, list):
        # perform "or" query
        should_filter = [
            _get_field_query(key, v) for v in value
        ]
        return Q('bool', should=should_filter, minimum_should_match=1)

    return _get_field_query(key, value)


def _get_filter_queries(filters):
    """Gets filter queries."""
    return [
        _get_filter_query(k, v)
        for k, v in filters.items()
    ]


def _get_range_queries(ranges):
    """Gets range queries."""
    return [
        Q('range', **{k: v})
        for k, v in ranges.items()
    ]


def _get_composite_filters(composite_filters, value):
    """Gets queries for composite filters."""
    return [
        _get_filter_query(composite_filter, value)
        for composite_filter in composite_filters
    ]


def _get_nested_filters(field_name, nested_filters):
    """Gets queries for nested filters."""
    normalised_nested_filters = {
        f'{field_name}_{k}': v
        for k, v in nested_filters.items()
    }

    filters, ranges = _split_date_range_fields(normalised_nested_filters)
    should_filters = _get_filter_queries(filters)

    if ranges:
        should_filters.extend(_get_range_queries(ranges))
    return should_filters


def _get_must_filter_query(filters, composite_filters, ranges):
    """Gets "and" filter query."""
    if filters is None:
        filters = {}

    must_filter = []

    for k, v in filters.items():
        should_filters = None

        # get nested "or" filters
        if composite_filters and k in composite_filters:
            # process composite filters
            should_filters = _get_composite_filters(composite_filters[k], v)
        elif isinstance(v, dict):
            should_filters = _get_nested_filters(k, v)

        if should_filters:
            # builds "or" query for given list of fields
            must_filter.append(
                Q('bool', should=should_filters, minimum_should_match=1)
            )
        else:
            must_filter.append(
                _get_filter_query(k, v)
            )

    if ranges:
        must_filter.extend(_get_range_queries(ranges))

    return must_filter