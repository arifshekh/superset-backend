# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os
import sys

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache

logger = logging.getLogger()

# Security configurations
# WTF_CSRF_ENABLED = False
ENABLE_PROXY_FIX = True
ENABLE_CORS = True
SESSION_COOKIE_SAMESITE = None
TALISMAN_ENABLED = False
PUBLIC_ROLE_LIKE_GAMMA = True
GUEST_ROLE_NAME = "Gamma"
PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_TIMEOUT', 3600))

# HTTP Headers
HTTP_HEADERS = {
    'X-Frame-Options': 'ALLOWALL'
}

# CORS Options
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['*']
}

# Get database dialect (used for both main and examples DB)
# Check DB_DIALECT first (higher priority for overrides)
DATABASE_DIALECT = (
    os.getenv("DB_DIALECT") or os.getenv("DATABASE_DIALECT") or "postgresql+psycopg2"
)

# Check for SUPERSET__SQLALCHEMY_DATABASE_URI first (highest priority)
SUPERSET_DB_URI = os.getenv("SUPERSET__SQLALCHEMY_DATABASE_URI")
if SUPERSET_DB_URI:
    SQLALCHEMY_DATABASE_URI = SUPERSET_DB_URI
    logger.info(
        f"Using SUPERSET__SQLALCHEMY_DATABASE_URI from environment: {SUPERSET_DB_URI[:50]}..."
    )
else:
    # Support both DB_* and DATABASE_* naming conventions
    # Check DB_* first (higher priority for overrides in .env-local)
    DATABASE_USER = os.getenv("DB_USER") or os.getenv("DATABASE_USER")
    DATABASE_PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("DATABASE_PASSWORD")
    DATABASE_HOST = os.getenv("DB_HOST") or os.getenv("DATABASE_HOST")
    DATABASE_PORT = os.getenv("DB_PORT") or os.getenv("DATABASE_PORT")
    DATABASE_DB = os.getenv("DB_NAME") or os.getenv("DATABASE_DB")

    # Build SQLAlchemy connection string only if all required variables are present
    # If variables are missing, SQLALCHEMY_DATABASE_URI won't be set, allowing
    # the default from superset/config.py to be used
    if (
        DATABASE_USER
        and DATABASE_PASSWORD
        and DATABASE_HOST
        and DATABASE_PORT
        and DATABASE_DB
    ):
        SQLALCHEMY_DATABASE_URI = (
            f"{DATABASE_DIALECT}://"
            f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
            f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
        )
        logger.info(
            f"Built SQLALCHEMY_DATABASE_URI from environment variables: {DATABASE_DIALECT}://{DATABASE_USER}:***@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
        )
    else:
        logger.warning(
            "Database environment variables not fully set, will use default from superset/config.py"
        )

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# Build examples URI if all variables are present
if (
    EXAMPLES_USER
    and EXAMPLES_PASSWORD
    and EXAMPLES_HOST
    and EXAMPLES_PORT
    and EXAMPLES_DB
):
    SQLALCHEMY_EXAMPLES_URI = (
        f"{DATABASE_DIALECT}://"
        f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
        f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
    )
elif "SQLALCHEMY_DATABASE_URI" in locals():
    # Fallback to main database URI if examples not configured and main URI is set
    SQLALCHEMY_EXAMPLES_URI = SQLALCHEMY_DATABASE_URI
# If SQLALCHEMY_DATABASE_URI is not set, SQLALCHEMY_EXAMPLES_URI will also use default from superset/config.py

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# Disable ClickHouse database connections (driver not installed)
# This prevents ClickHouse from appearing in the database connection dropdown
# and helps avoid errors when processing datasources that reference ClickHouse
DBS_AVAILABLE_DENYLIST = {
    "clickhouse": {""},  # Disable all ClickHouse drivers
    "clickhousedb": {""},  # Disable ClickHouse Connect driver as well
}

# Add error handling for ClickHouse databases with missing drivers
# This will be applied after Superset is fully loaded (see end of file)

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "EMBEDDED_SUPERSET": True,  # Enable Embed dashboard option
}
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = "http://superset:8088/"  # When using docker compose baseurl should be http://superset_app:8088/  # noqa: E501
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL
SQLLAB_CTAS_NO_LIMIT = True

