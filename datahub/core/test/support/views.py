from oauth2_provider.contrib.rest_framework.permissions import IsAuthenticatedOrTokenHasScope

from datahub.core.test.support.models import MultiAddressModel, MyDisableableModel, PermissionModel
from datahub.core.test.support.serializers import (
    MultiAddressModelSerializer,
    MyDisableableModelSerializer,
    PermissionModelSerializer,
)
from datahub.core.viewsets import CoreViewSet
from datahub.oauth.test.scopes import TestScope


class MyDisableableModelViewset(CoreViewSet):
    """MyDisableableModel view set."""

    permission_classes = (IsAuthenticatedOrTokenHasScope,)
    required_scopes = (TestScope.test_scope_1,)
    serializer_class = MyDisableableModelSerializer
    queryset = MyDisableableModel.objects.all()


class PermissionModelViewset(CoreViewSet):
    """PermissionModel view set."""

    serializer_class = PermissionModelSerializer
    required_scopes = ()
    queryset = PermissionModel.objects.all()


class MultiAddressModelViewset(CoreViewSet):
    """MultiAddressModel view set."""

    permission_classes = []
    serializer_class = MultiAddressModelSerializer
    queryset = MultiAddressModel.objects.all()
