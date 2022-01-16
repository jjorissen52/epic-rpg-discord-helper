import datetime

from types import SimpleNamespace

from django.db import models
from django.db.models import Case, When, Max, Min, Sum, Count, F, Value, Q


class ProfileManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(notify=True, server__active=True)

    def command_type_enabled(self, command_type):
        return self.active().filter(**{command_type: True})


class GamblingStatsManager(models.Manager):
    def stats(self, profile_uid=None, minutes=None, server_id=None):
        game_case = Case(
            When(game="bj", then=Value("blackjack")), When(game="cf", then=Value("coinflip")), default="game"
        )
        qs = self.get_queryset()
        if profile_uid:
            qs = qs.filter(profile_id=profile_uid)
        if minutes:
            after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
            qs = qs.filter(created__gt=after)
        if server_id:
            qs = qs.filter(profile__server_id=server_id)
        earnings = (
            qs.values("game")
            .order_by("game")
            .annotate(
                g=game_case,
                big_win=Max(
                    Case(
                        When(net__gt=0, then="net"),
                        default=0,
                    )
                ),
                big_loss=Min(
                    Case(
                        When(net__lt=0, then="net"),
                        default=0,
                    )
                ),
                total=Sum("net"),
            )
        )
        earnings_results = earnings.values("g", "big_win", "big_loss", "total")
        if not earnings_results:
            return (("No Results", "No games could be found."),)

        game_col_size, min_col_size = 15, 8
        win_col_size = max(max([len(str(f"{r['big_win']:,}")) for r in earnings_results]), min_col_size)
        loss_col_size = max(max([len(str(f"{r['big_loss']:,}")) for r in earnings_results]), min_col_size)
        total_col_size = max(max([len(str(f"{r['total']:,}")) for r in earnings_results]), min_col_size)
        biggest_net, lifetime = (
            f"{'Game':<{game_col_size}}     {'Big Win':>{win_col_size}}  {'Big Loss':>{loss_col_size}}\n",
            "",
        )
        t = SimpleNamespace(big_win=0, big_loss=0, total=0)
        for game in earnings_results:
            g = SimpleNamespace(**game)
            biggest_net += f"{g.g:{game_col_size}} ==> {g.big_win:{win_col_size},}  {g.big_loss:{loss_col_size},}\n"
            lifetime += f"{g.g:{game_col_size}} ==> {g.total:{total_col_size},}\n"
            t.big_win, t.big_loss, t.total = t.big_win + g.big_win, t.big_loss + g.big_loss, t.total + g.total
        biggest_net = f"```\n{biggest_net}{'Total':{game_col_size}} ==> {t.big_win:{win_col_size},}  {t.big_loss:{loss_col_size},}\n```"
        lifetime = f"```\n{lifetime}{'Total':{game_col_size}} ==> {t.total:{total_col_size},}```"

        games_played = (
            qs.values("game")
            .order_by("game")
            .annotate(
                g=game_case,
                won=Sum(
                    Case(
                        When(outcome="won", then=1),
                        default=0,
                        output_field=models.IntegerField(),
                    )
                ),
                lost=Sum(
                    Case(
                        When(outcome="lost", then=1),
                        default=0,
                        output_field=models.IntegerField(),
                    )
                ),
                tied=Sum(
                    Case(
                        When(outcome="tied", then=1),
                        default=0,
                        output_field=models.IntegerField(),
                    )
                ),
                total=Count("net"),
            )
        )
        games_played_results = games_played.values("g", "won", "lost", "tied", "total")

        game_col_size, min_col_size = 15, 6
        win_col_size = max(max([len(str(f"{r['won']:,}")) for r in games_played_results]), min_col_size)
        loss_col_size = max(max([len(str(f"{r['lost']:,}")) for r in games_played_results]), min_col_size)
        tied_col_size = max(max([len(str(f"{r['tied']:,}")) for r in games_played_results]), min_col_size)
        total_col_size = max(max([len(str(f"{r['total']:,}")) for r in games_played_results]), min_col_size)
        t = SimpleNamespace(wins=0, losses=0, ties=0, total=0)
        games_played = f"{'Game':<{game_col_size}}     {'Wins':>{win_col_size}}  {'Losses':>{loss_col_size}}  {'Ties':>{tied_col_size}}  {'Total':>{total_col_size}}\n"
        for game in games_played_results:
            g = SimpleNamespace(**game)
            games_played += f"{g.g:{game_col_size}} ==> {g.won:{win_col_size},}  {g.lost:{loss_col_size},}  {g.tied:{tied_col_size},}  {g.total:{total_col_size},}\n"
            t.wins, t.losses, t.ties, t.total = t.wins + g.won, t.losses + g.lost, t.ties + g.tied, t.total + g.total
        games_played = f"```\n{games_played}{'Total':{game_col_size}} ==> {t.wins:{win_col_size},}  {t.losses:{loss_col_size},}  {t.ties:{tied_col_size},}  {t.total:{total_col_size},}\n```"

        return (
            ("Games Played", games_played),
            ("Biggest Net", biggest_net),
            ("Lifetime Winnins", lifetime),
        )


class HuntQuerySet(models.QuerySet):
    def profile_hunts(self, profile_id=None, minutes=None, server_id=None):
        self = self.filter(target__isnull=False)
        if server_id:
            self = self.filter(profile__server_id=server_id)
        if profile_id:
            self = self.filter(profile_id=profile_id)
        if minutes:
            after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
            self = self.filter(created__gt=after)
        return self


