from datetime import datetime, timezone, UTC, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import text

from api.persistence import models
from api.persistence import aquariums
from api.persistence.database import engine
from api.config import (
    TestKits,
    ParamTypes,
    default_test_kits,
    get_param_type,
    get_test_kit,
)
from api.units.converter import convert_unit_for


def get_type_by_user(user_id: int) -> list[str]:
    with engine.connect() as con:
        sql = text(
            """
            SELECT DISTINCT(param_types.name)
            FROM param_values
            JOIN users ON param_values.user_id = users.id
            JOIN param_types ON param_values.param_type_name = param_types.name
            WHERE user_id = :user_id
            """
        )
        result = con.execute(sql, {"user_id": user_id})
        return [row[0] for row in result]


def get_type(db: Session, name: str):
    return (
        db.query(models.ParamType)
        .filter(models.ParamType.name == name.strip().lower())
        .first()
    )


def create(
    db: Session,
    user_id: int,
    aquarium: models.Aquarium | str | int,
    param_type: models.ParamType | str | ParamTypes,
    value: float,
    timestamp: datetime | None = None,
    test_kit: models.TestKit | str | TestKits | None = None,
):
    if not timestamp:
        timestamp = datetime.now(timezone.utc)

    if type(param_type) is models.ParamType:
        param_type = get_param_type(param_type.name)
    elif type(param_type) is str:
        param_type = get_param_type(param_type)

    if type(aquarium) is str:
        aquarium_id = aquariums.get_by_name(db, user_id, aquarium).id
    elif type(aquarium) is int:
        aquarium_id = aquarium
    elif type(aquarium) is models.Aquarium:
        aquarium_id = aquarium.id

    if type(test_kit) is str:
        test_kit = get_test_kit(test_kit)
    elif type(test_kit) is models.TestKit:
        test_kit = get_test_kit(test_kit.name)
    elif test_kit is None:
        test_kit = default_test_kits[param_type.value]

    # convert value
    # TODO: Also save value not converted?
    value_converted = convert_unit_for(param_type, test_kit, value)
    if value_converted is None:
        raise Exception(f"{param_type.value} and/or {test_kit.value} not supported")

    # TODO check if user is owner of aquarium?
    db_value = models.ParamValue(
        user_id=user_id,
        param_type_name=param_type.value,
        aquarium_id=aquarium_id,
        test_kit_name=test_kit.value,
        value=value_converted,
        timestamp=timestamp,
    )

    db.add(db_value)
    db.commit()
    db.refresh(db_value)
    return db_value


def get_count_by_type_last_n_days(
    db: Session, user_id: int, param_type: str, n_days: int
) -> int:
    now = datetime.now(UTC).replace(tzinfo=None)
    raw_query = (
        db.query(models.ParamValue)
        .join(models.ParamType)
        .where(models.ParamValue.user_id == user_id)
        .where(models.ParamType.name == param_type)
        .where(models.ParamValue.timestamp >= now - timedelta(days=n_days))
    )
    return raw_query.count()


def get_by_type(
    db: Session,
    user_id: int,
    param_type: str | ParamTypes,
    limit: int | None = None,
    offset: int | None = None,
):
    if type(param_type) is ParamTypes:
        param_type = param_type.value

    raw_query = (
        db.query(models.ParamValue)
        .join(models.ParamType)
        .where(models.ParamValue.user_id == user_id)
        .where(models.ParamType.name == param_type)
        .order_by(models.ParamValue.timestamp.desc())
    )

    if limit is not None:
        raw_query = raw_query.limit(limit)

    if offset is not None:
        raw_query = raw_query.offset(offset)

    return raw_query.all()