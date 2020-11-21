from django.db import models


class ProfileManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(notify=True, server__active=True)

    def command_type_enabled(self, command_type):
        return self.active().filter(**{command_type: True})
