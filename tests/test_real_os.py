"""
tests.test_real_os — Unit tests for RealOSTelemetryAdapter and host system memory.
"""

import unittest
from calm.adapters.real_os import RealOSTelemetryAdapter, HostSystemMemory


class TestRealOSTelemetry(unittest.TestCase):

    def setUp(self):
        self.adapter = RealOSTelemetryAdapter()

    def test_get_host_memory(self):
        mem = self.adapter.get_host_memory()
        self.assertIsInstance(mem, HostSystemMemory)
        self.assertGreater(mem.total_mb, 0)
        self.assertGreater(mem.available_mb, 0)
        self.assertIn(mem.pressure_level, ["LOW", "MODERATE", "HIGH", "CRITICAL"])

    def test_scan_target_processes(self):
        procs = self.adapter.scan_target_processes()
        self.assertIsInstance(procs, list)
        if procs:
            p = procs[0]
            self.assertGreater(p.pid, 0)
            self.assertIsNotNone(p.name)
            self.assertGreaterEqual(p.rss_mb, 0)


if __name__ == "__main__":
    unittest.main()
