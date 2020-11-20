from django.contrib import admin

from .models import Profile, CoolDown, Server, JoinCode


@admin.register(JoinCode)
class JoinCodeAdmin(admin.ModelAdmin):
    pass


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    search_fields = ("code__id", "name", "id")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    search_fields = ("last_known_nickname", "uid")


@admin.register(CoolDown)
class CoolDownAdmin(admin.ModelAdmin):
    pass
