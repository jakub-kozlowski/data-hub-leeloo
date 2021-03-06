# Data Hub Leeloo

[![image](https://circleci.com/gh/uktrade/data-hub-leeloo/tree/master.svg?style=svg)](https://circleci.com/gh/uktrade/data-hub-leeloo/tree/master)
[![image](https://codecov.io/gh/uktrade/data-hub-leeloo/branch/master/graph/badge.svg)](https://codecov.io/gh/uktrade/data-hub-leeloo)
[![image](https://codeclimate.com/github/uktrade/data-hub-leeloo/badges/gpa.svg)](https://codeclimate.com/github/uktrade/data-hub-leeloo)
[![Updates](https://pyup.io/repos/github/uktrade/data-hub-leeloo/shield.svg)](https://pyup.io/repos/github/uktrade/data-hub-leeloo/)

Leeloo provides an API into Data Hub for Data Hub clients. Using Leeloo you can search for entities and manage companies, contacts and interactions.

More guides can be found in the [docs](./docs/) folder.

## Installation with Docker

Leeloo uses Docker compose to setup and run all the necessary components. The docker-compose.yml file provided is meant to be used for running tests and development.

1.  Clone the repository:

    ```shell
    git clone https://github.com/uktrade/data-hub-leeloo
    cd data-hub-leeloo
    ```

2.  Create a `.env` file from `sample.env`

    ```shell
    cp sample.env .env
    ```

3.  Build and run the necessary containers for the required environment:

    ```shell
    docker-compose build
    ```

4.  Populate the database and initialise Elasticsearch:

    ```shell
    docker-compose run leeloo ./manage.py migrate
    docker-compose run leeloo ./manage.py init_es
    docker-compose run leeloo ./manage.py loadinitialmetadata
    docker-compose run leeloo ./manage.py createinitialrevisions
    ```

    * **NOTE:** 
      If you are using a linux system, these commands may hang on 
      waiting for the elasticsearch container to come up (`data-hub-leeloo_es_1`) - 
      it might be perpetually restarting.
      If the logs for that container mention something like 
      `max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]`,
      you will need to run the following on your host machine:

      ```shell
      sudo sysctl -w vm.max_map_count=262144
      ```

      and append/modify the `vm.max_map_count` setting in `/etc/sysctl.conf` (so 
      that this setting persists after restart):

      ```shell
      vm.max_map_count=262144
      ```

      For more information, [see the elasticsearch docs on vm.max_map_count](https://www.elastic.co/guide/en/elasticsearch/reference/6.6/vm-max-map-count.html).

5. Optionally, you can load some test data and update elasticsearch:

    ```shell
    docker-compose run leeloo ./manage.py loaddata /app/fixtures/test_data.yaml
    docker-compose run leeloo ./manage.py sync_es
    ```

6.  Create a superuser:

    ```shell
    docker-compose run leeloo ./manage.py createsuperuser
    ```

7.  Run the services:

    ```shell
    docker-compose up
    ```

8.  Optionally, you may want to run a local copy of the data hub frontend. 
    By default, you can run both leeloo and the frontend under one docker-compose
    project.  [See the instructions in the frontend readme to set it up](https://github.com/uktrade/data-hub-frontend/#setting-up-with-docker-compose).

## Native installation (without Docker)

Dependencies:

-   Python 3.7.x
-   PostgreSQL 10 (note: PostgreSQL 9.6 is used for the MI database)
-   redis 3.2
-   Elasticsearch 6.4

1.  Clone the repository:

    ```shell
    git clone https://github.com/uktrade/data-hub-leeloo
    cd data-hub-leeloo
    ```

2.  Install Python 3.7.
    
    [See this guide](https://docs.python-guide.org/starting/installation/) for detailed instructions for different platforms.
    
3.  Install system dependencies:
    
    On Ubuntu:
    
    ```shell
    sudo apt install build-essential libpq-dev python3.7-dev python3.7-venv
    ```
    
    On macOS:
    
    ```shell
    brew install libpq
    ```

4.  Create and activate the virtualenv:

    ```shell
    python3.7 -m venv env
    source env/bin/activate
    pip install -U pip
    ```

5.  Install the dependencies:

    ```shell
    pip install -r requirements.txt
    ```

6.  Create an `.env` settings file (it’s gitignored by default):

    ```shell
    cp config/settings/sample.env config/settings/.env
    ```

7.  Set `DOCKER_DEV=False` in `.env`
8.  Create the db. By default, the dev version uses postgres:

    ```shell
    psql -p5432
    create database datahub;
    ```

9. Make sure you have Elasticsearch running locally. If you don't, you can run one in Docker:

    ```shell
    docker run -p 9200:9200 -e "http.host=0.0.0.0" -e "transport.host=127.0.0.1" docker.elastic.co/elasticsearch/elasticsearch:6.3.2
    ```

10. Make sure you have redis running locally and that the REDIS_BASE_URL in your `.env` is up-to-date.

11. Populate the database and initialise Elasticsearch:

    ```shell
    ./manage.py migrate
    ./manage.py init_es

    ./manage.py loadinitialmetadata
    ./manage.py createinitialrevisions
    ```

12. Optionally, you can load some test data and update Elasticsearch:

    ```shell
    ./manage.py loaddata fixtures/test_data.yaml

    ./manage.py sync_es
    ```

13. Create a superuser:

    ```shell
    ./manage.py createsuperuser
    ```

14. Start the server:

    ```shell
    ./manage.py runserver
    ```

15. Start celery:

    ```shell
    celery worker -A config -l info -Q celery,long-running -B
    ```

    Note that in production the long-running queue is run in a separate worker with the 
    `-O fair --prefetch-multiplier 1` arguments for better fairness when long-running tasks 
    are running or pending execution.

## Local development

If using Docker, prefix these commands with `docker-compose run leeloo`.

To run the tests:

```shell
./tests.sh
```

To run the tests in parallel, pass `-n <number of processes>` to `./tests.sh`. For example, for four processes:


```shell
./tests.sh -n 4
```


To run the linter:

```shell
flake8
```

## Granting access to the front end

The [internal front end](https://github.com/uktrade/data-hub-frontend) uses single sign-on. You should configure Leeloo as follows to use with the front end:

* `SSO_ENABLED`: `True`
* `RESOURCE_SERVER_INTROSPECTION_URL`: URL of the [RFC 7662](https://tools.ietf.org/html/rfc7662) introspection endpoint (should be the same server the front end is using). This is provided by a [Staff SSO](https://github.com/uktrade/staff-sso) instance.
* `RESOURCE_SERVER_AUTH_TOKEN`: Access token for the introspection server.

The token should have the `data-hub:internal-front-end` scope. django-oauth-toolkit will create a user corresponding to the token if one does not already exist.

## Granting access to machine-to-machine clients

To give access to a machine-to-machine client that doesn't require user authentication:

1. Log into the [Django admin applications page](http://localhost:8000/admin/oauth2_provider/application/) and add a new OAuth application with these details:

    * Client type: Confidential
    * Authorization grant type: Client credentials

1. Define the required scopes for the app by adding a new record in the
[OAuth application scopes](http://localhost:8000/admin/oauth/oauthapplicationscope/)
page with these details:
    * Application: The application just created
    * Scope: The required scopes

The currently defined scopes can be found in [`datahub/oauth/scopes.py`](https://github.com/uktrade/data-hub-leeloo/tree/develop/datahub/oauth/scopes.py).

[Further information about the available grant types can be found in the OAuthLib docs](http://oauthlib.readthedocs.io/en/stable/oauth2/grants/grants.html).

## Deployment

Leeloo can run on any Heroku-style platform. Configuration is performed via the following environment variables:


| Variable name | Required | Description |
| ------------- | ------------- | ------------- |
| `ACTIVITY_STREAM_ACCESS_KEY_ID` | No | A non-secret access key ID, corresponding to `ACTIVITY_STREAM_SECRET_ACCESS_KEY`. The holder of the secret key can access the activity stream endpoint by Hawk authentication. |
| `ACTIVITY_STREAM_SECRET_ACCESS_KEY` | If `ACTIVITY_STREAM_ACCESS_KEY_ID` is set | A secret key, corresponding to `ACTIVITY_STREAM_ACCESS_KEY_ID`. The holder of this key can access the activity stream endpoint by Hawk authentication. |
| `ALLOWED_ADMIN_IPS` | No | IP addresses (comma-separated) that can access the admin site when RESTRICT_ADMIN is True. |
| `ALLOWED_ADMIN_IP_RANGES` | No | IP address ranges (comma-separated) that can access the admin site when RESTRICT_ADMIN is True. |
| `AV_V2_SERVICE_URL` | Yes | URL for ClamAV V2 service. If not configured, virus scanning will fail. |
| `AWS_ACCESS_KEY_ID` | No | Used as part of [boto3 auto-configuration](http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials). |
| `AWS_DEFAULT_REGION` | No | [Default region used by boto3.](http://boto3.readthedocs.io/en/latest/guide/configuration.html#environment-variable-configuration) |
| `AWS_SECRET_ACCESS_KEY` | No | Used as part of [boto3 auto-configuration](http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials). |
| `BULK_INSERT_BATCH_SIZE` | No | Used when loading Companies House records (default=5000). |
| `CELERY_TASK_ALWAYS_EAGER` | No | Can be set to True when running the app locally to run Celery tasks started from the web process synchronously. Not for use in production. |
| `DATA_SCIENCE_COMPANY_API_URL` | No | URL for the [DT07 reporting service](https://github.com/uktrade/dt07-reporting). |
| `DATA_SCIENCE_COMPANY_API_ID` | No | API ID for the DT07 reporting service. |
| `DATA_SCIENCE_COMPANY_API_KEY` | No | API key for the DT07 reporting service. |
| `DATA_SCIENCE_COMPANY_API_VERIFY_RESPONSES` | No | Whether to verify DT07 reporting service response signatures (default=True). |
| `DATABASE_CONN_MAX_AGE`  | No | [Maximum database connection age (in seconds).](https://docs.djangoproject.com/en/2.0/ref/databases/) |
| `DATABASE_URL`  | Yes | PostgreSQL server URL (with embedded credentials). |
| `DATAHUB_FRONTEND_BASE_URL`  | Yes | |
| `DEBUG`  | Yes | Whether Django's debug mode should be enabled. |
| `DJANGO_SECRET_KEY`  | Yes | |
| `DJANGO_SENTRY_DSN`  | Yes | |
| `DJANGO_SETTINGS_MODULE`  | Yes | |
| `DEFAULT_BUCKET`  | Yes | S3 bucket for object storage. |
| `ENABLE_DAILY_ES_SYNC` | No | Whether to enable the daily ES sync (default=False). |
| `ENABLE_SPI_REPORT_GENERATION` | No | Whether to enable daily SPI report (default=False). |
| `ES_INDEX_PREFIX`  | Yes | Prefix to use for indices and aliases |
| `ES_SEARCH_REQUEST_TIMEOUT` | No | Timeout (in seconds) for searches (default=20). |
| `ES_SEARCH_REQUEST_WARNING_THRESHOLD` | No | Threshold (in seconds) for emitting warnings about slow searches (default=10). |
| `ES_VERIFY_CERTS`  | No | |
| `ES5_URL`  | Required if not using GOV.UK PaaS-supplied Elasticsearch. | |
| `GUNICORN_ACCESSLOG`  | No | File to direct Gunicorn logs to (default=stdout). |
| `GUNICORN_ACCESS_LOG_FORMAT`  | No |  |
| `GUNICORN_ENABLE_ASYNC_PSYCOPG2` | No | Whether to enable asynchronous psycopg2 when the worker class is 'gevent' (default=True). |
| `GUNICORN_WORKER_CLASS`  | No | [Type of Gunicorn worker.](http://docs.gunicorn.org/en/stable/settings.html#worker-class) Uses async workers via gevent by default. |
| `GUNICORN_WORKER_CONNECTIONS`  | No | Maximum no. of connections for async workers (default=10). |
| `HAWK_RECEIVER_IP_WHITELIST` | No | IP addresses (comma-separated) that can access the Hawk-authenticated endpoints. |
| `INTERACTION_ADMIN_CSV_IMPORT_MAX_SIZE` | No | Maximum file size in bytes for interaction admin CSV uploads (default=2MB). |
| `INVESTMENT_DOCUMENT_AWS_ACCESS_KEY_ID` | No | Same use as AWS_ACCESS_KEY_ID, but for investment project documents. |
| `INVESTMENT_DOCUMENT_AWS_SECRET_ACCESS_KEY` | No | Same use as AWS_SECRET_ACCESS_KEY, but for investment project documents. |
| `INVESTMENT_DOCUMENT_AWS_REGION` | No | Same use as AWS_DEFAULT_REGION, but for investment project documents. |
| `INVESTMENT_DOCUMENT_BUCKET` | No | S3 bucket for investment project documents storage. |
| `ENABLE_MI_DASHBOARD_FEED` | No | Whether to enable daily MI dashboard feed (default=False). |
| `MARKET_ACCESS_ACCESS_KEY_ID` | No | A non-secret access key ID used by the Market Access service to access Hawk-authenticated public company endpoints. |
| `MARKET_ACCESS_SECRET_ACCESS_KEY` | If `MARKET_ACCESS_ACCESS_KEY_ID` is set | A secret key used by the Market Access service to access Hawk-authenticated public company endpoints. |
| `MI_DATABASE_URL`  | Yes | PostgreSQL server URL (with embedded credentials) for MI dashboard. |
| `MI_DATABASE_SSLROOTCERT` | No | base64 encoded root certificate for MI database connection. |
| `MI_DATABASE_SSLCERT` | No | base64 encoded client certificate for MI database connection. |
| `MI_DATABASE_SSLKEY` | No | base64 encoded client private key for MI database connection. |
| `MI_FDI_DASHBOARD_TASK_DURATION_WARNING_THRESHOLD` | No | Threshold (in seconds) for emitting warnings about long transfer duration (default=600). |
| `OMIS_NOTIFICATION_ADMIN_EMAIL`  | Yes | |
| `OMIS_NOTIFICATION_API_KEY`  | Yes | |
| `OMIS_NOTIFICATION_OVERRIDE_RECIPIENT_EMAIL`  | No | |
| `OMIS_PUBLIC_BASE_URL`  | Yes | |
| `REDIS_BASE_URL`  | No | redis base URL without the db |
| `REDIS_CACHE_DB`  | No | redis db for django cache (default 0) |
| `REDIS_CELERY_DB`  | No | redis db for celery (default 1) |
| `REPORT_AWS_ACCESS_KEY_ID` | No | Same use as AWS_ACCESS_KEY_ID, but for reports. |
| `REPORT_AWS_SECRET_ACCESS_KEY` | No | Same use as AWS_SECRET_ACCESS_KEY, but for reports. |
| `REPORT_AWS_REGION` | No | Same use as AWS_DEFAULT_REGION, but for reports. |
| `REPORT_BUCKET` | No | S3 bucket for report storage. |
| `RESOURCE_SERVER_INTROSPECTION_URL` | If SSO enabled | RFC 7662 token introspection URL used for signle sign-on |
| `RESOURCE_SERVER_AUTH_TOKEN` | If SSO enabled | Access token for RFC 7662 token introspection server |
| `RESTRICT_ADMIN` | No | Whether to restrict access to the admin site by IP address. |
| `SENTRY_ENVIRONMENT`  | Yes | Value for the environment tag in Sentry. |
| `SSO_ENABLED` | Yes | Whether single sign-on via RFC 7662 token introspection is enabled |
| `VCAP_SERVICES` | No | Set by GOV.UK PaaS when using their backing services. Contains connection details for Elasticsearch and Redis. |
| `WEB_CONCURRENCY` | No | Number of Gunicorn workers (set automatically by Heroku, otherwise defaults to 1). |


## Management commands

If using Docker, remember to run these commands inside your container by prefixing them with `docker-compose run leeloo`.

### Database


#### Apply migrations

```shell
./manage.py migrate
```

#### Create django-reversion initial revisions

If the database is freshly built or a new versioned model is added run:

```shell
./manage.py createinitialrevisions
```

#### Load initial metadata

These commands are generally only intended to be used on a blank database.

```shell
./manage.py loadinitialmetadata
```


### Elasticsearch

Create the Elasticsearch index (if it doesn't exist) and update the mapping:

```shell
./manage.py init_es
```

Resync all Elasticsearch records:

```shell
./manage.py sync_es
```

You can resync only specific models by using the `--model=` argument.

```shell
./manage.py sync_es --model=company --model=contact
```

For more details including all the available choices:

```shell
./manage.py sync_es --help
```

Migrate modified mappings:

```shell
./manage.py migrate_es
```

Elasticsearch mapping migrations are fairly complex – see [docs/Elasticsearch migrations.md](docs/Elasticsearch&#32;migrations.md) for more detail.


### Companies House

Update Companies House records:

```shell
./manage.py sync_ch
```

This downloads the latest data from Companies House, updates the Companies House table and triggers an Elasticsearch sync.

(Note that this does not remove any records from the Companies House table.)

## Dependencies

See [Managing dependencies](docs/Managing&#32;dependencies.md) for information about installing, 
adding and upgrading dependencies.

## Activity Stream

The `/v3/activity-stream/` endpoint is protected by two mechanisms:

* IP address whitelisting via the `X-Forwarded-For` header, with a comma separated list of whitelisted IPs in the environment variable `ACTIVITY_STREAM_IP_WHITELIST`.

* Hawk authentication via the `Authorization` header, with the credentials in the environment variables `ACTIVITY_STREAM_ACCESS_KEY_ID` and `ACTIVITY_STREAM_SECRET_ACCESS_KEY`.


### IP address whitelisting

The authentication blocks requests that do not have a whitelisted IP in the second-from-the-end IP in `X-Forwarded-For` header. In general, this cannot be trusted. However, in PaaS, this can be, and this is the only production environment. Ideally, this would be done at a lower level than HTTP, but this is not possible with the current architecture.

If making requests to this endpoint locally, you must manually add this header.


### Hawk authentication

In general, Hawk authentication hashing the HTTP payload and `Content-Type` header, and using a nonce, are both _optional_. Here, as with the Activity Stream endpoints in other DIT projects, both are _required_. `Content-Type` may be the empty string, and if there is no payload, then it should be treated as the empty string.
