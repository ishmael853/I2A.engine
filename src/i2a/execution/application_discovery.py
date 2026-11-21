import os
import shutil
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveredApplication:
    """Represents an application discovered on the system."""

    name: str
    executable: str


class ApplicationDiscovery:
    """Discovers applications from Windows Start Menu, registry, and PATH."""

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

    REGISTRY_LOCATIONS = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ]

    BLOCKED_TERMS = (
        "uninstall",
        "installer",
        "redistributable",
        "runtime",
        "setup.exe",
    )

    def discover(self) -> list[DiscoveredApplication]:
        """Discover applications from all supported Windows sources."""

        applications: dict[str, DiscoveredApplication] = {}

        self._discover_start_menu(applications)
        self._discover_registry(applications)
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
        """Add a valid executable while avoiding duplicates."""

        if not isinstance(name, str) or not isinstance(executable, str):
            return

        name = name.strip()
        executable = executable.strip().strip('"')

        if not name or not executable:
            return

        path = Path(executable).expanduser()

        if (
            not path.is_absolute()
            or not path.is_file()
            or path.suffix.lower() != ".exe"
        ):
            return

        key = os.path.normcase(str(path.resolve()))

        applications.setdefault(
            key,
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
        except ImportError:
            return

        shell = Dispatch("WScript.Shell")

        for location in self.START_MENU_LOCATIONS:
            if not location.is_dir():
                continue

            for shortcut in location.rglob("*.lnk"):
                try:
                    shortcut_info = shell.CreateShortcut(str(shortcut))
                    target = shortcut_info.TargetPath

                    self._add_application(
                        applications,
                        shortcut.stem,
                        target,
                    )
                except Exception:
                    continue

    def _discover_registry(
        self,
        applications: dict[str, DiscoveredApplication],
    ) -> None:
        """Discover launchable applications from Windows registry entries."""

        if sys.platform != "win32":
            return

        for hive, registry_path in self.REGISTRY_LOCATIONS:
            try:
                with winreg.OpenKey(hive, registry_path) as root:
                    subkey_count = winreg.QueryInfoKey(root)[0]

                    for index in range(subkey_count):
                        try:
                            subkey_name = winreg.EnumKey(root, index)

                            with winreg.OpenKey(
                                root,
                                subkey_name,
                            ) as subkey:
                                try:
                                    name = winreg.QueryValueEx(
                                        subkey,
                                        "DisplayName",
                                    )[0]
                                except OSError:
                                    continue

                                try:
                                    executable = winreg.QueryValueEx(
                                        subkey,
                                        "DisplayIcon",
                                    )[0]
                                except OSError:
                                    continue

                                executable = executable.split(",")[0]
                                executable = executable.strip().strip('"')

                                lower_name = str(name).lower()
                                lower_executable = executable.lower()

                                if (
                                    any(
                                        term in lower_name
                                        for term in self.BLOCKED_TERMS
                                    )
                                    or any(
                                        term in lower_executable
                                        for term in self.BLOCKED_TERMS
                                    )
                                ):
                                    continue

                                self._add_application(
                                    applications,
                                    name,
                                    executable,
                                )

                        except OSError:
                            continue

            except OSError:
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