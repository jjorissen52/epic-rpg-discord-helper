import datetime

from types import SimpleNamespace

from django.db import models
from django.db.models import Case, When, Max, Min, Sum, Count, F, Value


class ProfileManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(notify=True, server__active=True)

    def command_type_enabled(self, command_type):
        return self.active().filter(**{command_type: True})


class GamblingStatsManager(models.Manager):
    def stats(self, profile_uid, minutes=None):
        game_case = Case(
            When(game="bj", then=Value("blackjack")), When(game="cf", then=Value("coinflip")), default="game"
        )
        qs = self.get_queryset().filter(profile_id=profile_uid)
        if minutes:
            after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
            qs = qs.filter(created__gt=after)
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
            return (("No Results", "No games were played in that time period."),)

        game_col_size, min_col_size = 15, 8
        win_col_size = max(max([len(str(f"{r['big_win']:,}")) for r in earnings_results]), min_col_size)
        loss_col_size = max(max([len(str(f"{r['big_loss']:,}")) for r in earnings_results]), min_col_size)
        total_col_size = max(max([len(str(f"{r['total']:,}")) for r in earnings_results]), min_col_size)
        biggest_net, lifetime = (
            f"{'Game':<{game_col_size}}     {'Big Win':>{win_col_size}}  {'Big Loss':>{loss_col_size}}\n",
            "",
        )
        for game in earnings_results:
            g = SimpleNamespace(**game)
            biggest_net += f"{g.g:{game_col_size}} ==> {g.big_win:{win_col_size},}  {g.big_loss:{loss_col_size},}\n"
            lifetime += f"{g.g:{game_col_size}} ==> {g.total:{total_col_size},}\n"
        biggest_net = f"```\n{biggest_net}```"
        lifetime = f"```\n{lifetime}```"

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
        games_played = f"{'Game':<{game_col_size}}     {'Wins':>{win_col_size}}  {'Losses':>{loss_col_size}}  {'Ties':>{tied_col_size}}  {'Total':>{total_col_size}}\n"
        for game in games_played_results:
            g = SimpleNamespace(**game)
            games_played += f"{g.g:{game_col_size}} ==> {g.won:{win_col_size},}  {g.lost:{loss_col_size},}  {g.tied:{tied_col_size},}  {g.total:{total_col_size},}\n"
        games_played = f"```\n{games_played}```"

        return (
            ("Games Played", games_played),
            ("Biggest Net", biggest_net),
            ("Lifetime Winnins", lifetime),
        )
