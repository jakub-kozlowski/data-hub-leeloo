from django.conf import settings
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator

from datahub.core.admin import max_upload_size
from datahub.feature_flag.utils import feature_flagged_view
from datahub.interaction.admin_csv_import.file_form import InteractionCSVForm

INTERACTION_IMPORTER_FEATURE_FLAG_NAME = 'admin-interaction-csv-importer'


class InteractionCSVImportAdmin:
    """
    Views related to importing interactions from a CSV file.

    The implementation is not yet complete; hence, views are behind a feature flag.
    """

    def __init__(self, model_admin):
        """Initialises the instance with a reference to an InteractionAdmin instance."""
        self.model_admin = model_admin

    def get_urls(self):
        """Gets a list of routes that should be registered."""
        model_meta = self.model_admin.model._meta
        admin_site = self.model_admin.admin_site

        return [
            path(
                'import',
                admin_site.admin_view(self.select_file),
                name=f'{model_meta.app_label}_{model_meta.model_name}_import',
            ),
        ]

    @feature_flagged_view(INTERACTION_IMPORTER_FEATURE_FLAG_NAME)
    @method_decorator(max_upload_size(settings.INTERACTION_ADMIN_CSV_IMPORT_MAX_SIZE))
    def select_file(self, request, *args, **kwargs):
        """View containing a form to select a CSV file to import."""
        if not self.model_admin.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return self._select_file_form_response(request, InteractionCSVForm())

        form = InteractionCSVForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._select_file_form_response(request, form)

        # Next page not yet implemented; redirect to the change list for now
        changelist_route_name = admin_urlname(self.model_admin.model._meta, 'changelist')
        changelist_url = reverse(changelist_route_name)
        return HttpResponseRedirect(changelist_url)

    def _select_file_form_response(self, request, form):
        template_name = 'admin/interaction/interaction/import_select_file.html'
        title = 'Import interactions'

        context = {
            **self.model_admin.admin_site.each_context(request),
            'opts': self.model_admin.model._meta,
            'title': title,
            'form': form,
        }
        return TemplateResponse(request, template_name, context)
