"""Company and related resources view sets."""
import re
from functools import reduce
from operator import or_

from django.db.models import Case, IntegerField, Prefetch, Q, When
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from datahub.company.models import (
    Advisor,
    CompaniesHouseCompany,
    Company,
    Contact,
)
from datahub.company.queryset import get_contact_queryset
from datahub.company.serializers import (
    AdviserSerializer,
    CompaniesHouseCompanySerializer,
    CompanySerializer,
    ContactSerializer,
    OneListCoreTeamMemberSerializer,
)
from datahub.company.validators import NotATransferredCompanyValidator
from datahub.core.audit import AuditViewSet
from datahub.core.mixins import ArchivableViewSetMixin
from datahub.core.viewsets import CoreViewSet
from datahub.investment.queryset import get_slim_investment_project_queryset
from datahub.oauth.scopes import Scope


class CompanyViewSet(ArchivableViewSetMixin, CoreViewSet):
    """Company view set V3."""

    required_scopes = (Scope.internal_front_end,)
    serializer_class = CompanySerializer
    unarchive_validators = (NotATransferredCompanyValidator(),)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_fields = ('global_headquarters_id',)
    ordering_fields = ('name', 'created_on')
    queryset = Company.objects.select_related(
        'address_country',
        'archived_by',
        'business_type',
        'employee_range',
        'export_experience_category',
        'global_headquarters__one_list_account_owner__dit_team__country',
        'global_headquarters__one_list_account_owner__dit_team__uk_region',
        'global_headquarters__one_list_account_owner__dit_team',
        'global_headquarters__one_list_account_owner',
        'global_headquarters__one_list_tier',
        'global_headquarters',
        'headquarter_type',
        'one_list_account_owner__dit_team__country',
        'one_list_account_owner__dit_team__uk_region',
        'one_list_account_owner__dit_team',
        'one_list_account_owner',
        'one_list_tier',
        'registered_address_country',
        'trading_address_country',
        'transferred_to',
        'turnover_range',
        'uk_region',
    ).prefetch_related(
        Prefetch('contacts', queryset=get_contact_queryset()),
        Prefetch('investor_investment_projects', queryset=get_slim_investment_project_queryset()),
        'export_to_countries',
        'future_interest_countries',
        'sector__parent__parent',
        'sector__parent',
        'sector',
    )


class OneListGroupCoreTeamViewSet(CoreViewSet):
    """
    Views for the One List Core Team of the group a company is part of.
    A Core Team is usually assigned to the Global Headquarters and is shared among all
    members of the group.

    The permissions to access this resource are inherited from the company resource.

    E.g. user only needs `view_company` permission to GET this collection and
    onelistcoreteammember permissions are ignored for now.
    """

    required_scopes = (Scope.internal_front_end,)
    queryset = Company.objects
    serializer_class = OneListCoreTeamMemberSerializer

    def list(self, request, *args, **kwargs):
        """Lists Core Team members."""
        company = self.get_object()
        core_team = company.get_one_list_group_core_team()

        serializer = self.get_serializer(core_team, many=True)
        return Response(serializer.data)


class CompanyAuditViewSet(AuditViewSet):
    """Company audit views."""

    required_scopes = (Scope.internal_front_end,)
    queryset = Company.objects.all()


