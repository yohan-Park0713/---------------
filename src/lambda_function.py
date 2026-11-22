import json
import logging
from time import perf_counter

from collection import calculate_collection
from validation import validate_collection

logger = logging.getLogger(__name__)
VALIDATION_ERROR_CODES = {
    "Invalid input type": "INVALID_INPUT_TYPE",
    "Invalid collection data": "INVALID_COLLECTION_DATA",
    "Invalid unlock threshold": "INVALID_UNLOCK_THRESHOLD",
}


def _log_completion(context, started_at: float, error_code: str | None = None) -> None:
    try:
        request_id = getattr(context, "aws_request_id", None)
        rejected = error_code is not None
        logger.log(
            logging.WARNING if rejected else logging.INFO,
            "Collection request completed",
            extra={
                "request_id": request_id if isinstance(request_id, str) else None,
                "outcome": "validation_failed" if rejected else "success",
                "error_code": error_code,
                "duration_ms": (perf_counter() - started_at) * 1000,
            },
        )
    except Exception:
        # Telemetry failures must not change the Lambda response.
        pass


def invalid_request(message: str) -> dict:
    return {"statusCode": 400, "body": json.dumps({"message": message})}


def lambda_handler(event, context):
    started_at = perf_counter()
    if not isinstance(event, dict):
        _log_completion(context, started_at, "INVALID_INPUT_TYPE")
        return invalid_request("Invalid input type")

    total = event.get("total_desserts", 0)
    collected = event.get("collected_desserts", 0)
    threshold = event.get("unlock_threshold", 100)

    error = validate_collection(total, collected, threshold)
    if error is not None:
        _log_completion(context, started_at, VALIDATION_ERROR_CODES.get(error, "VALIDATION_FAILED"))
        return invalid_request(error)

    rate, unlocked = calculate_collection(total, collected, threshold)
    response = {
        "statusCode": 200,
        "body": json.dumps({
            "collection_rate": rate,
            "special_illustration_unlocked": unlocked,
        }),
    }
    _log_completion(context, started_at)
    return response
