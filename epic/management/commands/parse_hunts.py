import csv
import json
import os
import sys
from contextlib import ExitStack

from pathlib import Path

from django.core.management import BaseCommand

from epic.models import Hunt
from epic.utils import ignore_broken_pipe
from epic.types.classes import Namespace


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file", metavar="FILE")
        parser.add_argument("-o", "--output", nargs="?")

    @ignore_broken_pipe
    def handle(self, *args, **options):
        file = Path(os.path.join(os.getcwd(), options["file"]))
        output = Path(os.path.join(os.getcwd(), options["output"])) if options["output"] else None
        with ExitStack() as es:
            r = es.enter_context(open(file, "r"))
            w = es.enter_context(open(output, "w")) if output else sys.stdout
            writer = csv.writer(w)
            writer.writerow(["name", "target", "money", "xp", "loot"])
            for line in r.readlines():
                parsed = json.loads(line)
                h = Namespace.from_collection(parsed)
                if not h.content:
                    continue
                hunt_result = Hunt.hunt_result_from_message(h)
                if hunt_result:
                    writer.writerow(hunt_result)
                    continue
                for hunt_together_result in Hunt.hunt_together_from_message(h):
                    writer.writerow(hunt_together_result)
