from unittest.mock import patch
from subprocess import CompletedProcess
from scripts.run_etl import main


# ETL 성공 + 품질 검사 성공
@patch("scripts.run_etl.subprocess.run")
def test_etl_and_quality_success(mock_run):
    mock_run.side_effect = [
        CompletedProcess([], 0, "ETL success", ""),
        CompletedProcess([], 0, "Quality PASS", "")
    ]

    assert main() == 0
    assert mock_run.call_count == 2


# ETL 실패 → 품질 검사 실행하지 않음
@patch("scripts.run_etl.subprocess.run")
def test_etl_failure_skips_quality(mock_run):
    mock_run.return_value = CompletedProcess(
        [], 1, "", "ETL failed"
    )

    assert main() == 1
    assert mock_run.call_count == 1


# ETL 성공 + 품질 검사 실패
@patch("scripts.run_etl.subprocess.run")
def test_quality_failure(mock_run):
    mock_run.side_effect = [
        CompletedProcess([], 0, "ETL success", ""),
        CompletedProcess([], 1, "Quality FAIL", "")
    ]

    assert main() == 1
    assert mock_run.call_count == 2

