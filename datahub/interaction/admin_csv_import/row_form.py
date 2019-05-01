from enum import IntEnum

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy

from datahub.company.models import Advisor, Contact
from datahub.core.query_utils import get_full_name_expression
from datahub.event.models import Event
from datahub.interaction.models import CommunicationChannel, Interaction
from datahub.metadata.models import Service, Team


OBJECT_DISABLED_MESSAGE = gettext_lazy('This option is disabled.')
ADVISER_NOT_FOUND_MESSAGE = gettext_lazy(
    'An active adviser could not be found with the specified name.',
)
ADVISER_WITH_TEAM_NOT_FOUND_MESSAGE = gettext_lazy(
    'An active adviser could not be found with the specified name and team.',
)
MULTIPLE_ADVISERS_FOUND_MESSAGE = gettext_lazy(
    'Multiple matching advisers were found.',
)
INTERACTION_CANNOT_HAVE_AN_EVENT_MESSAGE = gettext_lazy(
    'An interaction cannot have an event.',
)


def _validate_not_disabled(obj):
    if obj.disabled_on:
        raise ValidationError(OBJECT_DISABLED_MESSAGE, code='object_is_disabled')


class ContactMatchingStatus(IntEnum):
    """The contact matching status of an interaction."""

    matched = 1
    unmatched = 2
    multiple_matches = 3


class NoDuplicatesModelChoiceField(forms.ModelChoiceField):
    """ModelChoiceField subclass that handles MultipleObjectsReturned exceptions."""

    default_error_messages = {
        'multiple_matches': gettext_lazy('There is more than one matching %(verbose_name)s.'),
    }

    def to_python(self, value):
        """Looks up value using the query set, handling MultipleObjectsReturned exceptions."""
        model = self.queryset.model
        try:
            return super().to_python(value)
        except model.MultipleObjectsReturned:
            raise ValidationError(
                self.error_messages['multiple_matches'],
                code='multiple_matches',
                params={
                    'verbose_name': model._meta.verbose_name,
                },
            )


