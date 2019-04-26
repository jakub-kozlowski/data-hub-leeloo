from datetime import timedelta
from secrets import token_urlsafe

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import filesizeformat

from datahub.core.admin_csv_import import BaseCSVImportForm
from datahub.interaction.admin_csv_import.row_form import InteractionCSVRowForm


INTERACTION_FILE_CACHE_TIMEOUT_SECS = int(timedelta(minutes=15).total_seconds())
INTERACTION_FILE_CACHE_KEY_LENGTH = 32


class InteractionCSVForm(BaseCSVImportForm):
    """Form used for loading a CSV file to import interactions."""

    csv_file_field_label = 'Interaction list (CSV file)'
    csv_file_field_help_text = (
        f'Maximum file size: {filesizeformat(settings.INTERACTION_ADMIN_CSV_IMPORT_MAX_SIZE)}'
    )
    required_columns = InteractionCSVRowForm.get_required_field_names()

    def are_all_rows_valid(self):
        """Check if all of the rows in the CSV pass validation."""
        with self.open_file_as_dict_reader() as dict_reader:
            return all(InteractionCSVRowForm(row).is_valid() for row in dict_reader)

    def get_row_error_iterator(self):
        """Get a generator of CSVRowError instances."""
        with self.open_file_as_dict_reader() as dict_reader:
            yield from (
                error
                for index, row in enumerate(dict_reader)
                for error in InteractionCSVRowForm(row).get_flat_error_list_iterator(index)
            )

    def save_file_to_cache(self):
        """Generate a token and stores the file in the configured cache with a timeout."""
        csv_file = self.cleaned_data['csv_file']
        csv_file.seek(0)
        data = csv_file.read()

        token = _make_token()
        cache_key = _cache_key_for_token(token)
        cache.set(cache_key, data, timeout=INTERACTION_FILE_CACHE_TIMEOUT_SECS)
        return token

    @classmethod
    def from_token(cls, token):
        """
        Create a InteractionCSVForm instance using a token.

        Returns None if the token can't be found in the cache.
        """
        cache_key = _cache_key_for_token(token)
        data = cache.get(cache_key)
        if not data:
            return None

        return InteractionCSVForm(
            files={
                'csv_file': SimpleUploadedFile(f'{token}.csv', data),
            },
        )


def _make_token():
    return token_urlsafe(INTERACTION_FILE_CACHE_KEY_LENGTH)


def _cache_key_for_token(token):
    return f'interaction-csv-import:{token}'