class CompaniesHouseCompanyViewSet(
        mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """Companies House company read-only GET only views."""

    required_scopes = (Scope.internal_front_end,)
    serializer_class = CompaniesHouseCompanySerializer
    queryset = CompaniesHouseCompany.objects.select_related('registered_address_country').all()
    lookup_field = 'company_number'


class ContactViewSet(ArchivableViewSetMixin, CoreViewSet):
    """Contact ViewSet v3."""

    required_scopes = (Scope.internal_front_end,)
    serializer_class = ContactSerializer
    queryset = get_contact_queryset()
    filter_backends = (
        DjangoFilterBackend, OrderingFilter,
    )
    filterset_fields = ['company_id']
    ordering = ('-created_on',)

    def get_additional_data(self, create):
        """Set adviser to the user on model instance creation."""
        data = super().get_additional_data(create)
        if create:
            data['adviser'] = self.request.user
        return data


class ContactAuditViewSet(AuditViewSet):
    """Contact audit views."""

    required_scopes = (Scope.internal_front_end,)
    queryset = Contact.objects.all()


class AdviserFilter(FilterSet):
    """Adviser filter."""

    autocomplete_fields = (
        'first_name',
        'last_name',
        'dit_team__name',
    )
    autocomplete = CharFilter(method='filter_autocomplete')

    def filter_autocomplete(self, queryset, field_name, value):
        """
        Performs an autocomplete search for advisers.

        The input string is split into tokens. Each token must match a prefix of a word in any of
        the following fields (case-insensitive):

        - first_name
        - last_name
        - dit_team.name

        A word is defined as an unbroken sequence of letters, numbers and/or underscores.

        Results are automatically ordered as follows:

        - advisers with a match on first_name are returned first, last_name second and
        dit_team.name last
        - within each group, results are sorted by first_name, last_name, dit_team.name and
        finally pk (so that the results are deterministic if the other ordering fields are
        identical).

        Scoring is not used is keep the order of results predictable when only a few characters
        are entered.

        Note that this ordering won't be used if an explicit sortby query parameter is provided
        in the request.
        """
        escaped_tokens = [re.escape(token) for token in value.split()]

        if not escaped_tokens:
            return queryset

        q_objects_for_filtering = (
            self._autocomplete_filtering_q(self.autocomplete_fields, escaped_token)
            for escaped_token in escaped_tokens
        )
        cases_for_ordering = (
            When(self._autocomplete_ordering_q(field, escaped_tokens), then=index)
            for index, field in enumerate(self.autocomplete_fields)
        )
        return queryset.annotate(
            _autocomplete_ordering=Case(*cases_for_ordering, output_field=IntegerField()),
        ).filter(
            *q_objects_for_filtering,
        ).order_by(
            '_autocomplete_ordering',
            *self.autocomplete_fields,
            'pk',
        )

    @classmethod
    def _autocomplete_ordering_q(cls, field, escaped_tokens):
        return reduce(
            or_,
            (
                Q(cls._autocomplete_q(field, escaped_token))
                for escaped_token in escaped_tokens
            ),
        )

    @classmethod
    def _autocomplete_filtering_q(cls, fields, escaped_token):
        return reduce(
            or_,
            (
                Q(cls._autocomplete_q(field, escaped_token))
                for field in fields
            ),
        )

    @staticmethod
    def _autocomplete_q(field, escaped_token):
        r"""
        Generates a Q object that performs a case-insensitive match of a token with prefixes
        of any of the words in a field.

        \m means a word boundary (a word is defined as a consecutive sequence of letters,
        numbers and underscores).
        """
        q_kwargs = {
            f'{field}__iregex': rf'\m{escaped_token}',
        }
        return Q(**q_kwargs)

    class Meta:
        model = Advisor
        # TODO: Remove unused options following the deprecation period.
        fields = {
            'first_name': ('exact', 'icontains'),
            'last_name': ('exact', 'icontains'),
            'email': ('exact', 'icontains'),
            'is_active': ('exact',),
        }


class AdviserOrderingFilter(OrderingFilter):
    """Filter back end for the adviser view."""

    def get_default_ordering(self, view):
        """
        Gets the default ordering for the view.

        If a value has been provided in the autocomplete query parameter, no default
        ordering is used as the autocomplete filter orders results automatically.

        Otherwise, the default ordering set on the view (in the ordering attribute)
        is used.
        """
        if view.request.query_params.get('autocomplete'):
            return None

        return super().get_default_ordering(view)


class AdviserReadOnlyViewSetV1(
        mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """Adviser GET only views."""

    required_scopes = (Scope.internal_front_end,)
    serializer_class = AdviserSerializer
    queryset = Advisor.objects.select_related(
        'dit_team',
    )
    filter_backends = (
        DjangoFilterBackend,
        AdviserOrderingFilter,
    )
    filterset_class = AdviserFilter
    ordering_fields = ('first_name', 'last_name', 'dit_team__name')
    ordering = ('first_name', 'last_name', 'dit_team__name')
