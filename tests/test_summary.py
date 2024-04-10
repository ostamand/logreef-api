import datetime

import pytest

from api.summary import get_by_type, get_for_all
from api.persistence.database import delete_from_db
from api.persistence import params
from api.config import TestKits
from .helpers import save_random_aquarium, save_random_user


def test_can_get_summary_for_all_types(test_db):
    user = save_random_user(test_db)
    aquarium = save_random_aquarium(test_db, user.id)
    param_1 = params.create(test_db, user.id, aquarium.id, "alkalinity", 9.5)
    param_2 = params.create(test_db, user.id, aquarium.id, "alkalinity", 9.0)
    param_3 = params.create(test_db, user.id, aquarium.id, "ph", 8.2)
    param_4 = params.create(test_db, user.id, aquarium.id, "magnesium", 1200)

    info = get_for_all(test_db, user.id)
    for type in ["alkalinity", "ph", "magnesium"]:
        assert type in info

    assert info["magnesium"]["values"][0] == 1200
    assert len(info["alkalinity"]["values"]) == 2

    delete_from_db(test_db, user)
    delete_from_db(test_db, aquarium)
    delete_from_db(test_db, param_1)
    delete_from_db(test_db, param_2)
    delete_from_db(test_db, param_3)
    delete_from_db(test_db, param_4)


def test_can_get_summary_for_type(test_db):
    user = save_random_user(test_db)
    aquarium = save_random_aquarium(test_db, user.id)

    param_type_name = "alkalinity"
    value_1 = 8.9
    value_2 = 10.0
    ts_1 = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    ts_2 = (ts_1 - datetime.timedelta(days=1)).replace(tzinfo=None)

    param_1 = params.create(
        test_db, user.id, aquarium.id, param_type_name, value_1, timestamp=ts_1
    )
    param_2 = params.create(
        test_db, user.id, aquarium.id, param_type_name, value_2, timestamp=ts_2
    )

    summary = get_by_type(
        test_db,
        user.id,
        param_type_name,
    )
    keys = ["values", "timestamps", "time_since_secs", "count_last_week"]
    for key in keys:
        assert key in summary

    assert value_1 == pytest.approx(summary["values"][0])
    assert value_2 == pytest.approx(summary["values"][1])

    assert ts_1 == pytest.approx(summary["timestamps"][0])
    assert ts_2 == pytest.approx(summary["timestamps"][1])

    assert summary["count_last_week"] == 2
    delete_from_db(test_db, param_1)

    summary = get_by_type(
        test_db,
        user.id,
        param_type_name,
    )
    assert summary["count_last_week"] == 1

    delete_from_db(test_db, user)
    delete_from_db(test_db, aquarium)
    delete_from_db(test_db, param_2)