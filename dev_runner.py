"""
dev_runner.py
개발용 핫 리로드 실행기.
.py 파일 변경 저장 시 main.py를 자동으로 재시작합니다.
프로덕션 환경에서는 사용하지 마십시오.
"""

import subprocess
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


WATCH_DIR = Path(__file__).parent
ENTRY_POINT = WATCH_DIR / "main.py"
DEBOUNCE_SECONDS = 1.0  # 연속 저장 시 재시작 간격


class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self._last_restart = 0.0
        self.start_app()

    def start_app(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        print(f"\n[dev_runner] 앱 시작: {ENTRY_POINT}")
        self.process = subprocess.Popen(
            [sys.executable, str(ENTRY_POINT)],
            cwd=str(WATCH_DIR),
        )

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return
        # dev_runner.py 자신의 변경은 무시
        if Path(event.src_path).name == "dev_runner.py":
            return

        now = time.time()
        if now - self._last_restart < DEBOUNCE_SECONDS:
            return
        self._last_restart = now

        rel = Path(event.src_path).relative_to(WATCH_DIR)
        print(f"[dev_runner] 변경 감지: {rel} → 재시작")
        self.start_app()


def main():
    handler = RestartHandler()
    observer = Observer()
    observer.schedule(handler, path=str(WATCH_DIR), recursive=True)
    observer.start()
    print("[dev_runner] 감시 시작. 종료하려면 Ctrl+C 를 누르세요.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[dev_runner] 종료 중...")
        observer.stop()
        if handler.process and handler.process.poll() is None:
            handler.process.terminate()
    observer.join()


if __name__ == "__main__":
    main()
