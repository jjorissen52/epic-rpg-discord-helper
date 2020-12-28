import datetime

from django.db import models


class UpdateAble(models.Model):
    class Meta:
        abstract = True

    created = models.DateTimeField(db_index=True)
    updated = models.DateTimeField(db_index=True)

    def save(self, *args, **kwargs):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if not self.pk and not self.created:
            self.created = now
        self.updated = now
        return super().save(*args, **kwargs)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save()
