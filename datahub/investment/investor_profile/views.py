from django_filters.rest_framework import DjangoFilterBackend

from datahub.core.viewsets import CoreViewSet
from datahub.investment.investor_profile.constants import ProfileType as ProfileTypeConstant
from datahub.investment.investor_profile.models import InvestorProfile
from datahub.investment.investor_profile.serializers import LargeCapitalInvestorProfileSerializer
from datahub.oauth.scopes import Scope


class LargeCapitalInvestorProfileViewSet(CoreViewSet):
    """Large capital investor profile view set."""

    required_scopes = (Scope.internal_front_end,)
    serializer_class = LargeCapitalInvestorProfileSerializer
    profile_type_id = ProfileTypeConstant.large.value.id
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('investor_company_id',)

    def get_queryset(self):
        """Returns only large capital investor profile queryset."""
        return InvestorProfile.objects.filter(profile_type_id=self.profile_type_id)
