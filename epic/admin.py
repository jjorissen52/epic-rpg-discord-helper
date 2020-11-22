from django.contrib import admin

from .models import Profile, CoolDown, Server, JoinCode


@admin.register(JoinCode)
class JoinCodeAdmin(admin.ModelAdmin):
    list_filter = ("claimed",)
    list_display = ("code", "claimed")


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    search_fields = ("code__id", "name", "id")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    search_fields = ("last_known_nickname", "uid")
    list_filter = ("notify",)


@admin.register(CoolDown)
class CoolDownAdmin(admin.ModelAdmin):
    search_fields = ("profile__last_known_nickname", "type")
