"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    issues = []
    lf_cfg = cfg.get("label_format", {})
    overflow_tol = float(lf_cfg.get("overflow_tol", 0.002))
    min_box_px = float(lf_cfg.get("min_box_px", 12))
    max_box_frac = float(lf_cfg.get("max_box_frac", 0.95))
    dup_box_iou = float(lf_cfg.get("dup_box_iou", 0.9))

    for lab_file in ds.label_files():
        stem = lab_file.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue

        valid_boxes = []
        for line_no, line_text in lines:
            try:
                cls_id, cx, cy, w, h = parse_yolo_line(line_text)
            except ValueError as err:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, f"dòng không đúng định dạng: {err}", line=line_no))
                continue

            if not (0 <= cls_id < len(ds.classes)):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp {cls_id} ngoài phạm vi 0..{len(ds.classes)-1}", line=line_no))
                continue

            if w <= 0.0 or h <= 0.0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"box rộng hoặc cao <= 0 (w={w}, h={h})", line=line_no))
                continue

            left = cx - w / 2.0
            top = cy - h / 2.0
            right = cx + w / 2.0
            bottom = cy + h / 2.0
            overflow = max(0.0, -left, -top, right - 1.0, bottom - 1.0)
            if overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn ra ngoài ảnh {overflow:.4f}",
                        line=line_no,
                        extra={"overflow": float(overflow)},
                    )
                )

            curr_box = (cx, cy, w, h)
            for prev_cls, prev_box in valid_boxes:
                if prev_cls == cls_id and iou_xywh(curr_box, prev_box) > dup_box_iou:
                    issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, f"box trùng với box trước đó cùng lớp {cls_id}", line=line_no))
                    break
            valid_boxes.append((cls_id, curr_box))

            img_size = ds.image_size(stem)
            if img_size:
                img_w, img_h = img_size
                short_side_px = min(w * img_w, h * img_h)
                if short_side_px < min_box_px:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"box quá nhỏ (cạnh ngắn {short_side_px:.1f}px < {min_box_px}px)", line=line_no))

            if w * h > max_box_frac:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"box quá lớn (diện tích {w*h:.2f} > {max_box_frac})", line=line_no))

    return issues
