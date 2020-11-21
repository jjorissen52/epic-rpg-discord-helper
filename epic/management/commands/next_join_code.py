import sys
from django.core.management.base import BaseCommand

from epic.models import JoinCode


class Command(BaseCommand):
    help = "Show the next n valid join codes"

    def add_arguments(self, parser):
        parser.add_argument("n", nargs="?", type=int)

    def handle(self, *args, **options):
        num_codes = 1 if not options["n"] else options["n"]

        for code in JoinCode.objects.filter(claimed=False)[:num_codes]:
            sys.stdout.write(f"{code.code}\n")
            sys.stdout.flush
