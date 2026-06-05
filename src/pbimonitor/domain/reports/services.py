from __future__ import annotations

import gzip
import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import imagehash
import numpy as np
from PIL import Image, ImageDraw

from pbimonitor.domain.reports.entities import DiffResult
from pbimonitor.exceptions import DiffComputationError


@dataclass(frozen=True)
class DiffPolicy:
    mse_threshold: float
    min_block_size: int
    max_depth: int
    draw_diff_image: bool = True


class ReportDiffService:
    def calculate_hash(self, image_path: Path) -> Optional[str]:
        try:
            with Image.open(image_path) as img:
                return str(imagehash.dhash(img))
        except Exception as exc:
            raise DiffComputationError(f"Could not calculate image hash for {image_path}") from exc

    def encode_delta(self, initial_path: Path, current_path: Path) -> bytes:
        try:
            initial_img = Image.open(initial_path).convert("RGB")
            current_img = Image.open(current_path).convert("RGB")
            if initial_img.size != current_img.size:
                current_img = current_img.resize(initial_img.size)
            initial = np.array(initial_img)
            current = np.array(current_img)
            delta = np.bitwise_xor(initial, current)
            buffer = io.BytesIO()
            np.save(buffer, delta)
            return gzip.compress(buffer.getvalue(), compresslevel=6)
        except Exception as exc:
            raise DiffComputationError("Could not encode XOR delta") from exc

    def decode_delta(self, initial_path: Path, compressed_delta: bytes) -> Image.Image:
        try:
            initial = np.array(Image.open(initial_path))
            decompressed = gzip.decompress(compressed_delta)
            buffer = io.BytesIO(decompressed)
            delta = np.load(buffer)
            restored = np.bitwise_xor(initial, delta)
            return Image.fromarray(restored.astype(np.uint8))
        except Exception as exc:
            raise DiffComputationError("Could not decode XOR delta") from exc

    def compare(
        self,
        report_id: str,
        baseline_path: Path,
        current_path: Path,
        diff_output_path: Optional[Path],
        policy: DiffPolicy,
        *,
        delta_encoding_baseline_path: Optional[Path] = None,
    ) -> DiffResult:
        try:
            started = time.monotonic()
            baseline_img = Image.open(baseline_path).convert("RGB")
            current_img = Image.open(current_path).convert("RGB")
            if baseline_img.size != current_img.size:
                current_img = current_img.resize(baseline_img.size)

            width, height = baseline_img.size
            changed_blocks = self._quadtree_compare(
                baseline_img=baseline_img,
                current_img=current_img,
                x=0,
                y=0,
                width=width,
                height=height,
                threshold=policy.mse_threshold,
                min_size=policy.min_block_size,
                depth=0,
                max_depth=policy.max_depth,
            )
            changed_area = sum(block[2] * block[3] for block in changed_blocks)
            diff_percent = round((changed_area / (width * height)) * 100, 2)

            baseline_hash = self.calculate_hash(baseline_path)
            current_hash = self.calculate_hash(current_path)
            hamming_distance = 0
            if baseline_hash and current_hash:
                hamming_distance = int(
                    imagehash.hex_to_hash(baseline_hash) - imagehash.hex_to_hash(current_hash)
                )

            delta_basis = delta_encoding_baseline_path or baseline_path
            delta = self.encode_delta(delta_basis, current_path)
            resolved_diff_path: Optional[Path] = None
            if policy.draw_diff_image and diff_output_path is not None:
                self._draw_diff(current_path, diff_output_path, changed_blocks)
                resolved_diff_path = diff_output_path

            elapsed_ms = int((time.monotonic() - started) * 1000)
            return DiffResult(
                report_id=report_id,
                baseline_hash=baseline_hash,
                current_hash=current_hash,
                hamming_distance=hamming_distance,
                diff_percent=diff_percent,
                changed_blocks=changed_blocks,
                delta_bytes=delta,
                diff_image_path=resolved_diff_path,
                diff_duration_ms=elapsed_ms,
            )
        except DiffComputationError:
            raise
        except Exception as exc:
            raise DiffComputationError("Unexpected error during diff computation") from exc

    def _draw_diff(
        self,
        current_path: Path,
        diff_output_path: Path,
        changed_blocks: list[tuple[int, int, int, int, float]],
    ) -> None:
        diff_output_path.parent.mkdir(parents=True, exist_ok=True)
        current_img = Image.open(current_path).convert("RGB")
        draw = ImageDraw.Draw(current_img)
        for x, y, width, height, _mse in changed_blocks:
            draw.rectangle([x, y, x + width, y + height], outline=(255, 0, 0), width=3)
        current_img.save(diff_output_path)

    def _calculate_mse(self, block1: Image.Image, block2: Image.Image) -> float:
        arr1 = np.array(block1, dtype=np.float32)
        arr2 = np.array(block2, dtype=np.float32)
        return float(np.mean((arr1 - arr2) ** 2))

    def _quadtree_compare(
        self,
        baseline_img: Image.Image,
        current_img: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        threshold: float,
        min_size: int,
        depth: int,
        max_depth: int,
    ) -> list[tuple[int, int, int, int, float]]:
        baseline_block = baseline_img.crop((x, y, x + width, y + height))
        current_block = current_img.crop((x, y, x + width, y + height))
        mse = self._calculate_mse(baseline_block, current_block)
        if mse <= threshold:
            return []
        if depth >= max_depth or width <= min_size or height <= min_size:
            return [(x, y, width, height, mse)]

        half_w = width // 2
        half_h = height // 2
        quadrants = [
            (x, y, half_w, half_h),
            (x + half_w, y, width - half_w, half_h),
            (x, y + half_h, half_w, height - half_h),
            (x + half_w, y + half_h, width - half_w, height - half_h),
        ]
        changed_blocks: list[tuple[int, int, int, int, float]] = []
        for qx, qy, qw, qh in quadrants:
            changed_blocks.extend(
                self._quadtree_compare(
                    baseline_img=baseline_img,
                    current_img=current_img,
                    x=qx,
                    y=qy,
                    width=qw,
                    height=qh,
                    threshold=threshold,
                    min_size=min_size,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            )
        return changed_blocks

