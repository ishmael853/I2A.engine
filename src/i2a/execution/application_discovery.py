
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveredApplication:
    """Represents an application discovered on the system."""

    name: str
    executable: str


class ApplicationDiscovery:
    """Discovers launchable applications from Start Menu and PATH."""

    START_MENU_LOCATIONS = [
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs",
        Path(os.environ.get("PROGRAMDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs",
    ]

    BLOCKED_TERMS = (
        "uninstall",
        "installer",
        "redistributable",
        "runtime",
        "setup.exe",
        "package cache",
        "officeclicktorun",
        "clicktorun",
    )

    BLOCKED_PATH_TERMS = (
        "\\package cache\\",
        "\\installer\\",
        "\\installers\\",
        "\\redist\\",
        "\\redistributable\\",
        "\\runtime\\",
    )

    BLOCKED_EXECUTABLES = {
        "uninstall.exe",
        "unins000.exe",
        "unins001.exe",
        "msiexec.exe",
        "wintoast.exe",
        "setup.exe",
        "installer.exe",
        "pg_ctl.exe",
    }

    def discover(self) -> list[DiscoveredApplication]:
        """Discover applications with verified executable targets."""

        applications: dict[str, DiscoveredApplication] = {}

        self._discover_start_menu(applications)
        self._discover_path(applications)

        return sorted(
            applications.values(),
            key=lambda application: application.name.lower(),
        )

    def _add_application(
        self,
        applications: dict[str, DiscoveredApplication],
        name: str,
        executable: str,
    ) -> None:
        """Add a valid executable while avoiding duplicate paths."""

        if not isinstance(name, str) or not isinstance(executable, str):
            return

        name = name.strip()
        executable = executable.strip().strip('"')

        if not name or not executable:
            return

        if any(
            term in name.lower()
            for term in self.BLOCKED_TERMS
        ):
            return

        path = Path(executable).expanduser()

        if (
            not path.is_absolute()
            or not path.is_file()
            or path.suffix.lower() != ".exe"
        ):
            return

        if path.name.lower() in self.BLOCKED_EXECUTABLES:
            return

        normalized_path = os.path.normcase(str(path.resolve()))

        if any(
            term in normalized_path
            for term in self.BLOCKED_PATH_TERMS
        ):
            return

        applications.setdefault(
            normalized_path,
            DiscoveredApplication(
                name=name,
                executable=str(path.resolve()),
            ),
        )

    def _discover_start_menu(
        self,
        applications: dict[str, DiscoveredApplication],
    ) -> None:
        """Discover executable targets from Start Menu shortcuts."""

        try:
            from win32com.client import Dispatch

            shell = Dispatch("WScript.Shell")
        except Exception:
            return

        for location in self.START_MENU_LOCATIONS:
            if not location.is_dir():
                continue

            for shortcut in location.rglob("*.lnk"):
                try:
                    name = shortcut.stem.strip()
                    shortcut_info = shell.CreateShortcut(str(shortcut))
                    target = shortcut_info.TargetPath

                    if not target:
                        continue

                    self._add_application(
                        applications,
                        name,
                        target,
                    )

                except Exception:
                    continue

    def _discover_path(
        self,
        applications: dict[str, DiscoveredApplication],
    ) -> None:
        """Discover supported executable commands available on PATH."""

        candidates = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
        }

        for name, executable in candidates.items():
            path = shutil.which(executable)

            if path:
                self._add_application(
                    applications,
                    name,
                    os.path.abspath(path),
                )

    def find(
        self,
        application_name: str,
    ) -> DiscoveredApplication | None:
        """Find an application by its name."""

        if not isinstance(application_name, str):
            return None

        requested_name = application_name.strip().lower()

        if not requested_name:
            return None

        for application in self.discover():
            if application.name.strip().lower() == requested_name:
                return application

        return None