class InteractionCSVRowForm(forms.Form):
    """Form used for validating a single row in a CSV of interactions."""

    kind = forms.ChoiceField(choices=Interaction.KINDS)
    date = forms.DateField(input_formats=['%d/%m/%Y', '%Y-%m-%d'])
    # Used to attempt to find a matching contact (and company) for the interaction
    # Note that if a matching contact is not found, the interaction in question is
    # skipped (and the user informed) rather than the whole process aborting
    contact_email = forms.EmailField()
    # Represents an InteractionDITParticipant for the interaction.
    # The adviser will be looked up by name (case-insensitive) with inactive advisers
    # excluded.
    # If team_1 is provided, this will also be used to narrow down the match (useful
    # when, for example, two advisers have the same name).
    adviser_1 = forms.CharField()
    team_1 = NoDuplicatesModelChoiceField(
        Team.objects.all(),
        to_field_name='name__iexact',
        required=False,
    )
    # Represents an additional InteractionDITParticipant for the interaction
    # adviser_2 is looked up in the same way as adviser_1 (described above)
    adviser_2 = forms.CharField(required=False)
    team_2 = NoDuplicatesModelChoiceField(
        Team.objects.all(),
        to_field_name='name__iexact',
        required=False,
    )
    service = NoDuplicatesModelChoiceField(
        Service.objects.all(),
        to_field_name='name__iexact',
        validators=[_validate_not_disabled],
    )
    communication_channel = NoDuplicatesModelChoiceField(
        CommunicationChannel.objects.all(),
        to_field_name='name__iexact',
        required=False,
        validators=[_validate_not_disabled],
    )
    event_id = forms.ModelChoiceField(
        Event.objects.all(),
        required=False,
        validators=[_validate_not_disabled],
    )
    # Subject is optional as it defaults to the name of the service
    subject = forms.CharField(required=False)
    notes = forms.CharField(required=False)

    @classmethod
    def get_required_field_names(cls):
        """Get the required base fields of this form."""
        return {name for name, field in cls.base_fields.items() if field.required}

    def clean(self):
        """Validate and clean the data for this row."""
        data = super().clean()

        kind = data.get('kind')
        event = data.get('event_id')
        subject = data.get('subject')
        service = data.get('service')

        # Ignore communication channel for service deliveries (as it is not a valid field for
        # service deliveries, but we are likely to get it in provided data anyway)
        if kind == Interaction.KINDS.service_delivery:
            data['communication_channel'] = None

        # Reject if an event has been given but it's an interaction (as the event field is only
        # valid for service deliveries – we don't know if the kind field is wrong or the event
        # has been set in error)
        if kind == Interaction.KINDS.interaction and event:
            error = ValidationError(
                INTERACTION_CANNOT_HAVE_AN_EVENT_MESSAGE,
                code='interaction_cannot_have_event',
            )
            self.add_error('event_id', error)

        # Look up values for adviser_1 and adviser_2 (adding errors if the look-up fails)
        self._populate_adviser(data, 'adviser_1', 'team_1')
        self._populate_adviser(data, 'adviser_2', 'team_2')

        # If no subject was provided, set it to the name of the service
        if not subject and service:
            data['subject'] = service.name

        # Attempt to look up the contact
        self._populate_contact(data)

        return data

    def _populate_adviser(self, data, adviser_field, team_field):
        try:
            data[adviser_field] = _look_up_adviser(
                data.get(adviser_field),
                data.get(team_field),
            )
        except ValidationError as exc:
            self.add_error(adviser_field, exc)

    def _populate_contact(self, data):
        """
        Attempts to look up a matching contact by email address.

        The following the logic is used:

        - only non-archived contacts are considered
        - if a unique match is found using Contact.email, this is used
        - if there are multiple matches found using Contact.email, matching aborts
        - otherwise, if there is a unique match on Contact.email_alternative, this is used
        """
        contact_email = data.get('contact_email')
        contact, matching_status = _look_up_contact(contact_email, 'email')
        if matching_status == ContactMatchingStatus.unmatched:
            contact, matching_status = _look_up_contact(contact_email, 'email_alternative')

        data['contact'] = contact
        data['contact_matching_status'] = matching_status


def _look_up_adviser(adviser_name, team):
    if not adviser_name:
        return None

    get_kwargs = {
        'is_active': True,
        'name__iexact': adviser_name,
    }

    if team:
        get_kwargs['dit_team'] = team

    queryset = Advisor.objects.annotate(name=get_full_name_expression())

    try:
        return queryset.get(**get_kwargs)
    except Advisor.DoesNotExist:
        if team:
            raise ValidationError(
                ADVISER_WITH_TEAM_NOT_FOUND_MESSAGE,
                code='adviser_and_team_not_found',
            )

        raise ValidationError(ADVISER_NOT_FOUND_MESSAGE, code='adviser_not_found')
    except Advisor.MultipleObjectsReturned:
        raise ValidationError(MULTIPLE_ADVISERS_FOUND_MESSAGE, code='multiple_advisers_found')


def _look_up_contact(email_address, lookup_field):
    """
    Looks up a contact by email address.

    :param email_address: The email address to find a matching contact for
    :param lookup_field: The name of the email address field on contact to use for matching
    """
    contact = None
    get_kwargs = {
        'archived': False,
        f'{lookup_field}__iexact': email_address,
    }

    try:
        contact = Contact.objects.get(**get_kwargs)
        contact_matching_status = ContactMatchingStatus.matched
    except Contact.DoesNotExist:
        contact_matching_status = ContactMatchingStatus.unmatched
    except Contact.MultipleObjectsReturned:
        contact_matching_status = ContactMatchingStatus.multiple_matches

    return contact, contact_matching_status
