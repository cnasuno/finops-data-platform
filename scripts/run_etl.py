import subprocess
import sys
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 로그 디렉터리 생성
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 로그 설정
logging.basicConfig(
    filename=LOG_DIR / "etl.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def main():
    logging.info("ETL started")

    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "load.py")],
            cwd=BASE_DIR,
            check=False,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logging.info("ETL completed successfully")
            if result.stdout:
                logging.info("ETL output:\n%s", result.stdout)
        else:
            logging.error(
                "ETL failed (exit code: %s)",
                result.returncode
            )
            if result.stderr:
                logging.error("ETL error:\n%s", result.stderr)

        return result.returncode

    except Exception:
        logging.exception("Failed to execute ETL")
        return 1


if __name__ == "__main__":
    sys.exit(main())