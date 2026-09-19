"""system_info MCP tool — stdlib-only host/platform facts.

No `psutil` dependency: uptime and richer metrics aren't worth adding a
package for in a reference/demo tool.
"""

from __future__ import annotations

import os
import platform


def system_info() -> str:
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    return "\n".join(f"{key}: {value}" for key, value in info.items())
