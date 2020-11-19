from django.contrib import admin

from .models import Profile, CoolDown


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass


@admin.register(CoolDown)
class CoolDownAdmin(admin.ModelAdmin):
    pass
