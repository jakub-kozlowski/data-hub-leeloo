import environ

environ.Env.read_env()  # reads the .env file
env = environ.Env()

from config.settings.common import *

# The automatic connection configuration is disabled during tests because the connection is set up
# using different environment variables in the _es_client pytest fixture
SEARCH_CONFIGURE_CONNECTION_ON_READY = False
# We need to prevent Django from connecting signal receivers when the search app is initialised
# to stop them from firing during non-search tests
SEARCH_CONNECT_SIGNAL_RECEIVERS_ON_READY = False
INSTALLED_APPS += [
    'datahub.core.test.support',
    'datahub.documents.test.my_entity_document',
    'datahub.search.test.search_support',
]

SEARCH_APPS += [
    'datahub.search.test.search_support.simplemodel.SimpleModelSearchApp',
    'datahub.search.test.search_support.relatedmodel.RelatedModelSearchApp',
]

# The index is set dynamically in datahub/search/conftest.py, so that tests can be parallelised.
ES_INDEX_PREFIX = None
ES_INDEX_SETTINGS = {
    **ES_INDEX_SETTINGS,
    'number_of_shards': 1,
    'number_of_replicas': 0,
}
DOCUMENT_BUCKET = 'test-bucket'
AV_V2_SERVICE_URL = 'http://av-service/'

DATA_SCIENCE_COMPANY_API_URL = 'http://company-timeline/'
DATA_SCIENCE_COMPANY_API_ID = 'company-timeline-api-id'
DATA_SCIENCE_COMPANY_API_KEY = 'company-timeline-api-key'

OMIS_GENERIC_CONTACT_EMAIL = 'omis@example.com'
OMIS_NOTIFICATION_OVERRIDE_RECIPIENT_EMAIL = ''
OMIS_NOTIFICATION_ADMIN_EMAIL = 'fake-omis-admin@digital.trade.gov.uk'
OMIS_NOTIFICATION_API_KEY = ''

GOVUK_PAY_URL = 'https://payments.example.com/'

INTERACTION_ADMIN_CSV_IMPORT_MAX_SIZE = 1024

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

CELERY_TASK_ALWAYS_EAGER = True

# Stop WhiteNoise emitting warnings when running tests without running collectstatic first
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

HAWK_RECEIVER_IP_WHITELIST = ['1.2.3.4']

HAWK_RECEIVER_CREDENTIALS = {
    'some-id': {
        'key': 'some-secret',
        'scope': HawkScope.activity_stream,
    },
    'test-id-with-scope': {
        'key': 'test-key-with-scope',
        'scope': next(iter(HawkScope.__members__.values())),
    },
    'test-id-without-scope': {
        'key': 'test-key-without-scope',
        'scope': object(),
    },
    'public-company-id': {
        'key': 'public-company-key',
        'scope': HawkScope.public_company,
    },
}

DOCUMENT_BUCKETS = {
    'default': {
        'bucket': 'foo',
        'aws_access_key_id': 'bar',
        'aws_secret_access_key': 'baz',
        'aws_region': 'eu-west-2',
    },
    'investment': {
        'bucket': 'foo',
        'aws_access_key_id': 'bar',
        'aws_secret_access_key': 'baz',
        'aws_region': 'eu-west-2',
    },
    'report': {
        'bucket': 'foo',
        'aws_access_key_id': 'bar',
        'aws_secret_access_key': 'baz',
        'aws_region': 'eu-west-2',
    }
}
