"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán:
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    so_cfg = cfg.get("second_opinion", {})
    conf_th = float(so_cfg.get("conf", 0.25))
    min_area_px = float(so_cfg.get("min_area_px", 600))
    fp_conf = float(so_cfg.get("fp_conf", 0.1))
    iou_missing = float(so_cfg.get("iou_missing", 0.3))
    iou_match = float(so_cfg.get("iou_match", 0.5))
    iou_loose = float(so_cfg.get("iou_loose", 0.5))

    issues = []

    for img_p in ds.image_files():
        stem = img_p.stem
        if stem not in preds:
            continue

        raw_lines = ds.read_label_lines(stem)
        if raw_lines is None:
            continue

        valid_labels = []
        for line_no, text in raw_lines:
            try:
                c, x, y, w, h = parse_yolo_line(text)
                if 0 <= c < len(ds.classes):
                    valid_labels.append((line_no, c, (x, y, w, h)))
            except ValueError:
                continue

        img_size = ds.image_size(stem)
        w_img, h_img = img_size if img_size else (0, 0)

        all_preds = preds.get(stem, [])

        filtered_preds = []
        for p in all_preds:
            p_cls = int(p[0])
            p_conf = float(p[1])
            p_box = (float(p[2]), float(p[3]), float(p[4]), float(p[5]))
            area_px = (p_box[2] * w_img) * (p_box[3] * h_img)
            if p_conf >= conf_th and area_px >= min_area_px:
                filtered_preds.append((p_cls, p_conf, p_box))

        for p_cls, p_conf, p_box in filtered_preds:
            cands = []
            for l_no, l_cls, l_box in valid_labels:
                iou = iou_xywh(p_box, l_box)
                if iou >= iou_missing:
                    cands.append((l_no, l_cls, l_box, iou))

            if not cands:
                cls_name = ds.classes[p_cls] if 0 <= p_cls < len(ds.classes) else str(p_cls)
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model thấy {cls_name} (conf {p_conf:.2f}) nhưng nhãn thiếu",
                        line=None,
                        extra={"conf": float(p_conf)},
                    )
                )
            else:
                same_class_cands = [c for c in cands if c[1] == p_cls]
                diff_class_cands = [c for c in cands if c[1] != p_cls]

                if same_class_cands:
                    best_same_iou = max(c[3] for c in same_class_cands)
                    if best_same_iou < iou_loose:
                        cls_name = ds.classes[p_cls] if 0 <= p_cls < len(ds.classes) else str(p_cls)
                        issues.append(
                            Issue(
                                "second_opinion",
                                WARN,
                                "POSSIBLE_LOOSE_BOX",
                                stem,
                                f"nhãn {cls_name} lệch so với dự đoán (IoU {best_same_iou:.2f} < {iou_loose})",
                                line=None,
                                extra={"conf": float(p_conf), "iou": float(best_same_iou)},
                            )
                        )
                else:
                    if diff_class_cands:
                        best_diff_iou = max(c[3] for c in diff_class_cands)
                        if best_diff_iou >= iou_match:
                            cls_name = ds.classes[p_cls] if 0 <= p_cls < len(ds.classes) else str(p_cls)
                            issues.append(
                                Issue(
                                    "second_opinion",
                                    WARN,
                                    "POSSIBLE_WRONG_CLASS",
                                    stem,
                                    f"model đoán {cls_name} (conf {p_conf:.2f}), nhãn gán khác lớp (IoU {best_diff_iou:.2f})",
                                    line=None,
                                    extra={"conf": float(p_conf), "iou": float(best_diff_iou)},
                                )
                            )

        fp_preds = [p for p in all_preds if float(p[1]) >= fp_conf]
        for line_no, l_cls, l_box in valid_labels:
            has_match = any(
                iou_xywh(l_box, (float(p[2]), float(p[3]), float(p[4]), float(p[5]))) >= iou_missing
                for p in fp_preds
            )
            if not has_match:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"nhãn ở dòng {line_no} không khớp dự đoán nào (IoU < {iou_missing})",
                        line=line_no,
                        extra={"iou": 0.0},
                    )
                )

    return issues
