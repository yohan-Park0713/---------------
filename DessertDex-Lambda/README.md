# DESSERT.DEX Lambda

`DessertDexCollection`은 수집률을 계산하고 특별 일러스트 해금 여부를 반환합니다. 개발 및 실행 기준은 Python 3.13입니다.

## 로컬 테스트

Windows PowerShell에서 `DessertDex-Lambda` 디렉터리로 이동한 뒤 실행합니다. `python --version`으로 Python 3.13이 선택됐는지 확인합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade 'pip>=26.2'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

테스트는 AWS 자격 증명 없이 실행됩니다. `src/lambda_function.py`가 이벤트와 응답을 처리하고, `src/validation.py`가 입력을 검증하며, `src/collection.py`가 수집률과 해금 여부를 계산합니다.

## 정적 분석과 의존성 점검

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache src tests
.\.venv\Scripts\python.exe -m bandit -c pyproject.toml -r src tests
.\.venv\Scripts\python.exe -m pip_audit --strict --aliases
```

Ruff와 Bandit은 소스와 테스트를 검사합니다. pip-audit는 PyPI 취약점 서비스에 연결해 가상환경에 설치된 직접·전이 의존성과 pip 자체를 검사합니다. 2026-11-22 점검 결과는 Ruff 0건, Bandit 낮음 25건, pip 업데이트 후 알려진 의존성 취약점 0건입니다. Bandit은 발견 사항으로 종료 코드 1을 반환합니다. [상세 점검 기록](docs/security.md#정적-분석과-의존성-점검)

## GitHub Actions CI

`DessertDex-Lambda`가 GitHub 저장소 루트인 구성을 기준으로 `.github/workflows/ci.yml`을 배치했습니다. 팀 모노레포로 올릴 경우 워크플로를 모노레포 루트의 `.github/workflows/`에 두고 작업 디렉터리를 `DessertDex-Lambda`로 지정합니다.

워크플로가 GitHub에 올라간 후 push와 Pull Request에서 **Lambda CI**가 실행됩니다. 저장소의 **Actions → Lambda CI**에서 실행 건과 검사 단계별 출력을 열 수 있습니다. Pull Request에서는 **Checks**에서 같은 결과를 확인합니다. GitHub 호스팅 러너에서 Python 3.13과 읽기 전용 저장소 권한으로 실행하며, AWS 자격 증명이 필요하지 않습니다.

앞의 로컬 설정을 마친 뒤 PowerShell에서 가상환경을 활성화하면 CI와 같은 명령으로 확인할 수 있습니다.

```powershell
. .\.venv\Scripts\Activate.ps1
python -m pytest
python -m ruff check --no-cache src tests
python -m bandit -c pyproject.toml -r src --exit-zero
python -m bandit -c pyproject.toml -r src --severity-level medium
python -m pip_audit --strict --aliases
```

Bandit의 첫 단계는 `src`의 모든 심각도를 출력합니다. 두 번째 단계는 같은 범위에 중간 또는 높은 경고가 있으면 실패합니다. 앞 절의 `src tests` 명령은 테스트 코드까지 검토할 때 사용하는 별도 검사입니다. [Bandit 검토 기록](docs/security.md#ci에서의-bandit-판정)

## 로컬 로그 확인


PowerShell에서 다음 명령을 실행하면 pytest가 성공 호출과 검증 실패의 로그 수준 및 구조화 필드를 표시합니다. 로컬 출력은 사람이 읽기 쉬운 텍스트 형식입니다.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_logging.py -k 'success_log or validation_warning' --log-cli-level=INFO -o 'log_cli_format=%(levelname)s %(message)s request_id=%(request_id)s outcome=%(outcome)s error_code=%(error_code)s duration_ms=%(duration_ms).3f'
```

## CloudWatch 확인 절차

1. AWS에서 검증할 때 `DessertDexCollection`의 로그 형식을 **JSON**, 애플리케이션 로그 수준을 **INFO**로 설정합니다. Python `logging`의 `extra` 필드는 Lambda가 JSON 필드로 변환합니다. 기본 로그 그룹은 `/aws/lambda/DessertDexCollection`이며, 로그가 보이지 않으면 기존 실행 역할의 로그 쓰기 권한과 조회 계정의 권한을 확인합니다. [Python 로깅 설정](https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html) · [CloudWatch Logs 권한](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html)
2. 정상 이벤트 `{"total_desserts":2,"collected_desserts":1,"unlock_threshold":50}`와 검증 실패 이벤트 `{"total_desserts":0}`를 호출합니다. 각각 기존 `200`과 `400` 응답을 확인합니다.
3. CloudWatch Logs Insights에서 해당 로그 그룹과 호출 시간대를 선택하고 아래 쿼리를 실행합니다. 정상 호출은 `INFO / success`, 검증 실패는 `WARNING / validation_failed`로 표시되며 두 호출 모두 `request_id`와 숫자형 `duration_ms`로 추적할 수 있습니다. 성공의 `error_code`는 JSON에서 `null`이며, 실패 예시에서는 `INVALID_COLLECTION_DATA`입니다.

```text
fields @timestamp, level, request_id, outcome, error_code, duration_ms
| filter message = "Collection request completed"
| sort @timestamp desc
| limit 50
```

Lambda가 정상 반환한 `statusCode: 400`은 기본 `Errors` 지표에 집계되지 않습니다. 검증 실패를 집계하려면 위 필터에 `outcome = "validation_failed"` 조건을 추가하고 `stats count(*) as rejected_requests by error_code`를 사용합니다. [Lambda 오류 지표](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
