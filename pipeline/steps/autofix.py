"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |
"""
from collections import defaultdict
from pathlib import Path

import yaml

from ..common import ERROR, parse_yolo_line

REMOVE_IMAGE_CODES = {
    "DUP_IMAGE_EXACT",
    "DUP_IMAGE_NEAR",
    "LEAK_TEST",
    "CORRUPT_IMAGE",
    "BAD_SIZE",
}

DROP_LINE_CODES = {
    "BAD_FORMAT",
    "BAD_CLASS_ID",
    "BOX_ZERO",
    "DUP_BOX",
}


def fix(ds, issues, cfg):
    # Chỉ xử lý các lỗi có severity ERROR
    err_issues = [i for i in issues if i.severity == ERROR]
    fixes = []
    removed_stems = set()

    # 1. Xoá ảnh + nhãn đối với các lỗi ảnh hỏng, trùng lặp, rò rỉ tập test
    for iss in err_issues:
        if iss.code in REMOVE_IMAGE_CODES or iss.code.startswith("DUP_IMAGE"):
            stem = iss.image
            if stem not in removed_stems:
                removed_stems.add(stem)
                img_p = ds.image_path(stem)
                if img_p and img_p.exists():
                    img_p.unlink()
                lbl_p = ds.label_path(stem)
                if lbl_p and lbl_p.exists():
                    lbl_p.unlink()
                ds._size_cache.pop(stem, None)
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "remove_image",
                    "before": "ảnh trong ds",
                    "after": "đã xoá",
                })

    # 2. Sửa data.yaml nếu sai tên lớp
    bad_yaml_issues = [i for i in err_issues if i.code == "BAD_CLASS_NAME"]
    if bad_yaml_issues:
        old_names = ds.yaml_names()
        target_classes = list(cfg["classes"])
        data = {}
        if ds.yaml_path.exists():
            data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        data["names"] = target_classes
        ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        fixes.append({
            "image": "data.yaml",
            "line": "",
            "action": "rename_classes",
            "before": str(old_names),
            "after": str(target_classes),
        })

    # 3. Ảnh thiếu file nhãn -> ghi needs_label (không tự bịa nhãn)
    needs_label_handled = set()
    for iss in err_issues:
        if iss.code == "MISSING_LABEL_FILE":
            stem = iss.image
            if stem not in removed_stems and stem not in needs_label_handled:
                needs_label_handled.add(stem)
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                })

    # 4. Sửa các lỗi theo dòng (drop_line, clip_box)
    line_issues_by_stem = defaultdict(list)
    for iss in err_issues:
        if iss.line is not None and iss.image not in removed_stems:
            if iss.code in DROP_LINE_CODES or iss.code == "BOX_OUT_OF_IMAGE":
                line_issues_by_stem[iss.image].append(iss)

    for stem in sorted(line_issues_by_stem.keys()):
        lab_p = ds.label_path(stem)
        if not lab_p.exists():
            continue

        raw_text = lab_p.read_text(encoding="utf-8", errors="replace")
        orig_lines = raw_text.splitlines()
        n_lines = len(orig_lines)

        line_map = defaultdict(list)
        for iss in line_issues_by_stem[stem]:
            if 1 <= iss.line <= n_lines:
                line_map[iss.line].append(iss)

        new_lines = []
        for line_num in range(1, n_lines + 1):
            orig_text = orig_lines[line_num - 1]
            if line_num not in line_map:
                new_lines.append(orig_text)
                continue

            issues_on_line = line_map[line_num]
            codes_on_line = {i.code for i in issues_on_line}

            # Quy tắc ưu tiên: xoá dòng (drop_line) thắng clip_box
            if codes_on_line & DROP_LINE_CODES:
                fixes.append({
                    "image": stem,
                    "line": line_num,
                    "action": "drop_line",
                    "before": orig_text,
                    "after": "",
                })
            elif "BOX_OUT_OF_IMAGE" in codes_on_line:
                try:
                    c, x, y, w, h = parse_yolo_line(orig_text)
                    x1 = x - w / 2.0
                    y1 = y - h / 2.0
                    x2 = x + w / 2.0
                    y2 = y + h / 2.0

                    x1_c = max(0.0, min(1.0, x1))
                    y1_c = max(0.0, min(1.0, y1))
                    x2_c = max(0.0, min(1.0, x2))
                    y2_c = max(0.0, min(1.0, y2))

                    w_c = x2_c - x1_c
                    h_c = y2_c - y1_c

                    if w_c <= 1e-6 or h_c <= 1e-6:
                        # Sau khi cắt không còn diện tích: xoá dòng
                        fixes.append({
                            "image": stem,
                            "line": line_num,
                            "action": "drop_line",
                            "before": orig_text,
                            "after": "",
                        })
                    else:
                        xc = (x1_c + x2_c) / 2.0
                        yc = (y1_c + y2_c) / 2.0
                        clipped_text = f"{int(c)} {xc:.6g} {yc:.6g} {w_c:.6g} {h_c:.6g}"
                        fixes.append({
                            "image": stem,
                            "line": line_num,
                            "action": "clip_box",
                            "before": orig_text,
                            "after": clipped_text,
                        })
                        new_lines.append(clipped_text)
                except ValueError:
                    fixes.append({
                        "image": stem,
                        "line": line_num,
                        "action": "drop_line",
                        "before": orig_text,
                        "after": "",
                    })

        content = "\n".join(new_lines)
        if new_lines:
            content += "\n"
        lab_p.write_text(content, encoding="utf-8")

    return fixes
