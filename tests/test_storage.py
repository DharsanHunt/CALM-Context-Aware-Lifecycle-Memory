"""
Unit tests for CALM V2 Storage & Compression layer.
"""

import unittest
from calm.storage.compression import CompressionEngine
from calm.storage.cache import MemoryCachePool
from calm.storage.archive import ColdArchiveStore
from calm.models.memory_item import MemoryItem, ItemType
from calm.models.app_state import LifecycleState


class TestStorageAndCompression(unittest.TestCase):

    def setUp(self):
        self.compressor = CompressionEngine(level=6)

    def test_real_payload_compression(self):
        sample_text = "This is a detailed agent conversation context block. " * 50
        comp_bytes, result = self.compressor.compress_payload(sample_text)
        
        self.assertGreater(result.original_bytes, 0)
        self.assertLess(result.compressed_bytes, result.original_bytes)
        self.assertLess(result.compression_ratio, 0.50)  # Significant real compression
        self.assertGreaterEqual(result.compression_time_ms, 0.0)

        # Verify round-trip decompression
        decompressed = self.compressor.decompress_payload(comp_bytes)
        self.assertEqual(decompressed, sample_text)

    def test_memory_cache_pool(self):
        pool = MemoryCachePool(ram_limit_mb=2500)
        item = MemoryItem(id="doc_1", type=ItemType.DOCUMENT, raw_size_bytes=1000, state=LifecycleState.ACTIVE)
        pool.put(item)
        self.assertEqual(pool.get("doc_1"), item)
        self.assertEqual(pool.total_resident_bytes(), 1000)

    def test_cold_archive_store(self):
        store = ColdArchiveStore()
        item = MemoryItem(id="old_task", type=ItemType.TASK)
        store.archive(item)
        self.assertTrue(store.contains("old_task"))
        self.assertEqual(store.count(), 1)
        retrieved = store.retrieve("old_task")
        self.assertEqual(retrieved.id, "old_task")
        self.assertEqual(store.count(), 0)


if __name__ == "__main__":
    unittest.main()
