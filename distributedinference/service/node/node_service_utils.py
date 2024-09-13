from uuid import UUID

from distributedinference.service import error_responses


def parse_node_uid(node_id: str) -> UUID:
    try:
        return UUID(node_id)
    except ValueError:
        raise error_responses.ValidationTypeError("Error, node_id is not a valid UUID")
    except TypeError:
        raise error_responses.ValidationTypeError("Error, node_id is not a valid type")
    except Exception:
        raise error_responses.ValidationTypeError("Failed to process node_id")
