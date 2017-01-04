from unittest import mock
from unittest.mock import Mock

import pytest
from django.urls import reverse
from elasticsearch import ElasticsearchException
from rest_framework import status

pytestmark = pytest.mark.django_db


@mock.patch('datahub.ping.services.KorbenConnector')
def test_all_good(mock_korben_connector, client):
    """Test all good."""
    mock_korben_connector().ping.return_value = Mock(status_code=status.HTTP_200_OK)
    url = reverse('ping')
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert '<status>OK</status>' in str(response.content)
    assert response._headers['content-type'] == ('Content-Type', 'text/xml')


@mock.patch('datahub.ping.services.KorbenConnector')
def test_korben_not_returning_200(mock_korben_connector, client):
    """Test Korben broken."""
    korben_error_content = """foobar"""
    mock_korben_connector().ping.return_value = Mock(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=korben_error_content
    )
    url = reverse('ping')
    response = client.get(url)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert '<status>FALSE</status>' in str(response.content)
    assert '<!--foobar-->' in str(response.content)
    assert response._headers['content-type'] == ('Content-Type', 'text/xml')


@mock.patch('datahub.ping.services.ESConnector')
def test_elasticsearch_error(mock_es_connector, client):
    """Test ES broken."""
    mock_es_connector().ping.return_value = Mock(side_effect=ElasticsearchException('foo'))
    url = reverse('ping')
    response = client.get(url)
    assert '<status>FALSE</status>' in str(response.content)
    assert '<!--Unknown error-->' in str(response.content)
    assert response._headers['content-type'] == ('Content-Type', 'text/xml')