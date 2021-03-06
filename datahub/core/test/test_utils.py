from datetime import date
from enum import Enum
from uuid import UUID

import pytest

from datahub.core.constants import Constant
from datahub.core.test.support.models import MetadataModel
from datahub.core.utils import (
    get_financial_year,
    join_truthy_strings,
    load_constants_to_database,
    reverse_with_query_string,
    slice_iterable_into_chunks,
)


@pytest.mark.parametrize(
    'args,sep,res',
    (
        (('abc', 'def', 'ghi'), ',', 'abc,def,ghi'),
        (('abc', 'def'), ' ', 'abc def'),
        (('abc', ''), ' ', 'abc'),
        (('abc', None), ' ', 'abc'),
        ((None, ''), ' ', ''),
        ((), ' ', ''),
    ),
)
def test_join_truthy_strings(args, sep, res):
    """Tests joining turthy strings."""
    assert join_truthy_strings(*args, sep=sep) == res


def test_slice_iterable_into_chunks():
    """Test slice iterable into chunks."""
    size = 2
    iterable = range(5)
    chunks = list(slice_iterable_into_chunks(iterable, size))
    assert chunks == [[0, 1], [2, 3], [4]]


class _MetadataModelConstant(Enum):
    object_2 = Constant('Object 2a', 'c2ed6ff6-4a09-41ba-bda2-f4cdb2f96833')
    object_3 = Constant('Object 3b', '09afd6ef-deff-4b0f-9c5b-4816d3ddac09')
    object_4 = Constant('Object 4', 'c8ecf162-f14a-4ab2-a570-fb70a2435e6b')
    object_5 = Constant('Object 5', '6ea0e2a2-0b2b-408c-a621-aff49f58496e')


@pytest.mark.django_db
def test_load_constants_to_database():
    """
    Test loading constants to the database.

    Makes sure that new values are created, existing ones are updated and none are deleted.
    """
    initial_objects = [
        {
            'id': 'e2b77f5f-a3d9-4c48-9d40-5a5427ddcfc2',
            'name': 'Object 1',
        },
        {
            'id': 'c2ed6ff6-4a09-41ba-bda2-f4cdb2f96833',
            'name': 'Object 2',
        },
        {
            'id': '09afd6ef-deff-4b0f-9c5b-4816d3ddac09',
            'name': 'Object 3',
        },
        {
            'id': 'c8ecf162-f14a-4ab2-a570-fb70a2435e6b',
            'name': 'Object 4',
        },
    ]

    MetadataModel.objects.bulk_create([MetadataModel(**data) for data in initial_objects])

    load_constants_to_database(_MetadataModelConstant, MetadataModel)

    expected_items = {
        (UUID('e2b77f5f-a3d9-4c48-9d40-5a5427ddcfc2'), 'Object 1'),  # not deleted
        (UUID('c2ed6ff6-4a09-41ba-bda2-f4cdb2f96833'), 'Object 2a'),  # name updated
        (UUID('09afd6ef-deff-4b0f-9c5b-4816d3ddac09'), 'Object 3b'),  # name updated
        (UUID('c8ecf162-f14a-4ab2-a570-fb70a2435e6b'), 'Object 4'),  # unchanged
        (UUID('6ea0e2a2-0b2b-408c-a621-aff49f58496e'), 'Object 5'),  # created
    }
    actual_items = {(obj.id, obj.name) for obj in MetadataModel.objects.all()}
    assert actual_items == expected_items


@pytest.mark.parametrize(
    'query_args,expected_url',
    (
        ({}, '/test-disableable/?'),
        ({'123': 'abc'}, '/test-disableable/?123=abc'),
        ({'ab': ['1', '2']}, '/test-disableable/?ab=1&ab=2'),
    ),
)
@pytest.mark.urls('datahub.core.test.support.urls')
def test_reverse_with_query_string(query_args, expected_url):
    """Test reverse_with_query_string() for various query arguments."""
    assert reverse_with_query_string('test-disableable-collection', query_args) == expected_url


@pytest.mark.parametrize(
    'date_obj,expected_financial_year',
    (
        (None, None),
        (date(1980, 1, 1), 1979),
        (date(2018, 1, 1), 2017),
        (date(2019, 3, 1), 2018),
        (date(2019, 8, 1), 2019),
        (date(2025, 3, 1), 2024),
        (date(2025, 4, 1), 2025),
        (date(2025, 3, 31), 2024),
    ),
)
def test_get_financial_year(date_obj, expected_financial_year):
    """Test for get financial year"""
    assert get_financial_year(date_obj) == expected_financial_year