class HuntManager(models.Manager):
    def get_queryset(self):
        return HuntQuerySet(self.model, using=self._db)

    def open_hunts(self, profile_ids):
        return self.get_queryset().filter(target__isnull=True, profile_id__in=profile_ids)

    def hunt_stats(self, profile_id=None, minutes=None, server_id=None):
        qs = self.get_queryset().profile_hunts(profile_id, minutes, server_id)
        lifetime_hunts = (
            qs.values("target")
            .order_by("target")
            .annotate(
                hunted=Count("id"),
                xp=Sum("xp"),
                drops=Sum(Case(When(loot="", then=0), default=1, output_field=models.IntegerField())),
            )
            .order_by("-hunted", "-drops")
        )
        if not lifetime_hunts:
            return (("No Results", "No hunts could be found."),)

        min_col_size = 7
        target_col_size = max(max([len(str(f"{r['target'][:20]}")) for r in lifetime_hunts]), min_col_size) + 1
        hunted_col_size = max(max([len(str(f"{r['hunted']:,}")) for r in lifetime_hunts]), min_col_size) + 3
        xp_col_size = max(max([len(str(f"{r['xp']:,}")) for r in lifetime_hunts]), min_col_size) + 3
        drop_col_size = max(max([len(str(f"{r['drops']:,}")) for r in lifetime_hunts]), min_col_size) + 3

        header = f"{'Target':<{target_col_size}}{'Hunted':>{hunted_col_size}}{'Exp':>{xp_col_size}}{'Drops':>{drop_col_size}}\n"
        lifetime_pages = [header]
        lifetime_page = 0
        t = SimpleNamespace(hunted=0, xp=0, drops=0)
        for h in lifetime_hunts:
            h = SimpleNamespace(**h)
            h.target = f"{h.target[:17]}..." if len(h.target) > 20 else h.target
            next_line = f"{h.target:{target_col_size}}{h.hunted:{hunted_col_size},}{h.xp:{xp_col_size},}{h.drops:{drop_col_size},}\n"
            if not len(lifetime_pages[lifetime_page]) + len(next_line) < 1000:
                lifetime_pages.append(header)
                lifetime_page += 1
            lifetime_pages[lifetime_page] += next_line
            t.hunted, t.xp, t.drops = t.hunted + h.hunted, t.xp + h.xp, t.drops + h.drops
        next_line = (
            f'{"TOTAL":{target_col_size}}{t.hunted:{hunted_col_size},}{t.xp:{xp_col_size},}{t.drops:{drop_col_size},}\n'
        )
        if not len(lifetime_pages[lifetime_page]) + len(next_line) < 1000:
            lifetime_pages.append(header)
            lifetime_page += 1
        lifetime_pages[lifetime_page] += next_line
        return ((f"Hunt Statistics {i+1}", f"```\n{lifetime}```") for i, lifetime in enumerate(lifetime_pages))

    def drop_stats(self, profile_id=None, minutes=None, server_id=None):
        qs = self.get_queryset().profile_hunts(profile_id, minutes, server_id)
        lifetime_drops = (
            qs.exclude(Q(loot__isnull=True) | Q(loot=""))
            .values("loot")
            .order_by("loot")
            .annotate(
                dropped=Count("id"),
                sort=Case(When(loot__contains="lootbox", then=1), default=0, output_field=models.IntegerField()),
            )
            .order_by("-sort", "-dropped")
        )
        if not lifetime_drops:
            return (("No Results", "No drops could be found."),)

        min_col_size = 8
        loot_col_size = max(max([len(str(f"{r['loot']}")) for r in lifetime_drops]), min_col_size) + 2
        dropped_col_size = max(max([len(str(f"{r['dropped']}")) for r in lifetime_drops]), min_col_size) + 2
        lifetime = f"{'Loot':>{loot_col_size}}  {'Dropped':>{dropped_col_size}}\n"
        total_dropped = 0
        for d in lifetime_drops:
            d = SimpleNamespace(**d)
            lifetime += f"{d.loot:>{loot_col_size}}  {d.dropped:>{dropped_col_size},}\n"
            total_dropped += d.dropped
        lifetime = f"```\n{lifetime}{'Total':>{loot_col_size}}  {total_dropped:>{dropped_col_size},}\n```"
        return (("Drop Statistics", lifetime),)


class GroupActivityManager(models.Manager):
    def delete_stale(self):
        stale_time = now = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=60)
        qs = self.get_queryset().filter(created__lt=stale_time).delete()

    def latest_group_activity(self, profile_id_or_nickname, type):
        qs = self.get_queryset().filter(type=type)
        if isinstance(profile_id_or_nickname, str) and not profile_id_or_nickname.isdigit():
            # name conflict must be resolved on a best-effort basis,
            # which in this case means the newest activity by that profile
            qs = qs.filter(initiator__last_known_nickname=profile_id_or_nickname)
        else:
            qs = qs.filter(initiator_id=profile_id_or_nickname)
        return qs.order_by("-created").first()


class EventQuerySet(models.QuerySet):
    def active(self, is_active=True):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.filter(start__lt=now, end__gt=now) if is_active else self.exclude(start__lt=now, end__gt=now)
