import json

from epic.types import Namespace


class FakeClient:
    user = "Test Client User"
    users = None

    def __init__(self, users: dict):
        self.users = {int(key): Namespace.from_collection(user) for key, user in users.items()}

    def get_user(self, user_id: int):
        return self.users.get(int(user_id), None)


class FixtureLoader:
    data_dir = None

    def unpack_activities(self, fixture_name, variant=None):
        with open(self.data_dir / f"{fixture_name}.json", "r") as r:
            activities = json.load(r)
        # if no variant is provided, we assume that the activity is at the top level of the JSON
        # fixture without a key/value pair
        if variant:
            idata, confirm_data = activities[variant]["initiate"], activities[variant]["confirm"]
        else:
            idata, confirm_data = activities["initiate"], activities["confirm"]
        return Namespace.from_collection(idata), Namespace.from_collection(confirm_data)
