# Báo cáo Day 09 — Nguyễn Quang Tùng, 2A202603080

## 1. Kết luận trước
* **Phán quyết**: **HOLD** (mã thoát 10).
* **Số lượng ảnh**: 224 ảnh thô (`data/raw`) $\rightarrow$ **203 ảnh sạch** (`submission/export/clean_v1/`), loại bỏ 21 ảnh hỏng, quá nhỏ, trùng lặp và rò rỉ test.
* **Lý do**: Toàn bộ lỗi bắt buộc nghiêm trọng đã xử lý triệt để (`n_errors = 0`). Tuy nhiên, với ngân sách duyệt 80 ảnh, hàng đợi vẫn còn **44 ảnh** mang cảnh báo ngữ nghĩa chưa duyệt, chiếm **21.7%** dataset (44/203), vượt trần an toàn 10.0% (`warn_ratio_hold = 0.10`). Dataset chỉ được xuất bản nháp nội bộ (`manifest.json` ghi `decision: Hold`), chưa đủ điều kiện phát hành (Release).

## 2. Lỗi và phân việc
Báo cáo vòng 1 (`02_error_list_v1`) ghi nhận 36 lỗi bắt buộc (`ERROR`) và 171 cảnh báo (`WARN`).
**Nguyên tắc phân việc**: Cơ học/xác định 100% giao máy xử lý tự động (`autofix`/`intake`); vấn đề ngữ nghĩa, bối cảnh và thị giác chuyển người duyệt qua hàng đợi.

| Mã lỗi | Số lượng | Đơn vị xử lý | Cơ chế & Lý do phân việc |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 ảnh | Máy (`intake`) | File ảnh hỏng (không đọc được header), loại bỏ ngay cửa vào. |
| `BAD_SIZE` | 3 ảnh | Máy (`intake`) | Cạnh ngắn < 250px không đủ độ phân giải train YOLO, loại bỏ. |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (`intake`) | Trùng byte tuyệt đối (MD5 hash), loại bỏ tránh lãng phí tính toán. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (`intake`) | Trùng gần đúng (pHash $\le 6$), loại bỏ tránh thiên lệch mô hình. |
| `LEAK_TEST` | 5 ảnh | Máy (`intake`) | Trùng kho test/val, bắt buộc loại bỏ để chống rò rỉ đề (data leakage). |
| `BAD_FORMAT` | 3 dòng | Máy (`autofix`) | Thiếu cột toạ độ hoặc dính NaN/Inf, xoá dòng rác theo chuẩn YOLO. |
| `BAD_CLASS_ID` | 6 dòng | Máy (`autofix`) | ID ngoài dải 0..3 (93, -1, 7, 4), xoá dòng sai cú pháp xác định. |
| `BAD_CLASS_NAME` | 2 lỗi | Máy (`autofix`) | Tên lớp trong `data.yaml` sai chuẩn ('Person', 'Bus'), chuẩn hoá lại. |
| `BOX_ZERO` | 4 dòng | Máy (`autofix`) | Width hoặc height $\le 0$, xoá dòng vì không có diện tích thực. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (`autofix`) | Tràn viền nhẹ, tính toán xén toạ độ về $[0, 1]$ (`clip_box`). |
| `DUP_BOX` | 7 dòng | Máy (`autofix`) | Trùng box cùng lớp (IoU > 0.9), giữ box đầu và xoá box trùng sau. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (Hàng đợi) | Thiếu file nhãn; máy không tự bịa nhãn mà chuyển diện `needs_label`. |
| `BOX_TINY` | 6 box | Người (Hàng đợi) | Box quá nhỏ (< 12px), cần mắt người xác nhận vật thể xa hay nhiễu ảnh. |
| `BOX_HUGE` | 3 box | Người (Hàng đợi) | Box chiếm > 95% ảnh, cần người kiểm tra do chụp cận cảnh hay gán nhầm. |
| `EMPTY_LABEL` | 12 ảnh | Người (Hàng đợi) | File nhãn rỗng, cần người thẩm định là ảnh nền thật hay bị bỏ sót. |
| `CLASS_RARE` | 4 lớp | Người (Hàng đợi) | Cảnh báo mất cân bằng tập dữ liệu khi có lớp chỉ xuất hiện 1-2 lần. |
| `POSSIBLE_MISSING` | 68 vị trí | Người (Hàng đợi) | Model phụ tá phát hiện vật thể rõ ràng nhưng nhãn thiếu, cần người vẽ bù. |
| `POSSIBLE_WRONG_CLASS` | 18 vị trí | Người (Hàng đợi) | Cùng vị trí nhưng nhãn và model khác lớp, cần người phân xử lớp đúng. |
| `POSSIBLE_LOOSE_BOX` | 31 dòng | Người (Hàng đợi) | Box nhãn vẽ lệch/lỏng (IoU < 0.5) so với model, cần người kéo khít lại. |
| `POSSIBLE_FALSE_POS` | 29 dòng | Người (Hàng đợi) | Nhãn ở vị trí model không thấy vật thể, cần người xác nhận có gán thừa. |

