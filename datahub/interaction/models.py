import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from model_utils import Choices

from datahub.core import reversion
from datahub.core.models import (
    ArchivableModel,
    BaseConstantModel,
    BaseModel,
    BaseOrderedConstantModel,
)
from datahub.core.utils import get_front_end_url, StrEnum

MAX_LENGTH = settings.CHAR_FIELD_MAX_LENGTH


class InteractionPermission(StrEnum):
    """
    Permission codename constants.

    (Defined here rather than in permissions to avoid an import of that module.)


    The following codenames mean that the user can view, change, add or delete any type of
    interaction:

    view_all_interaction
    change_all_interaction
    add_all_interaction
    delete_interaction


    The following codenames mean that the user can only view, change and add interactions for
    investment projects that they are associated with:

    view_associated_investmentproject_interaction
    change_associated_investmentproject_interaction
    add_associated_investmentproject_interaction

    They cannot view, change or add interactions that do not relate to an investment project.

    An associated project has the same meaning that it does in investment projects (that is a
    project that was created by an adviser in the same team, or an adviser in the same team has
    been linked to the project).


    Note that permissions on other models are independent of permissions on interactions. Also
    note that if both *_all_* and *_associated_investmentproject_* permissions are assigned to the
    same user,  the *_all_* permission will be the effective one.
    """

    view_all = 'view_all_interaction'
    view_associated_investmentproject = 'view_associated_investmentproject_interaction'
    change_all = 'change_all_interaction'
    change_associated_investmentproject = 'change_associated_investmentproject_interaction'
    add_all = 'add_all_interaction'
    add_associated_investmentproject = 'add_associated_investmentproject_interaction'
    delete = 'delete_interaction'
    export = 'export_interaction'


class CommunicationChannel(BaseConstantModel):
    """Communication channel/mode of communication."""


class ServiceDeliveryStatus(BaseOrderedConstantModel):
    """
    Status of a service delivery.

    Primarily used for Tradeshow Access Programme (TAP) grants.
    """


class PolicyArea(BaseOrderedConstantModel):
    """
    Policy area for a policy feedback interaction.
    """


class PolicyIssueType(BaseOrderedConstantModel):
    """
    Policy issue type for a policy feedback interaction.
    """


class InteractionDITParticipant(models.Model):
    """
    Many-to-many model between an interaction and an adviser (called a DIT participant).

    This will replace Interaction.dit_adviser and Interaction.dit_team.

    Due to a small number of old records that have only a team or an adviser,
    adviser and team are nullable (but do not have blank=True, to avoid any further
    such records being created).
    """

    id = models.BigAutoField(primary_key=True)
    interaction = models.ForeignKey(
        'interaction.Interaction',
        on_delete=models.CASCADE,
        related_name='dit_participants',
    )
    adviser = models.ForeignKey(
        'company.Advisor',
        null=True,
        on_delete=models.CASCADE,
        related_name='+',
    )
    team = models.ForeignKey(
        'metadata.Team',
        null=True,
        on_delete=models.CASCADE,
        related_name='+',
    )

    def __str__(self):
        """Human-readable representation."""
        return f'{self.interaction} – {self.adviser} – {self.team}'

    class Meta:
        default_permissions = ()
        unique_together = (('interaction', 'adviser'),)


