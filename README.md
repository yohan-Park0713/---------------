# DESSERT.DEX Lambda

`DessertDexCollection`은 수집률을 계산하고 특별 일러스트 해금 여부를 반환합니다. 개발 및 실행 기준은 Python 3.13입니다.

## 개발 성과 및 검증 결과

계산 로직과 입력 검증을 Lambda 핸들러에서 분리하고, 기존 호출 계약을 유지하면서 비정상 이벤트와 과도한 정수 입력을 처리하도록 보강했습니다. 요청 결과는 구조화 로그로 기록하며, GitHub Actions에서 테스트와 보안 점검을 자동 실행합니다.

| 검증 항목 | 결과 |
|---|---|
| 로컬 pytest | 69개 통과, 실패 0개 |
| Ruff | 오류 0건 |
| Bandit (`src`) | 낮음 1건, 중간·높음 0건 |
| pip-audit | 알려진 취약점 0건 |
| GitHub Actions | 실제 실행 성공, 26초 |
| AWS Lambda | Python 3.13, ARM64, ZIP 배포 성공 |
| AWS 독립 검증 | 기존 기능 회귀 6개와 추가 보안 테스트 4개 통과, 실패 0개 |
| CloudWatch | JSON 로그에서 정상 INFO와 비정상 WARNING 확인. Logs Insights 조회·필터·집계 검증 완료 |

EC2 및 S3와의 실제 팀 서비스 통합은 아직 수행하지 않았습니다. [AWS 배포 환경, 검증 결과 및 재현 쿼리](docs/aws-validation.md)

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

## CloudWatch 검증

실제 AWS 검증에서 정상 요청의 CloudWatch JSON 로그에는 `error_code`가 생략됐고, 비정상 요청에서는 `INVALID_INPUT_TYPE`을 확인했습니다. [CloudWatch 설정과 Logs Insights 쿼리 4개](docs/aws-validation.md#cloudwatch-설정과-관측-결과)