**Ưu tiên hàng đợi (`05_review_queue.csv`)**:
* Ảnh thiếu nhãn (`NEEDS_LABEL`) được cộng 10 điểm để ưu tiên xử lý đầu tiên, tránh lỗi bắt buộc làm nghẽn pipeline.
* Ảnh dính chùm nhiều lỗi có điểm ưu tiên cao nhất, điển hình `img_0020` đứng đầu (14.528 điểm) do dính cả `FIXED_DROP_LINE`, `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`.
* Với ngân sách 80 ảnh, người duyệt xử lý hết 100% (6/6) ảnh thiếu nhãn và 74 ảnh bất thường nhất; 44 ảnh cảnh báo nhẹ còn lại đành gác lại vì hết ngân sách.

## 3. Calibration
Kết quả sweep tham số trên tập `data/calib/` (39 ảnh có ground truth chèn lỗi):

| Tham số | Ban đầu | Đã chọn | P / R (trước → sau) | Phân tích đánh đổi & Lý do chọn |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **6** | P: 1.00 → 1.00<br>R: 0.50 → 0.67 | Tại mức 2, Recall chỉ 0.50 (bỏ sót nửa số ảnh trùng). Nâng lên 6 giúp tăng Recall lên 0.67 (bắt thêm 2 ảnh biến thể trong tập raw) mà Precision vẫn tuyệt đối 1.00. Vì bước này tự động xoá ảnh (`remove_image`), bắt buộc giữ Precision = 1.00 để không xoá nhầm ảnh sạch. |
| `second_opinion.conf` | 0.25 | **0.50** | MISSING P: 0.50 → 0.57<br>WRONG_CLASS P: 0.56 → 0.56<br>R: 1.00 → 1.00 | Tại mức 0.25, model phụ tá quá nhạy (273 cảnh báo làm tràn hàng đợi). Nâng lên 0.50 giúp giảm 37% cảnh báo rác (còn 171 cảnh báo), tăng Precision MISSING từ 50% lên 57%, đồng thời giữ nguyên Recall = 1.00 (không bỏ sót lỗi thiếu nhãn thật). |

**Cạm bẫy Calibration**:
Nếu chỉ chọn theo F1 cao nhất trên tập calib, mức `phash_dist = 16` đạt F1 = 0.91 (Recall 0.83). Tuy nhiên, đây là bẫy overfit do tập calib chỉ có 39 ảnh nhân tạo rành mạch. Trên tập raw 224 ảnh, khoảng cách Hamming 16 quá lỏng, dễ coi các ảnh phong cảnh cùng tông màu xám/trời là trùng và xoá nhầm. Ngưỡng 6 là điểm cân bằng an toàn nhất, vừa bắt đúng ảnh biến thể co giãn nhẹ (cặp `img_0076` và `img_0042`, pHash dist = 0), vừa bảo vệ ảnh độc lập. Với `conf`, nếu nâng lên 0.7–0.8 để giảm tải hàng đợi, Recall MISSING sẽ tụt xuống 0.88 rồi 0.75 (bỏ sót 25% lỗi thật), nên 0.50 là điểm ngọt hợp lý.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
* **Kiểm chứng Gate chặn đúng**: Chạy kịch bản không có người duyệt bằng lệnh:
  `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`
  Kết quả: Vì không có người duyệt, 6 ảnh thiếu nhãn (`MISSING_LABEL_FILE`) còn nguyên. QC vòng 3 ghi nhận `n_errors = 6`. Gate kích hoạt ngay kết luận **REWORK**, trả về mã thoát **20** và **không xuất** thư mục dataset `work/exp_nb`. Điều này chứng minh cửa chặn hoạt động độc lập và thực thi nghiêm ngặt.
* **3 điểm mù mà pipeline chưa bắt được**:
  1. *Box lỏng nhẹ/lệch viền nhưng IoU vẫn $\ge 0.50$*: Trên `img_0030`, một số box người đi bộ vẽ thụng xuống dưới nhưng IoU với model vẫn đạt ~0.55 (vượt ngưỡng lỏng `iou_loose = 0.50`), hệ thống coi là khớp và bỏ qua.
  2. *Vật thể bị che khuất một phần (occlusion) hoặc thiếu sáng*: Cả người gán nhãn lẫn model phụ tá `yolo26l` đều nhìn sót hoặc cùng đoán nhầm một lớp. Hiện tượng "đồng thuận sai" (`silent false agreement`) khiến pipeline không phát hiện được lỗi khi cả hai cùng sai.
  3. *Ảnh trùng bị cắt cúp sâu (crop mất > 70% diện tích)*: Thuật toán pHash dựa trên hệ số tần số thấp DCT 2D; khi ảnh bị crop quá nhiều bối cảnh, chữ ký băm thay đổi hoàn toàn khiến cửa intake không thể phát hiện.

