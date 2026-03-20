from typing import Literal

PlatformStr = Literal["android", "ios", "windows", "macos"]
WinCatStr = Literal["game", "daw", "adobe", "software"]
AndroidCatStr = Literal["app"]
IOSCatStr = Literal["app"]
MacOSCatStr = Literal["software", "daw"]
CatStr = WinCatStr | AndroidCatStr | IOSCatStr | MacOSCatStr
StatusStr = Literal["pending", "examining", "testing", "completed", "rejected", "cancelled"]