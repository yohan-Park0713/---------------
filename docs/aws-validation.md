# AWS Lambda 배포 및 독립 검증

이 문서는 AWS Academy Learner Lab에서 완료한 배포와 독립 검증 결과를 기록합니다.

## 배포 절차

1. 로컬에서 pytest를 통과한 소스로 `DessertDexCollection.zip`을 준비합니다. ZIP 루트에 `lambda_function.py`, `collection.py`, `validation.py`를 배치합니다.
2. Learner Lab의 Lambda 콘솔에서 기존 `DessertDexCollection`을 열고 코드 업로드 메뉴에서 ZIP 파일을 올립니다.
3. 함수의 패키지 유형 **ZIP**, 런타임 **Python 3.13**, 아키텍처 **ARM64**, 핸들러 `lambda_function.lambda_handler`를 확인합니다. [Python ZIP 패키지 배포](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
4. 테스트 이벤트로 함수를 직접 호출하고 반환 객체의 `statusCode`와 JSON 문자열 `body`를 [호출 계약](api-contract.md)과 비교합니다.

## AWS 테스트 결과

| 검증 | 통과 | 실패 |
|---|---:|---:|
| 기존 기능 회귀 | 6 | 0 |
| 추가 보안 테스트 | 4 | 0 |
| 합계 | 10 | 0 |

기존 회귀 범위는 수집률 계산, 해금 판단, 비정수 입력, 수집 개수 초과, 전체 개수 0, 해금 기준 범위 초과입니다. 추가 보안 테스트는 제공된 집계 결과를 기록했습니다.

## CloudWatch 설정과 관측 결과

함수 로그 형식은 **JSON**, 애플리케이션 로그 수준은 **INFO**를 사용합니다. 기본 로그 그룹을 사용하는 경우 CloudWatch에서 `/aws/lambda/DessertDexCollection`을 선택합니다. Python 표준 로깅의 구조화 필드는 Lambda가 JSON으로 변환합니다. [Lambda Python 로깅](https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html)

| 관측 | 수준 | `outcome` | `error_code` | `duration_ms` |
|---|---|---|---|---:|
| 정상 요청 | INFO | `success` | CloudWatch 로그에서 생략 | 0.100239 |
| 비정상 요청 | WARNING | `validation_failed` | `INVALID_INPUT_TYPE` | 0.005861 |

두 로그에서 `request_id`, `outcome`, `duration_ms`를 확인했습니다. 처리 시간은 핸들러 진입부터 완료 로그 직전까지의 애플리케이션 내부 측정값입니다. 정상과 비정상 표본이 각각 1건이므로 유형별 평균과 최대는 각각 그 단일 값과 같습니다. 성능이나 종단 간 응답 시간을 평가하려면 별도의 측정이 필요합니다.

## Logs Insights 재현 쿼리

CloudWatch Logs Insights에서 해당 로그 그룹과 검증 호출 시간대를 선택합니다. 아래 쿼리는 완료 메시지를 기준으로 애플리케이션 로그를 조회합니다. [Logs Insights 쿼리 문법](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)

### 1. 전체 애플리케이션 완료 로그

```text
fields @timestamp, level, request_id, outcome, error_code, duration_ms
| filter message = "Collection request completed"
| sort @timestamp desc
```

검증 결과는 2건입니다.

### 2. 비정상 요청 필터링

```text
fields @timestamp, level, request_id, outcome, error_code, duration_ms
| filter message = "Collection request completed" and outcome = "validation_failed"
| sort @timestamp desc
```

검증 결과는 1건입니다.

### 3. 오류 유형별 집계

```text
filter message = "Collection request completed" and outcome = "validation_failed"
| stats count(*) as requests by error_code
| sort requests desc
```

`INVALID_INPUT_TYPE`이 1건 집계됐습니다.

### 4. 요청 유형별 횟수와 평균·최대 처리 시간

```text
filter message = "Collection request completed"
| stats count(*) as requests, avg(duration_ms) as avg_duration_ms, max(duration_ms) as max_duration_ms by outcome
| sort outcome asc
```

| `outcome` | 횟수 | 평균(ms) | 최대(ms) |
|---|---:|---:|---:|
| `success` | 1 | 0.100239 | 0.100239 |
| `validation_failed` | 1 | 0.005861 | 0.005861 |

## 보안 검증과 한계

- 로컬 pytest는 69개 통과, Ruff는 0건, pip-audit는 검사 시점의 알려진 취약점 0건이었습니다. 운영 코드 Bandit 검사는 낮음 1건, 중간·높음 0건이었으며 GitHub Actions 실제 실행은 26초에 성공했습니다.
- Bandit의 낮음 `B110`은 로깅 장애에도 기존 응답을 유지하기 위한 예외 처리입니다. 로깅 장애가 발생하면 완료 로그가 유실될 수 있습니다. 애플리케이션 로그 정책은 입력 원문, 사용자 식별 정보 및 인증 정보를 기록 대상에서 제외합니다. [로그 보안 정책과 점검 기록](security.md)
- 함수가 정상 반환한 `statusCode: 400`은 Lambda 기본 `Errors` 지표에 집계되지 않습니다. 입력 거부 건수는 Logs Insights의 `validation_failed`로 확인합니다. [Lambda 오류 지표](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- 핸들러는 역직렬화된 이벤트를 받습니다. 본문 크기와 JSON 파싱 비용은 호출 경계에서 관리해야 하며, 실제 수집 기록과 입력 집계값의 일치 여부는 호출 서비스가 확인해야 합니다.
- 이번 AWS 검증은 Lambda 독립 호출 범위이며 EC2 및 S3와의 실제 팀 서비스 통합은 아직 수행하지 않았습니다.
