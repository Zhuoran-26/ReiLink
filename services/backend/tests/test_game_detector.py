from app.modules.game_detector.detector import EldenRingDetector


def test_running_when_process_exists():
    status = EldenRingDetector(process_iter=[{"name": "eldenring.exe"}], system_name="Windows").get_status()
    assert status.status == "running"
    assert status.game_id == "elden_ring"


def test_idle_when_process_missing():
    status = EldenRingDetector(process_iter=[{"name": "steam.exe"}], system_name="Windows").get_status()
    assert status.status == "idle"
    assert status.game_id is None


def test_non_windows_does_not_crash():
    status = EldenRingDetector(process_iter=[{"name": "eldenring.exe"}], system_name="Darwin").get_status()
    assert status.status == "idle"

