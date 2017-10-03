from datahub.interaction import models
from datahub.metadata.fixtures import Fixture
from datahub.metadata.registry import registry


class InteractionFixtures(Fixture):
    """Metadata fixtures (for the loadmetadata command)."""

    files = [
        'fixtures/communication_channels.yaml'
    ]


registry.register(
    metadata_id='communication-channel',
    model=models.CommunicationChannel,
)

# For backwards compatibility. Will be removed once front end updated.
registry.register(
    metadata_id='interaction-type',
    model=models.CommunicationChannel,
)
