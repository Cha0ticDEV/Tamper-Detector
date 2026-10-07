
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
import numpy as np

def block_reduce(arr, block=24, reducer=np.mean):
    h, w = arr.shape
    rows, cols = max(1, h // block), max(1, w // block)
    trimmed = arr[:rows*block, :cols*block]
    blocks = trimmed.reshape(rows, block, cols, block)
    return reducer(blocks, axis=(1, 3)).astype(np.float32)

def expand_grid(grid, shape, block):
    h, w = shape
    out = np.repeat(np.repeat(grid, block, axis=0), block, axis=1)
    return out[:h, :w]

def robust_z(values):
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    return (values - med) / max(1.4826 * mad, 1e-6)

def connected_components(mask, min_cells=2):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    groups = []
    for r in range(h):
        for c in range(w):
            if not mask[r, c] or seen[r, c]:
                continue
            stack, cells = [(r, c)], []
            seen[r, c] = True
            while stack:
                cr, cc = stack.pop()
                cells.append((cr, cc))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and mask[nr, nc] and not seen[nr, nc]:
                            seen[nr, nc] = True
                            stack.append((nr, nc))
            if len(cells) >= min_cells:
                groups.append(cells)
    return sorted(groups, key=len, reverse=True)

def groups_to_boxes(groups, block, shape):
    h, w = shape
    boxes = []
    for cells in groups:
        rows = [r for r, _ in cells]
        cols = [c for _, c in cells]
        boxes.append((min(cols)*block, min(rows)*block,
                      min((max(cols)+1)*block, w),
                      min((max(rows)+1)*block, h), len(cells)))
    return boxes

def make_heatmap(grid, shape, block):
    heat = expand_grid(grid, shape, block)
    lo, hi = np.percentile(heat, [50, 99])
    norm = np.clip((heat-lo)/max(hi-lo, 1e-6), 0, 1)
    return ImageEnhance.Contrast(Image.fromarray((norm*255).astype(np.uint8))).enhance(1.8)

def analyze_ela(image_path, quality=90, block=24):
    path = Path(image_path)
    original = Image.open(path).convert("RGB")
    temp = path.with_name(path.stem + "_ela_temp.jpg")
    original.save(temp, "JPEG", quality=quality)
    resaved = Image.open(temp).convert("RGB")
    diff_img = ImageChops.difference(original, resaved)
    diff = np.asarray(diff_img.convert("L"), dtype=np.float32)

    grid = block_reduce(diff, block, np.mean)
    z = robust_z(grid)
    threshold = max(float(np.percentile(grid, 98)),
                    float(np.median(grid) + 2.5*np.std(grid)))
    suspicious = (z >= 3.0) & (grid >= threshold)
    groups = connected_components(suspicious, 2)

    return {
        "temp_path": temp,
        "ela_image": ImageEnhance.Brightness(diff_img).enhance(10),
        "heatmap": make_heatmap(grid, diff.shape, block),
        "mean_error": float(diff.mean()),
        "max_error": float(diff.max()),
        "suspicious_blocks": int(suspicious.sum()),
        "regions": len(groups),
        "boxes": groups_to_boxes(groups, block, diff.shape),
    }

def analyze_local_consistency(image_path, block=24):
    image = Image.open(image_path).convert("L")
    gray = np.asarray(image, dtype=np.float32)
    blur = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32)
    residual = gray - blur

    noise = block_reduce(residual, block, np.std)
    texture = block_reduce(gray, block, np.std)

    p = np.pad(noise, 1, mode="edge")
    neighbors = np.stack([p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:],
                           p[1:-1, :-2], p[1:-1, 2:],
                           p[2:, :-2], p[2:, 1:-1], p[2:, 2:]])
    med = np.median(neighbors, axis=0)
    ratio = (noise + 0.5) / (med + 0.5)

    usable = texture >= max(float(np.percentile(texture, 25)), 1.0)
    anomaly = ((ratio >= 2.5) | (ratio <= 0.40)) & usable
    groups = connected_components(anomaly, 2)

    heat = np.abs(np.log(np.maximum(ratio, 1e-6)))
    return {
        "heatmap": make_heatmap(heat, gray.shape, block),
        "anomaly_blocks": int(anomaly.sum()),
        "regions": len(groups),
        "boxes": groups_to_boxes(groups, block, gray.shape),
    }

def inspect_metadata(image_path):
    path = Path(image_path)
    image = Image.open(path)
    return {
        "format": image.format or path.suffix.replace(".", "").upper(),
        "width": image.width,
        "height": image.height,
        "file_size_kb": path.stat().st_size/1024,
        "exif_count": len(image.getexif()),
    }

def assess(ela, local, metadata):
    ela_flag = ela["regions"] >= 1 and ela["suspicious_blocks"] >= 2
    local_flag = local["regions"] >= 1
    evidence = int(ela_flag) + int(local_flag)
    reasons = []
    if ela_flag:
        reasons.append(f"Adaptive ELA found {ela['suspicious_blocks']} high-error blocks in {ela['regions']} region(s).")
    if local_flag:
        reasons.append(f"Local consistency found {local['anomaly_blocks']} anomalous blocks in {local['regions']} region(s).")
    if evidence == 2:
        status, level = "POTENTIAL MANIPULATION INDICATORS", "Moderate"
    elif evidence == 1:
        status, level = "SOME IMAGE ANOMALIES DETECTED", "Low"
    else:
        status, level = "NO STRONG IMAGE ANOMALIES DETECTED", "Low"
    return {"status": status, "level": level, "evidence": evidence, "reasons": reasons}
