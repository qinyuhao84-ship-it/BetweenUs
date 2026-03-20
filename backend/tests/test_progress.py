from app.services.progress import ProgressService


def test_progress_is_monotonic_and_reaches_completion():
    service = ProgressService()
    session_id = "s-1"

    p1 = service.start(session_id)
    p2 = service.advance(session_id, "transcribing", 35)
    p3 = service.advance(session_id, "analyzing", 70)
    p4 = service.advance(session_id, "rendering", 95)
    p5 = service.complete(session_id)

    assert p1.percent == 5
    assert p2.percent == 35
    assert p3.percent == 70
    assert p4.percent == 95
    assert p5.percent == 100
    assert p5.stage == "completed"


def test_progress_does_not_go_backward():
    service = ProgressService()
    session_id = "s-2"

    service.start(session_id)
    service.advance(session_id, "analyzing", 70)
    p = service.advance(session_id, "transcribing", 20)

    assert p.percent == 70
    assert p.stage == "analyzing"
