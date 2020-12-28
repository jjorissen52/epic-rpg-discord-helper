import json
from pathlib import Path
from types import SimpleNamespace

HISTORY_DIR = None


def get_history_dir():
    global settings
    global HISTORY_DIR
    if not HISTORY_DIR:
        HISTORY_DIR = Path(settings.BASE_DIR) / "epic" / "import" / "history"
    return HISTORY_DIR


class Namespace(SimpleNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty = not args and not kwargs

    def __getattribute__(self, item):
        try:
            attr = super().__getattribute__(item)
        except AttributeError:
            return Namespace()
        if attr is None:
            return Namespace()
        return attr

    def __str__(self):
        if self._empty:
            return ""
        return "Namespace Obj"

    def __bool__(self):
        return not self._empty


def recursive_namespace(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = recursive_namespace(v)
        return Namespace(**obj)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = recursive_namespace(obj[i])
        return obj
    return obj


def gambling(file_name="message_dump.json"):
    history_file = get_history_dir() / file_name
    all_profiles = {profile.uid: profile for profile in Profile.objects.all()}
    gambles = []
    with open(history_file, "r") as hist:
        for line in hist.readlines():
            parsed = json.loads(line)
            h = recursive_namespace(parsed)
            if h.embeds:
                for embed in h.embeds:
                    if h.embeds[0].author.icon_url:
                        uid = embed.author.icon_url.strip("https://cdn.discordapp.com/avatars/").split("/")[0]
                        profile = all_profiles.get(uid, None)
                        if profile:
                            gamble = Gamble.from_results_screen(profile, embed)
                            if gamble:
                                gamble.created = h.created_at
                                gamble.updated = h.created_at
                                gambles.append(gamble)
    Gamble.objects.bulk_create(gambles)


def hunt(file_name="message_dump.json"):
    history_file = get_history_dir() / file_name
    # risk of collision here :shrug:
    all_profiles = {profile.last_known_nickname: profile for profile in Profile.objects.all()}
    hunts = []
    with open(history_file, "r") as hist:
        for line in hist.readlines():
            parsed = json.loads(line)
            h = recursive_namespace(parsed)
            if h.content:
                hunt_result = Hunt.hunt_result_from_message(h)
                if hunt_result:
                    name, target, money, xp, loot = hunt_result
                    hunts.append(
                        Hunt(
                            profile=all_profiles[name],
                            target=target,
                            money=money,
                            xp=xp,
                            loot=loot,
                            created=h.created_at,
                            updated=h.created_at,
                        )
                    )
                else:
                    hunt_together_result = Hunt.hunt_together_from_message(h)
                    if hunt_together_result:
                        name, target, money, xp, loot = hunt_together_result[0]
                        hunts.append(
                            Hunt(
                                profile=all_profiles[name],
                                target=target,
                                money=money,
                                xp=xp,
                                loot=loot,
                                created=h.created_at,
                                updated=h.created_at,
                            )
                        )
                        name, target, money, xp, loot = hunt_together_result[1]
                        hunts.append(
                            Hunt(
                                profile=all_profiles[name],
                                target=target,
                                money=money,
                                xp=xp,
                                loot=loot,
                                created=h.created_at,
                                updated=h.created_at,
                            )
                        )

    Hunt.objects.bulk_create(hunts)


if __name__ == "__main__":
    import os
    import dotenv
    import sys
    import fire

    from django.core.wsgi import get_wsgi_application

    dotenv.load_dotenv(override=True)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

    get_wsgi_application()

    from django.conf import settings
    from epic.models import Gamble, Server, Profile, Hunt

    fire.Fire(
        {
            "hunt": hunt,
            "gambling": gambling,
        }
    )
