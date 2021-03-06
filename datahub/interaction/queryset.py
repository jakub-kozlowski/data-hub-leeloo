from django.db.models import OuterRef, Prefetch, Subquery

from datahub.core.model_helpers import get_m2m_model
from datahub.interaction.models import Interaction, InteractionDITParticipant


def get_interaction_queryset():
    """Gets the interaction query set used by v3 views."""
    contacts_m2m_model = get_m2m_model(Interaction, 'contacts')
    first_contact_queryset = contacts_m2m_model.objects.filter(
        interaction_id=OuterRef('pk'),
        # We order by pk so that we always use the same contact, but note that when
        # calling .set() on a many-to-many field, Django inserts the many-to-many objects
        # in an arbitrary order
    ).order_by(
        'pk',
    )[:1]

    return Interaction.objects.annotate(
        first_name_of_first_contact=Subquery(
            first_contact_queryset.values('contact__first_name'),
        ),
        last_name_of_first_contact=Subquery(
            first_contact_queryset.values('contact__last_name'),
        ),
    ).select_related(
        'company',
        'created_by',
        'archived_by',
        'dit_adviser',
        'dit_team',
        'communication_channel',
        'investment_project',
        'modified_by',
        'service',
        'service_delivery_status',
        'event',
    ).prefetch_related(
        'contacts',
        'policy_areas',
        'policy_issue_types',
        Prefetch(
            'dit_participants',
            queryset=InteractionDITParticipant.objects.select_related('adviser', 'team'),
        ),
    )
