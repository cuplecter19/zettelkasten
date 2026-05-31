# zettelkasten

PySide6 기반 제텔카스텐(Zettelkasten) 데스크톱 앱입니다.

## VSCode 실시간 개발 환경

VSCode에서 코드를 저장할 때마다 앱이 자동으로 재시작되는 핫 리로드 환경을
제공합니다. 빌드와 실시간 확인은 모두 VSCode 안에서 단축키로 수행할 수 있습니다.

### 1. 사전 준비

먼저 의존성을 설치합니다. 개발 전용 패키지(`watchdog`, `pytest`, `pytest-qt`)가
포함되어 있습니다.

```bash
pip install -r requirements.txt
```

VSCode에는 다음 확장이 설치되어 있어야 합니다.

- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Python Debugger** (ms-python.debugpy)

VSCode에서 프로젝트 루트 폴더(`zettelkasten/`)를 열고, 명령 팔레트
(`Ctrl+Shift+P`)에서 **Python: Select Interpreter** 를 실행해 의존성을 설치한
인터프리터(또는 가상환경)를 선택합니다. `.vscode/` 폴더의 설정은 이미
저장소에 포함되어 있어 추가 설정 없이 바로 사용할 수 있습니다.

### 2. 빌드 및 실시간 확인 (핫 리로드)

`Ctrl+Shift+B` 를 누르면 기본 빌드 작업인 **"앱 실행 (핫 리로드)"** 가
실행됩니다. 이 작업은 `dev_runner.py` 를 통해 `main.py` 를 띄우고, 프로젝트의
`.py` 파일이 저장될 때마다 앱을 자동으로 재시작합니다.

1. `Ctrl+Shift+B` 로 핫 리로드 실행기를 시작합니다.
2. 소스 코드를 수정하고 저장(`Ctrl+S`)합니다.
3. 터미널 패널의 `dev_runner` 에 "변경 감지 → 재시작" 로그가 출력되며 앱이
   새 코드로 다시 실행됩니다.
4. 종료하려면 해당 터미널에서 `Ctrl+C` 를 누릅니다.

연속 저장 시 과도한 재시작을 막기 위해 1초의 디바운스(debounce) 간격이
적용됩니다(`dev_runner.py` 의 `DEBOUNCE_SECONDS`).

### 3. 특정 패널만 단독으로 확인

전체 앱을 실행하지 않고 개별 패널/위젯만 빠르게 확인할 수 있습니다.
`ui/panels/` 와 `ui/widgets/` 의 각 파일 하단에는 단독 실행 블록
(`if __name__ == "__main__":`)이 추가되어 있습니다.

1. 확인할 파일(예: `ui/panels/editor_panel.py`)을 엽니다.
2. `F5` 를 누른 뒤 **"현재 파일 단독 실행"** 구성을 선택합니다.
3. 해당 위젯만 독립 창으로 표시됩니다.

> 단독 실행 시에는 DB 연결이 없으므로, DB가 필요한 패널은 단독 실행 블록 안에서
> `init_db()` 를 호출하거나 목(mock) 데이터를 주입해야 합니다.

### 4. 전체 앱 디버그 실행

중단점을 사용해 전체 앱을 디버깅하려면 `F5` 를 누른 뒤
**"전체 앱 실행 (디버그)"** 구성을 선택합니다. 통합 터미널에서 `main.py` 가
디버그 모드로 실행됩니다.

### 5. 테스트 실행

- `Ctrl+Shift+B` 후 **"테스트 실행 (전체)"** 작업을 선택하면 `pytest` 가
  실행됩니다.
- 또는 VSCode 사이드바의 **테스트(Testing)** 탭에서 개별 테스트를 실행할 수
  있습니다. (`.vscode/settings.json` 에 pytest 자동 인식이 설정되어 있습니다.)

헤드리스(GUI 없는) 환경에서 터미널로 직접 실행할 경우:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

### 6. Qt Designer 로 UI 편집

`Ctrl+Shift+B` 후 **"Qt Designer 열기"** 작업을 선택하면 `pyside6-designer` 가
실행되어 UI 레이아웃을 시각적으로 편집할 수 있습니다.

### 작업 유형별 실행 방법 요약

| 작업 | 실행 방법 |
|------|-----------|
| 전체 앱 + 자동 재시작 | `Ctrl+Shift+B` → "앱 실행 (핫 리로드)" |
| 특정 패널만 확인 | 해당 `.py` 파일 열고 `F5` → "현재 파일 단독 실행" |
| 전체 앱 디버그 | `F5` → "전체 앱 실행 (디버그)" |
| 테스트 전체 실행 | `Ctrl+Shift+B` → "테스트 실행 (전체)", 또는 테스트 탭 |
| UI 레이아웃 편집 | `Ctrl+Shift+B` → "Qt Designer 열기" |

### 주의사항

1. `dev_runner.py` 는 **개발 중에만** 사용하며, 배포 시 포함하지 않습니다.
2. 각 UI 파일의 단독 실행 블록은 DB 연결이 없으므로, DB가 필요한 패널은 블록
   안에서 `init_db()` 호출 또는 목 데이터 주입이 필요합니다.
3. `watchdog` 은 macOS 에서 `FSEventsObserver`, Windows 에서
   `ReadDirectoryChangesW` 를 자동 선택하므로 OS별 별도 설정은 필요 없습니다.
4. `.vscode/` 폴더는 팀 공유 설정이므로 `.gitignore` 에 추가하지 않는 것을
   권장합니다.