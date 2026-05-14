from __future__ import annotations

from pathlib import Path

from PIL import Image

from pbimonitor.domain.reports.services import DiffPolicy, ReportDiffService


def _create_image(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (128, 128), color)
    image.save(path)


def test_quadtree_reports_non_zero_diff(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.png"
    current = tmp_path / "current.png"
    diff = tmp_path / "diff.png"
    _create_image(baseline, (255, 255, 255))
    image = Image.new("RGB", (128, 128), (255, 255, 255))
    image.putpixel((10, 10), (255, 0, 0))
    image.save(current)

    service = ReportDiffService()
    policy = DiffPolicy(mse_threshold=1.0, min_block_size=16, max_depth=4, draw_diff_image=True)
    result = service.compare("report-1", baseline, current, diff, policy)

    assert result.diff_percent > 0
    assert len(result.changed_blocks) > 0
    assert diff.exists()


def test_xor_encode_decode_roundtrip(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.png"
    current = tmp_path / "current.png"
    _create_image(baseline, (10, 20, 30))
    _create_image(current, (10, 20, 40))

    service = ReportDiffService()
    delta = service.encode_delta(baseline, current)
    restored = service.decode_delta(baseline, delta)

    restored_path = tmp_path / "restored.png"
    restored.save(restored_path)
    assert restored.tobytes() == Image.open(current).tobytes()


def test_compare_encodes_delta_against_separate_baseline(tmp_path: Path) -> None:
    last_baseline = tmp_path / "last.png"
    init_baseline = tmp_path / "init.png"
    current = tmp_path / "current.png"
    diff = tmp_path / "diff.png"
    _create_image(last_baseline, (255, 255, 255))
    _create_image(init_baseline, (0, 0, 0))
    _create_image(current, (0, 0, 255))

    service = ReportDiffService()
    policy = DiffPolicy(mse_threshold=1.0, min_block_size=16, max_depth=4, draw_diff_image=False)
    result_same_encode = service.compare(
        "r1", last_baseline, current, diff, policy, delta_encoding_baseline_path=last_baseline
    )
    result_split_encode = service.compare(
        "r1", last_baseline, current, diff, policy, delta_encoding_baseline_path=init_baseline
    )
    assert result_same_encode.delta_bytes != result_split_encode.delta_bytes
    decoded_from_init = service.decode_delta(init_baseline, result_split_encode.delta_bytes or b"")
    assert decoded_from_init.tobytes() == Image.open(current).convert("RGB").tobytes()