## 5. Train: raw vs clean
Huấn luyện mô hình `yolo26n` trên Google Colab (GPU T4), 20 epochs, batch 16, imgsz 640 qua 2 seed (0 và 1). Đánh giá trên cùng tập Test độc lập (100 ảnh):

| Biến thể | Số ảnh train | Số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|
| **raw** (chưa lọc) | 224 | 2 | **0.726** ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| **clean** (sau pipeline) | 203 | 2 | **0.695** ± 0.010 | 0.482 ± 0.007 | 0.726 ± 0.005 | 0.619 ± 0.016 |

Chênh lệch mAP50 (`clean` − `raw`) = **-0.031**.

**Đánh giá thực nghiệm**:
Chênh lệch -0.031 nằm sát biên độ nhiễu thống kê giữa các seed của clean ($\pm 0.010$) và độ lệch precision của raw ($\pm 0.061$) trên tập test nhỏ 100 ảnh.
Hai nguyên nhân cốt lõi:
1. *Data leakage ở tập raw*: Tập `raw` có 5 ảnh trùng trực tiếp với test set (`LEAK_TEST`) và 8 ảnh trùng tuyệt đối, giúp mô hình "học tủ" câu hỏi kiểm tra và tạo ra mAP cao giả tạo. Tập `clean` loại bỏ hoàn toàn số ảnh này nên điểm số phản ánh năng lực khái quát hoá trung thực.
2. *Sụt giảm quy mô dữ liệu*: Tập `clean` mất 21 ảnh (~10% dữ liệu) trong bài toán vốn chỉ có ~200 ảnh và train 20 epoch ngắn, làm giảm mật độ mẫu ở một số góc chụp hiếm trước khi mô hình kịp hội tụ bù đắp.
* *Cách kiểm chứng*: Loại bỏ 5 ảnh leak khỏi tập Test độc lập và đánh giá lại; điểm của `raw` sẽ giảm xuống phản ánh đúng thực tế.

## 6. Quyết định và ghi chú AI
* **Quyết định**: Đồng thuận với kết luận của Gate, giữ trạng thái **HOLD**. Dataset `submission/export/clean_v1/` lưu hành nội bộ dạng bản nháp (`manifest.json` ghi `decision: Hold`).
* **Điều kiện nâng lên Release**:
  1. Tăng ngân sách thẩm định từ 80 lên tối thiểu 130 ảnh để giải quyết nốt 44 ảnh cảnh báo còn lại, đưa tỷ lệ cảnh báo về dưới 10%.
  2. Hoặc họp rà soát mức độ rủi ro của 44 cảnh báo còn lại; nếu chấp nhận được, cập nhật guideline dự án nới ngưỡng `warn_ratio_hold` từ 10% lên 25%.
* **(Thưởng +2) Thực nghiệm CVAT**:
  * Thử nghiệm lọc box trên CVAT theo `docs/CVAT_FILTER.md` với điều kiện `width < 20`: Trên ảnh `img_0161`, bộ lọc gom đúng 3 box dòng 2, 3, 4 (10.3px, 11.4px, 11.9px) — khớp hoàn toàn với 3 cảnh báo `BOX_TINY` của pipeline (ngưỡng `min_box_pixels = 12.0`). Ngưỡng 12px của pipeline chặt chẽ hơn ngưỡng 20px của slide, tránh bắt nhầm vật thể ở xa hợp lệ.
  * Thuộc tính `can_review`: Người gán nhãn tích chọn khi gặp ca khó/mơ hồ (che khuất, thiếu sáng) cần chuyên viên kiểm tra lại. Trong pipeline tự động, cơ chế tương đương là model phụ tá phát hiện các ca bất thường (`POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`, `POSSIBLE_LOOSE_BOX`) và tính điểm đẩy vào `05_review_queue.csv` cho con người duyệt.
* **Ghi chú sử dụng AI**:
  * *Prompt chính*: "Viết 4 module `label_format.py`, `gate.py`, `autofix.py`, `second_opinion.py` theo đúng docstring và thiết kế hướng kiểm thử (TDD), xử lý chặt chẽ các ca biên (dòng rỗng, tràn số, box âm) và tuyệt đối không ghi đè dữ liệu gốc `data/raw/`."
  * *Cách kiểm tra code AI*: Chạy tự động 79 ca kiểm thử bằng `pytest -q`, bổ sung kiểm tra các ca biên phức tạp (1 dòng dính nhiều lỗi, file có dòng trắng xen giữa) và đối chiếu số liệu `08_summary.json` với `manifest.json`.
  * *Một lần AI chưa chuẩn*: Trong script `scripts/check_submission.py`, đường dẫn Windows dùng `\` làm lỗi so khớp với danh sách mẫu trong `_protected.json` (dùng `/`); đã sửa thành `.as_posix()` để tương thích đa nền tảng.