@reversion.register_base_model()
class Interaction(ArchivableModel, BaseModel):
    """Interaction."""

    KINDS = Choices(
        ('interaction', 'Interaction'),
        ('service_delivery', 'Service delivery'),
    )

    STATUSES = Choices(
        ('draft', 'Draft'),
        ('complete', 'Complete'),
    )

    THEMES = Choices(
        (None, 'Not set'),
        ('export', 'Export'),
        ('investment', 'Investment'),
        ('other', 'Something else'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    theme = models.CharField(
        max_length=MAX_LENGTH,
        choices=THEMES,
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=MAX_LENGTH, choices=KINDS)
    # TODO: Ensure that this is required (with default="complete")
    # once we have ensured that a default value "complete" is set on
    # all existing Interactions and we have ensured that new interactions are
    # being created with a status
    status = models.CharField(
        max_length=MAX_LENGTH,
        choices=STATUSES,
        null=True,
        blank=True,
    )
    # TODO: Remove this override (the field is provided with a default by ArchivableModel)
    # once we have ensured that a default value False is set on
    # all existing Interactions and we have ensured that new interactions are
    # being created with archived=False
    archived = models.BooleanField(blank=True, null=True)
    # If source is set, it provides details of an external source that this
    # interaction represents.  e.g. a calendar event
    # {'id': 'abc123', 'type': 'calendar'}
    source = JSONField(encoder=DjangoJSONEncoder, blank=True, null=True)
    date = models.DateTimeField()
    company = models.ForeignKey(
        'company.Company',
        related_name='%(class)ss',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    contacts = models.ManyToManyField(
        'company.Contact',
        related_name='%(class)ss',
        blank=True,
    )
    event = models.ForeignKey(
        'event.Event',
        related_name='%(class)ss',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text='For service deliveries only.',
    )
    service = models.ForeignKey(
        'metadata.Service', blank=True, null=True, on_delete=models.SET_NULL,
    )
    subject = models.TextField()
    # TODO: Ensure that this is required (with default='')
    # once we have ensured that a default value '' is set on
    # all existing Interactions and we have ensured that new interactions are
    # being created with a '' location
    location = models.CharField(max_length=MAX_LENGTH, blank=True, null=True)
    # TODO: dit_adviser is being replaced with InteractionDITParticipant, and dit_adviser will be
    #  removed once the migration is complete
    dit_adviser = models.ForeignKey(
        'company.Advisor',
        related_name='%(class)ss',
        null=True,
        on_delete=models.PROTECT,
        help_text='This field is deprecated and has been replaced by DIT participants.',
    )
    notes = models.TextField(max_length=10000, blank=True)
    # TODO: dit_team is being replaced with InteractionDITParticipant, and dit_team will be
    #  removed once the migration is complete
    dit_team = models.ForeignKey(
        'metadata.Team',
        null=True,
        on_delete=models.PROTECT,
        help_text='This field is deprecated and has been replaced by DIT participants.',
    )
    communication_channel = models.ForeignKey(
        'CommunicationChannel', blank=True, null=True,
        on_delete=models.SET_NULL,
        help_text='For interactions only.',
    )
    archived_documents_url_path = models.CharField(
        max_length=MAX_LENGTH, blank=True,
        help_text='Legacy field. File browser path to the archived documents for this '
                  'interaction.',
    )
    service_delivery_status = models.ForeignKey(
        'ServiceDeliveryStatus', blank=True, null=True, on_delete=models.PROTECT,
        verbose_name='status',
        help_text='For service deliveries only.',
    )
    # Investments
    investment_project = models.ForeignKey(
        'investment.InvestmentProject',
        related_name='%(class)ss',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text='For interactions only.',
    )
    # Grants
    grant_amount_offered = models.DecimalField(
        null=True, blank=True, max_digits=19, decimal_places=2,
        help_text='For service deliveries only.',
    )
    net_company_receipt = models.DecimalField(
        null=True, blank=True, max_digits=19, decimal_places=2,
        help_text='For service deliveries only.',
    )
    # Policy feedback
    was_policy_feedback_provided = models.BooleanField()
    policy_areas = models.ManyToManyField(
        'PolicyArea',
        blank=True,
        related_name='interactions',
    )
    policy_issue_types = models.ManyToManyField(
        'PolicyIssueType',
        blank=True,
        related_name='interactions',
    )
    policy_feedback_notes = models.TextField(blank=True, default='')

    @property
    def is_event(self):
        """Whether this service delivery is for an event."""
        if self.kind == self.KINDS.service_delivery:
            return bool(self.event)
        return None

    def get_absolute_url(self):
        """URL to the object in the Data Hub internal front end."""
        return get_front_end_url(self)

    def __str__(self):
        """Human-readable representation."""
        return self.subject

    class Meta:
        indexes = [
            models.Index(fields=['-date', '-created_on']),
        ]
        permissions = (
            (
                InteractionPermission.view_associated_investmentproject.value,
                'Can view interaction for associated investment projects',
            ),
            (
                InteractionPermission.add_associated_investmentproject.value,
                'Can add interaction for associated investment projects',
            ),
            (
                InteractionPermission.change_associated_investmentproject.value,
                'Can change interaction for associated investment projects',
            ),
            (
                InteractionPermission.export.value,
                'Can export interaction',
            ),
        )
        default_permissions = (
            'add_all',
            'change_all',
            'delete',
            'view_all',
        )
