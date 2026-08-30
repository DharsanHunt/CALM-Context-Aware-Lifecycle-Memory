"""
calm.storage.compression — Real payload compression engine with benchmarking.
Supports real byte compression (zlib/gzip) for Agent mode and calibrated models for Mobile mode.
"""

import time
import zlib
import json
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class CompressionResult:
    """Quantitative measurement of compression performance."""
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    compression_time_ms: float
    decompression_time_ms: float
    algorithm: str = "zlib"
    level: int = 6


class CompressionEngine:
    """
    Executes actual compression on memory payloads (JSON / strings / objects).
    Tracks original size, compressed size, ratio, and precise processing latencies.
    """

    def __init__(self, level: int = 6):
        self.level = level

    def compress_payload(self, content: Any) -> Tuple[bytes, CompressionResult]:
        """
        Serializes and compresses content payload using zlib.
        Returns (compressed_bytes, CompressionResult).
        """
        # 1. Serialize content to UTF-8 bytes
        if isinstance(content, bytes):
            raw_bytes = content
        elif isinstance(content, str):
            raw_bytes = content.encode("utf-8")
        else:
            raw_bytes = json.dumps(content).encode("utf-8")

        orig_len = len(raw_bytes)

        # 2. Compress and measure time
        t0 = time.perf_counter()
        compressed = zlib.compress(raw_bytes, level=self.level)
        t_compress = (time.perf_counter() - t0) * 1000.0  # ms

        comp_len = len(compressed)
        ratio = comp_len / float(orig_len) if orig_len > 0 else 1.0

        # 3. Benchmark decompression
        t1 = time.perf_counter()
        _ = zlib.decompress(compressed)
        t_decompress = (time.perf_counter() - t1) * 1000.0  # ms

        result = CompressionResult(
            original_bytes=orig_len,
            compressed_bytes=comp_len,
            compression_ratio=round(ratio, 4),
            compression_time_ms=round(t_compress, 3),
            decompression_time_ms=round(t_decompress, 3),
            algorithm="zlib",
            level=self.level,
        )
        return compressed, result

    def decompress_payload(self, compressed_bytes: bytes, as_json: bool = False) -> Any:
        """Decompresses byte payload back to original representation."""
        decompressed_raw = zlib.decompress(compressed_bytes)
        if as_json:
            return json.loads(decompressed_raw.decode("utf-8"))
        try:
            return decompressed_raw.decode("utf-8")
        except UnicodeDecodeError:
            return decompressed_raw