log_level_text = os.getenv("SUPERSET_LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level_text.upper(), logging.INFO)

if os.getenv("CYPRESS_CONFIG") == "true":
    # When running the service as a cypress backend, we need to import the config
    # located @ tests/integration_tests/superset_test_config.py
    base_dir = os.path.dirname(__file__)
    module_folder = os.path.abspath(
        os.path.join(base_dir, "../../tests/integration_tests/")
    )
    sys.path.insert(0, module_folder)
    from superset_test_config import *  # noqa

    sys.path.pop(0)

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at [{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")

# Add error handling for ClickHouse databases with missing drivers
# This monkey-patches the Database.get_dialect() method to gracefully handle
# missing ClickHouse drivers without deleting database connections
# We do this after importing superset_config_docker to ensure Superset is loaded
from sqlalchemy.exc import NoSuchModuleError


def patch_database_get_dialect():
    """Patch Database.get_dialect() to handle missing ClickHouse driver gracefully"""
    try:
        # Import here to ensure Superset models are loaded
        from superset.models.core import Database
        from sqlalchemy.dialects import postgresql

        original_get_dialect = Database.get_dialect

        def get_dialect_with_clickhouse_handling(self):
            """Wrapper that handles missing ClickHouse driver gracefully"""
            try:
                return original_get_dialect(self)
            except NoSuchModuleError as e:
                # Check if it's a ClickHouse-related error
                error_msg = str(e).lower()
                if "clickhouse" in error_msg:
                    logger.warning(
                        f"Skipping ClickHouse database '{getattr(self, 'database_name', 'unknown')}' - driver not installed. "
                        f"Install clickhouse-connect to use this database."
                    )
                    # Return a dummy dialect to prevent crashes
                    return postgresql.dialect()
                raise
            except Exception as e:
                # Also catch any other errors related to ClickHouse
                error_msg = str(e).lower()
                if "clickhouse" in error_msg:
                    logger.warning(
                        f"Error loading ClickHouse database '{getattr(self, 'database_name', 'unknown')}': {e}. "
                        f"Skipping to prevent crash."
                    )
                    return postgresql.dialect()
                raise

        Database.get_dialect = get_dialect_with_clickhouse_handling
        logger.info(
            "Patched Database.get_dialect() to handle missing ClickHouse driver"
        )
    except Exception as e:
        logger.warning(f"Could not patch Database.get_dialect(): {e}")


def patch_jinja_template_processor():
    """Patch jinja_context template processor to handle missing ClickHouse driver"""
    try:
        from superset.jinja_context import (
            BaseTemplateProcessor,
            JinjaTemplateProcessor,
        )
        from sqlalchemy.dialects import postgresql

        # Store original methods
        original_base_init = BaseTemplateProcessor.__init__
        original_jinja_set_context = JinjaTemplateProcessor.set_context

        def safe_get_dialect(database):
            """Safely get dialect, handling ClickHouse errors"""
            try:
                return database.get_dialect()
            except (NoSuchModuleError, Exception) as e:
                error_msg = str(e).lower()
                if "clickhouse" in error_msg:
                    logger.warning(
                        "Skipping ClickHouse database '%s' in template processor - "
                        "driver not installed.",
                        getattr(database, "database_name", "unknown"),
                    )
                    return postgresql.dialect()
                raise

        def patched_base_init(self, database, *args, **kwargs):
            """Patched BaseTemplateProcessor.__init__ with safe dialect handling"""
            # Call original init but catch error on where_in filter
            try:
                original_base_init(self, database, *args, **kwargs)
            except (NoSuchModuleError, Exception) as e:
                error_msg = str(e).lower()
                if "clickhouse" in error_msg:
                    # Initialize manually with safe dialect
                    self._database = database
                    self._query = kwargs.get("query")
                    self._schema = None
                    if (
                        self._query
                        and hasattr(self._query, "schema")
                        and self._query.schema
                    ):
                        self._schema = self._query.schema
                    elif kwargs.get("table") and hasattr(kwargs.get("table"), "schema"):
                        self._schema = kwargs.get("table").schema
                    self._table = kwargs.get("table")
                    self._extra_cache_keys = kwargs.get("extra_cache_keys")
                    self._applied_filters = kwargs.get("applied_filters")
                    self._removed_filters = kwargs.get("removed_filters")
                    self._context = {}
                    from jinja2.sandbox import SandboxedEnvironment
                    from jinja2.runtime import DebugUndefined

                    self.env = SandboxedEnvironment(undefined=DebugUndefined)
                    # Use safe dialect for where_in filter
                    from superset.jinja_context import WhereInMacro

                    self.env.filters["where_in"] = WhereInMacro(postgresql.dialect())
                    # Call parent set_context
                    filtered_kwargs = {
                        k: v
                        for k, v in kwargs.items()
                        if k
                        not in [
                            "query",
                            "table",
                            "extra_cache_keys",
                            "applied_filters",
                            "removed_filters",
                        ]
                    }
                    super(BaseTemplateProcessor, self).set_context(**filtered_kwargs)
                else:
                    raise

        def patched_jinja_set_context(self, *args, **kwargs):
            """Patched JinjaTemplateProcessor.set_context with safe dialect handling"""
            try:
                return original_jinja_set_context(self, *args, **kwargs)
            except (NoSuchModuleError, Exception) as e:
                error_msg = str(e).lower()
                if "clickhouse" in error_msg:
                    logger.warning(
                        "Skipping ClickHouse database in JinjaTemplateProcessor: %s",
                        e,
                    )
                    # Call parent set_context only (minimal functionality)
                    super(JinjaTemplateProcessor, self).set_context(**kwargs)
                else:
                    raise

        BaseTemplateProcessor.__init__ = patched_base_init
        JinjaTemplateProcessor.set_context = patched_jinja_set_context
        logger.info(
            "Patched jinja_context template processors to handle "
            "missing ClickHouse driver"
        )
    except Exception as e:
        logger.warning(f"Could not patch jinja_context template processors: {e}")


# Apply both patches after Superset is loaded
try:
    patch_database_get_dialect()
    patch_jinja_template_processor()
except Exception as e:
    logger.warning(f"Could not apply ClickHouse error handling patches: {e}")
