# Lambda 호출 계약

핸들러 진입점은 `lambda_function.lambda_handler`입니다. 직접 호출 이벤트는 JSON 객체여야 하며 최상위에서 다음 값을 읽습니다.

| 필드 | 누락 시 기본값 | 조건 |
|---|---:|---|
| `total_desserts` | 0 | 1 이상 9,007,199,254,740,991 이하인 정수 |
| `collected_desserts` | 0 | 0 이상 전체 개수 이하인 정수 |
| `unlock_threshold` | 100 | 0 이상 100 이하인 정수 |

응답은 `statusCode`와 JSON 문자열 `body`를 담습니다. 성공 시 `statusCode`는 200이며, 본문에는 `collection_rate`와 `special_illustration_unlocked`가 들어갑니다. 해금 조건은 소수점 둘째 자리까지 반올림한 수집률이 기준값 이상인 경우입니다.

검증 실패의 `statusCode`는 400이며, 본문의 `message`는 아래 순서로 결정됩니다.

1. 이벤트가 객체가 아니거나 필드 타입이 정수가 아니면 `Invalid input type`입니다. 불리언도 이 오류에 해당합니다.
2. 전체 개수 또는 수집 개수 범위 위반은 `Invalid collection data`
3. 해금 기준 범위 위반은 `Invalid unlock threshold`
