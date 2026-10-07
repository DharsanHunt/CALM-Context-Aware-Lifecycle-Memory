"""
calm.adapters.real_os — Production Real Host Operating System & Process Telemetry Adapter.
Bridges CALM from simulated memory models to live OS process management, page fault tracking,
real working-set trimming (psapi.EmptyWorkingSet), and thread priority scheduling.
"""

import os
import sys
import time
import ctypes
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from calm.models.app_state import LifecycleState


# Windows NT Priority Class Constants
PRIORITY_IDLE = 0x00000040          # IDLE_PRIORITY_CLASS (Archived / Deep Background)
PRIORITY_BELOW_NORMAL = 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS (Compressed)
PRIORITY_NORMAL = 0x00000020        # NORMAL_PRIORITY_CLASS (Cached resident)
PRIORITY_ABOVE_NORMAL = 0x00008000  # ABOVE_NORMAL_PRIORITY_CLASS (Prewarmed)
PRIORITY_HIGH = 0x00000080          # HIGH_PRIORITY_CLASS (Active foreground)

PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_INFORMATION = 0x0200
PROCESS_VM_READ = 0x0010
PROCESS_ALL_ACCESS = 0x1F0FFF


@dataclass
class RealProcessTelemetry:
    pid: int
    name: str
    rss_mb: float
    wset_mb: float
    peak_wset_mb: float
    private_mb: float
    vms_mb: float
    page_faults: int
    cpu_percent: float
    num_threads: int
    status: str
    priority_class: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "rss_mb": round(self.rss_mb, 2),
            "wset_mb": round(self.wset_mb, 2),
            "peak_wset_mb": round(self.peak_wset_mb, 2),
            "private_mb": round(self.private_mb, 2),
            "vms_mb": round(self.vms_mb, 2),
            "page_faults": self.page_faults,
            "cpu_percent": round(self.cpu_percent, 1),
            "num_threads": self.num_threads,
            "status": self.status,
            "priority_class": self.priority_class,
            "timestamp": self.timestamp,
        }


@dataclass
class HostSystemMemory:
    total_mb: float
    available_mb: float
    used_mb: float
    free_mb: float
    percent_used: float
    pressure_level: str  # LOW, MODERATE, HIGH, CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mb": round(self.total_mb, 1),
            "available_mb": round(self.available_mb, 1),
            "used_mb": round(self.used_mb, 1),
            "free_mb": round(self.free_mb, 1),
            "percent_used": round(self.percent_used, 1),
            "pressure_level": self.pressure_level,
        }


