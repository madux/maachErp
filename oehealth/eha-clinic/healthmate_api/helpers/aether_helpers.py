import json
import hashlib
from typing import (Any, List, Mapping)


# Aether Messages have some required metadata in order to validate and process them
def structure_message(
    hashed_id: str,
    schemadecorator_id: str,
    body: Mapping[str, Any]
    )-> Mapping[str, Any]:
    return {
        'id': hashed_id,
        'status': 'Publishable',
        'schemadecorator': schemadecorator_id,
        'payload': dict(**body, **{'id': hashed_id})
    }

# Simple hashing function to make an internal ID Aether compliant
def id_hash(internal_uuid: str, size=36):
    return hashlib.md5(internal_uuid.encode('utf-8')).hexdigest()[:size]

# Convenience function to turn a list of internal records into a ready payload.
def prepare_many(
    records: List[Mapping[str, Any]],
    id_field_name: str,
    schemadecorator_id: str
) -> List[Mapping[str, Any]]:
    return [
        structure_message(
            id_hash(
                msg.get(id_field_name)
            ),
            schemadecorator_id,
            msg
        ) for msg in records
    ]
