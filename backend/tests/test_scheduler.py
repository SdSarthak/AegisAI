from app.tasks.scheduler import scheduler


def test_scheduler_exists():
    assert scheduler is not None