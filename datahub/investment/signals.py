from django.db.models.signals import post_save
from django.dispatch import receiver

from datahub.investment.models import (
    InvestmentProject, InvestmentProjectCode, InvestmentProjectStageLog
)


@receiver(post_save, sender=InvestmentProject, dispatch_uid='project_code_project_post_save')
def project_code_project_post_save(sender, **kwargs):
    """Creates a project code for investment projects on creation.

    Projects with a CDMS project code do not get a new project code.

    This generates project codes for fixtures loaded via manage.py loaddata (i.e. when
    kwargs['raw'] is True), though that may need to change if fixed project codes are
    required for that fixtures.
    """
    instance = kwargs['instance']
    created = kwargs['created']
    if created and not instance.cdms_project_code:
        InvestmentProjectCode.objects.create(project=instance)


@receiver(post_save, sender=InvestmentProject, dispatch_uid='stage_log_project_post_save')
def stage_log_project_post_save(sender, **kwargs):
    """Creates a log of changes to stage field."""
    instance = kwargs['instance']
    created = kwargs['created']

    created_on = None

    if created:
        created_on = instance.created_on
    else:
        last_stage = InvestmentProjectStageLog.objects.order_by('-created_on').first()
        if last_stage.stage != instance.stage:
            created_on = instance.modified_on

    if created_on:
        InvestmentProjectStageLog.objects.create(
            investment_project=instance,
            stage=instance.stage,
            created_on=created_on,
        )
