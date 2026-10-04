"""Command-line daily report runner.

Run with: python -m app.daily_job
Use Windows Task Scheduler or a hosted cron service to invoke this once a day.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .main import DEFAULT_DATABASE
from .models import Base
from .operations import save_daily_report


def run() -> None:
    DEFAULT_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DEFAULT_DATABASE.as_posix()}")
    try:
        Base.metadata.create_all(engine)
        with sessionmaker(bind=engine)() as session:
            report = save_daily_report(session)
            print(f"Saved daily report {report.report_date} (id {report.id}).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    run()