class RealOSTelemetryAdapter:
    """
    Production OS controller interfacing with kernel memory APIs,
    working set trimming, and dynamic process scheduler priority adjustment.
    """

    def __init__(self, target_process_names: Optional[List[str]] = None):
        self.target_names = [n.lower() for n in (target_process_names or [
            "chrome.exe", "spotify.exe", "code.exe", "python.exe", "msedge.exe",
            "discord.exe", "slack.exe", "whatsapp.exe", "antigravity.exe",
            "chrome", "spotify", "code", "python", "node"
        ])]

    def get_host_memory(self) -> HostSystemMemory:
        """Reads real physical system RAM statistics."""
        if not PSUTIL_AVAILABLE:
            return HostSystemMemory(8192.0, 4096.0, 4096.0, 4096.0, 50.0, "MODERATE")

        mem = psutil.virtual_memory()
        total_mb = mem.total / (1024 * 1024)
        avail_mb = mem.available / (1024 * 1024)
        used_mb = mem.used / (1024 * 1024)
        free_mb = mem.free / (1024 * 1024)
        pct = mem.percent

        if pct < 55.0:
            pressure = "LOW"
        elif pct < 75.0:
            pressure = "MODERATE"
        elif pct < 90.0:
            pressure = "HIGH"
        else:
            pressure = "CRITICAL"

        return HostSystemMemory(
            total_mb=total_mb,
            available_mb=avail_mb,
            used_mb=used_mb,
            free_mb=free_mb,
            percent_used=pct,
            pressure_level=pressure,
        )

    def scan_target_processes(self) -> List[RealProcessTelemetry]:
        """Scans running OS processes with complete working set & page fault metrics."""
        if not PSUTIL_AVAILABLE:
            return []

        results: List[RealProcessTelemetry] = []
        for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "num_threads", "status", "nice"]):
            try:
                p_info = proc.info
                p_name = (p_info["name"] or "").lower()
                mem_info = p_info.get("memory_info")
                if not mem_info:
                    continue

                rss_mb = mem_info.rss / (1024 * 1024)
                vms_mb = mem_info.vms / (1024 * 1024)
                wset_mb = getattr(mem_info, "wset", mem_info.rss) / (1024 * 1024)
                peak_wset_mb = getattr(mem_info, "peak_wset", mem_info.rss) / (1024 * 1024)
                private_mb = getattr(mem_info, "private", mem_info.rss) / (1024 * 1024)
                page_faults = getattr(mem_info, "num_page_faults", 0)

                # Map priority class
                nice_val = p_info.get("nice")
                if nice_val == 64 or nice_val == 19:
                    p_class = "IDLE"
                elif nice_val == 16384:
                    p_class = "BELOW_NORMAL"
                elif nice_val == 32 or nice_val == 0:
                    p_class = "NORMAL"
                elif nice_val == 32768:
                    p_class = "ABOVE_NORMAL"
                elif nice_val == 128 or nice_val == -10:
                    p_class = "HIGH"
                else:
                    p_class = str(nice_val)

                is_target = any(t in p_name for t in self.target_names)
                if is_target or rss_mb > 80.0:
                    results.append(
                        RealProcessTelemetry(
                            pid=p_info["pid"],
                            name=p_info["name"] or "unknown",
                            rss_mb=rss_mb,
                            wset_mb=wset_mb,
                            peak_wset_mb=peak_wset_mb,
                            private_mb=private_mb,
                            vms_mb=vms_mb,
                            page_faults=page_faults,
                            cpu_percent=p_info.get("cpu_percent") or 0.0,
                            num_threads=p_info.get("num_threads") or 1,
                            status=p_info.get("status") or "running",
                            priority_class=p_class,
                        )
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        results.sort(key=lambda x: x.rss_mb, reverse=True)
        return results

    def trim_process_working_set(self, pid: int) -> Dict[str, Any]:
        """
        Executes real OS working set trimming via EmptyWorkingSet.
        Flushes unreferenced working set pages to the OS standby page list.
        Measures exact physical RAM reclaimed in MB.
        """
        if sys.platform != "win32":
            return {"success": False, "pid": pid, "reason": "Working set trimming only supported on Windows"}

        if not PSUTIL_AVAILABLE:
            return {"success": False, "pid": pid, "reason": "psutil not available"}

        try:
            p = psutil.Process(pid)
            before_rss = p.memory_info().rss / (1024 * 1024)

            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not handle:
                return {"success": False, "pid": pid, "reason": "Access Denied (requires elevation for system tasks)"}

            # Call Windows PSAPI EmptyWorkingSet
            success = ctypes.windll.psapi.EmptyWorkingSet(handle)
            ctypes.windll.kernel32.CloseHandle(handle)

            if not success:
                return {"success": False, "pid": pid, "reason": "EmptyWorkingSet call failed"}

            time.sleep(0.05)
            after_rss = p.memory_info().rss / (1024 * 1024)
            reclaimed_mb = max(0.0, before_rss - after_rss)
            savings_pct = (reclaimed_mb / before_rss * 100) if before_rss > 0 else 0.0

            return {
                "success": True,
                "pid": pid,
                "name": p.name(),
                "before_rss_mb": round(before_rss, 2),
                "after_rss_mb": round(after_rss, 2),
                "reclaimed_mb": round(reclaimed_mb, 2),
                "reclaimed_pct": round(savings_pct, 1),
                "action": "EmptyWorkingSet",
                "timestamp": time.time(),
            }
        except psutil.NoSuchProcess:
            return {"success": False, "pid": pid, "reason": "Process no longer exists"}
        except psutil.AccessDenied:
            return {"success": False, "pid": pid, "reason": "Access Denied"}
        except Exception as e:
            return {"success": False, "pid": pid, "error": str(e)}

    def set_lifecycle_priority(self, pid: int, state: LifecycleState) -> Dict[str, Any]:
        """
        Adjusts Windows NT process priority class according to CALM Lifecycle State:
        - ACTIVE     -> HIGH_PRIORITY_CLASS (0x80)
        - CACHED     -> NORMAL_PRIORITY_CLASS (0x20)
        - COMPRESSED -> BELOW_NORMAL_PRIORITY_CLASS (0x4000)
        - ARCHIVED   -> IDLE_PRIORITY_CLASS (0x40)
        """
        if sys.platform != "win32":
            return {"success": False, "reason": "Priority scheduling adjustment currently Windows-specific"}

        state_priority_map = {
            LifecycleState.ACTIVE: PRIORITY_HIGH,
            LifecycleState.CACHED: PRIORITY_NORMAL,
            LifecycleState.COMPRESSED: PRIORITY_BELOW_NORMAL,
            LifecycleState.ARCHIVED: PRIORITY_IDLE,
        }

        target_class = state_priority_map.get(state, PRIORITY_NORMAL)

        try:
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
            if not handle:
                return {"success": False, "pid": pid, "reason": "Access Denied"}

            res = ctypes.windll.kernel32.SetPriorityClass(handle, target_class)
            ctypes.windll.kernel32.CloseHandle(handle)

            return {
                "success": bool(res),
                "pid": pid,
                "state": state.value,
                "priority_class_hex": hex(target_class),
            }
        except Exception as e:
            return {"success": False, "pid": pid, "error": str(e)}

    def trim_all_background_processes(
        self,
        exclude_pids: Optional[List[int]] = None,
        min_rss_mb: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Scans all target background applications and trims their working sets.
        Returns aggregate physical memory reclaimed across all processes.
        """
        excludes = set(exclude_pids or [os.getpid()])
        procs = self.scan_target_processes()

        total_reclaimed = 0.0
        trimmed_processes = []

        for p in procs:
            if p.pid in excludes or p.rss_mb < min_rss_mb:
                continue

            res = self.trim_process_working_set(p.pid)
            if res.get("success") and res.get("reclaimed_mb", 0) > 0.5:
                total_reclaimed += res["reclaimed_mb"]
                trimmed_processes.append(res)

        return {
            "total_reclaimed_mb": round(total_reclaimed, 2),
            "trimmed_process_count": len(trimmed_processes),
            "processes": trimmed_processes,
            "timestamp": time.time(),
        }
