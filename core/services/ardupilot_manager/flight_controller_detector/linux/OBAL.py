import platform
from typing import Any, List

from commonwealth.utils.commands import load_file
from elftools.elf.elffile import ELFFile

from flight_controller_detector.linux.linux_boards import LinuxFlightController
from typedefs import Platform, Serial


class OBAL(LinuxFlightController):
    manufacturer = "HefnySco"

    def __init__(self, **data: Any) -> None:
        name = "OBAL"
        plat = Platform.OBAL
        if platform.machine() == "aarch64":
            # edge case for 64-bit kernel on 32-bit userland...
            # let's check the arch for /usr/bin/ls
            with open("/usr/bin/ls", "rb") as f:
                elf_file = ELFFile(f)
                firm_arch = elf_file.get_machine_arch()
                # from https://github.com/eliben/pyelftools/blob/main/elftools/elf/elffile.py#L513
                if firm_arch == "AArch64":
                    raise RuntimeError("64-bit not currently supported")
        super().__init__(**data, name=name, platform=plat)

    def is_pi5(self) -> bool:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            return "Raspberry Pi 5" in f.read()

    def detect(self) -> bool:
        return False

    def get_serials(self) -> List[Serial]:
        raise NotImplementedError


class OBALPi4(OBAL):
    devices = {
        "ADS1115": (0x48, 1),
        "PCA9685": (0x40, 1),
    }

    def get_serials(self) -> List[Serial]:
        release = "Bullseye"
        os_release = load_file("/etc/os-release")
        if "bookworm" in os_release.lower():
            release = "Bookworm"

        match release:
            case "Bullseye":
                return [
                    Serial(port="C", endpoint="/dev/ttyS0"),
                    Serial(port="B", endpoint="/dev/ttyAMA1"),
                    Serial(port="E", endpoint="/dev/ttyAMA2"),
                    Serial(port="F", endpoint="/dev/ttyAMA3"),
                ]
            case "Bookworm":
                return [
                    Serial(port="C", endpoint="/dev/ttyS0"),
                    Serial(port="B", endpoint="/dev/ttyAMA3"),
                    Serial(port="E", endpoint="/dev/ttyAMA4"),
                    Serial(port="F", endpoint="/dev/ttyAMA5"),
                ]
        raise RuntimeError("Unknown release, unable to map ports")

    def detect(self) -> bool:
        if self.is_pi5():
            return False
        return all(self.check_for_i2c_device(bus, address) for address, bus in self.devices.values())
