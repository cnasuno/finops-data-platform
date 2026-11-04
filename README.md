
# FinOps Data Platform

금융거래 데이터를 생성하고 검증하여 MySQL에 적재하는 ETL 파이프라인 프로젝트.

## Tech Stack
- Python 3.12
- MySQL 8.4
- WSL Ubuntu
- Git / GitHub

## Pipeline
CSV → Python Validation → MySQL

## Database
- accounts: 계좌 정보
- transactions: 정상 거래
- pipeline_runs: 실행 이력 및 처리 건수
- rejected_transactions: 검증 실패 거래

## Project Status
- [x] Database schema design
- [x] ERD
- [ ] CSV data generation
- [ ] Validation and loading
- [ ] Data quality tests

## ERD
See [ERD](docs/erd.md).
