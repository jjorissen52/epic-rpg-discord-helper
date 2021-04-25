import json
from pathlib import Path

from epic.types.classes import Namespace

HISTORY_DIR = None


def get_history_dir():
    global settings
    global HISTORY_DIR
    if not HISTORY_DIR:
        HISTORY_DIR = Path(settings.BASE_DIR) / "epic" / "import" / "history"
    return HISTORY_DIR


def gambling(file_name="/tmp/message_dump.json"):
    history_file = get_history_dir() / file_name
    all_profiles = {profile.uid: profile for profile in Profile.objects.all()}
    gambles = []
    with open(history_file, "r") as hist:
        for line in hist.readlines():
            parsed = json.loads(line)
            h = Namespace.from_collection(parsed)
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


def hunt(file_name="/tmp/message_dump.json"):
    history_file = get_history_dir() / file_name
    # risk of collision here :shrug:
    all_profiles = {profile.last_known_nickname: profile for profile in Profile.objects.all()}
    hunts = []
    with open(history_file, "r") as hist:
        for line in hist.readlines():
            parsed = json.loads(line)
            h = Namespace.from_collection(parsed)
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
    import fire

    from django.core.wsgi import get_wsgi_application

    dotenv.load_dotenv(override=True)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epic_reminder.settings")

    get_wsgi_application()

    from epic.models import Gamble, Profile, Hunt

    fire.Fire(
        {
            "hunt": hunt,
            "gambling": gambling,
        }
    )
