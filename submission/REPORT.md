# Báo cáo Day 09 — Nguyễn Quang Tùng, 2A202603080

## 1. Kết luận trước
Pipeline kết luận: **HOLD** (Mã thoát 10).
* **Số ảnh đầu vào**: 224 ảnh thô (`data/raw`).
* **Số ảnh đầu ra dataset sạch**: 203 ảnh (xuất bản nháp tại `submission/export/clean_v1/`, loại bỏ 21 ảnh hỏng, trùng lặp và rò rỉ test).
* **Lý do chính**: Toàn bộ lỗi bắt buộc nghiêm trọng đã được khắc phục hoàn toàn (`n_errors = 0`). Tuy nhiên, do ngân sách thẩm định của con người có hạn (80 ảnh), vẫn còn 44 bức ảnh mang cảnh báo ngữ nghĩa chưa được duyệt. Tỉ lệ ảnh cảnh báo chưa duyệt là **21.7%** (44/203 ảnh), vượt ngưỡng quy định 10.0% (`warn_ratio_hold = 0.10`). Do đó, dataset chỉ được lưu hành dưới dạng bản nháp để thử nghiệm nội bộ và CHƯA được phát hành chính thức (Release).

## 2. Lỗi và phân việc
Tổng hợp từ `02_error_list_v1` trước khi sửa (tổng cộng 36 lỗi bắt buộc và 171 cảnh báo trên 203 ảnh hợp lệ):

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_CLASS_ID` | 6 dòng | Máy (`autofix`) | ID lớp nằm ngoài phạm vi 0..3 (93, -1, 7, 4), máy xoá dòng an toàn theo quy tắc xác định. |
| `BAD_CLASS_NAME` | 2 lỗi | Máy (`autofix`) | Tên lớp trong `data.yaml` sai chuẩn ('Person', 'Bus'), máy chuẩn hoá về danh sách `classes`. |
| `BAD_FORMAT` | 3 dòng | Máy (`autofix`) | Dòng nhãn thiếu cột hoặc chứa giá trị NaN/Inf, máy xoá dòng rác. |
| `BAD_SIZE` | 3 ảnh | Máy (`intake`) | Ảnh có cạnh ngắn < 250px không đạt độ phân giải tối thiểu để train YOLO, tự động loại bỏ. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (`autofix`) | Box tràn ra ngoài mép ảnh, máy tự động cắt toạ độ về [0, 1] (`clip_box`). |
| `BOX_ZERO` | 4 dòng | Máy (`autofix`) | Box có chiều rộng hoặc cao $\le 0$, máy xoá dòng vì không có diện tích thực. |
| `CORRUPT_IMAGE` | 2 ảnh | Máy (`intake`) | File ảnh bị hỏng không mở được header, tự động loại bỏ ở cửa vào. |
| `DUP_BOX` | 7 dòng | Máy (`autofix`) | Box trùng lặp cùng lớp trong 1 ảnh (IoU > 0.9), máy giữ box đầu và xoá box sau. |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (`intake`) | Trùng lặp từng byte (MD5 hash), tự động loại bỏ ảnh trùng tránh lãng phí tính toán. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (`intake`) | Trùng gần đúng (pHash Hamming $\le 6$), tự động loại bỏ ảnh biến thể co giãn. |
| `LEAK_TEST` | 5 ảnh | Máy (`intake`) | Ảnh trùng với kho test/val, bắt buộc loại bỏ để chống rò rỉ đề (data leakage). |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (Hàng đợi) | Máy không được phép tự bịa nhãn, đưa vào diện `needs_label` để người gán nhãn bổ sung. |
| `BOX_HUGE` | 3 box | Người (Hàng đợi) | Cảnh báo box chiếm diện tích $> 95\%$ ảnh, cần mắt người xác nhận có phải dị vật hoặc góc chụp cận. |
| `BOX_TINY` | 6 box | Người (Hàng đợi) | Cảnh báo box nhỏ < 12px, người duyệt quyết định giữ hay lọc theo guideline dự án. |
| `CLASS_RARE` | 4 lớp | Người (Hàng đợi) | Cảnh báo mất cân bằng tập dữ liệu khi có lớp lạ chỉ xuất hiện 1-2 lần. |
| `EMPTY_LABEL` | 12 ảnh | Người (Hàng đợi) | Cảnh báo file rỗng là ảnh nền (background) thật hay do người gán nhãn bỏ sót. |
| `POSSIBLE_FALSE_POS` | 29 dòng | Người (Hàng đợi) | Nhãn không khớp vật thể nào model tham chiếu thấy, người kiểm tra xem có gán thừa. |
| `POSSIBLE_LOOSE_BOX` | 31 dòng | Người (Hàng đợi) | Box nhãn bị lệch hoặc lỏng (IoU < 0.5) so với model, cần người chỉnh lại viền cho khít. |
| `POSSIBLE_MISSING` | 68 vị trí | Người (Hàng đợi) | Model tham chiếu phát hiện vật thể nhưng nhãn thiếu, cần người bổ sung box. |
| `POSSIBLE_WRONG_CLASS` | 18 vị trí | Người (Hàng đợi) | Box trùng vị trí nhưng sai lớp (IoU $\ge 0.5$), người sửa lại nhãn lớp chính xác. |

**Chiến lược hàng đợi duyệt (`05_review_queue.csv`):**
* Hàng đợi sắp xếp theo tổng điểm ưu tiên: Ảnh `NEEDS_LABEL` có trọng số cao nhất (cộng 10.0 điểm) để ưu tiên xử lý dứt điểm các lỗi bắt buộc làm nghẽn pipeline. Kế đến là các ảnh dính nhiều lỗi ngữ nghĩa đồng thời (`img_0020` đứng đầu với điểm ưu tiên 14.528 vì dính cả `FIXED_DROP_LINE`, `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`).
* Với ngân sách duyệt cố định 80 ảnh, con người đã xử lý được **100% (6/6) ảnh thiếu file nhãn** và **74 ảnh có nguy cơ lỗi ngữ nghĩa nghiêm trọng nhất** (các ca sai lớp và sót nhãn có độ tin cậy cao). 50 ảnh còn lại trong hàng đợi (tương ứng 44 ảnh còn mang cảnh báo ở vòng 3) có độ ưu tiên thấp hơn nên chưa thể duyệt hết.

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **6** | P: 1.00 → 1.00<br>R: 0.50 → 0.67 | Tăng Recall bắt ảnh gần trùng từ 50% lên 67% (bắt thêm 2 ảnh gần trùng trong tập raw), trong khi Precision giữ tuyệt đối 1.00 (tránh xoá nhầm ảnh sạch). |
| `second_opinion.conf` | 0.25 | **0.50** | MISSING P: 0.50 → 0.57<br>WRONG_CLASS P: 0.56 → 0.56<br>R: 1.00 → 1.00 | Tăng độ chuẩn xác cảnh báo, giảm báo động giả từ 273 xuống 171 cảnh báo (giảm tải 37% cho hàng đợi), trong khi Recall vẫn giữ 100% lỗi thiếu nhãn thật. |

**Cạm bẫy Calibration có thể đánh lừa:**
* Tập calib chỉ có 39 ảnh, phân bố lỗi do con người cố ý gài cắm tương đối sạch và mang tính cục bộ.
* Nếu chạy theo chỉ số F1 thuần tuý trên tập calib và chọn `phash_dist = 16` (F1 đạt 0.909 trên calib), thì khi áp dụng vào tập dữ liệu raw thực tế (224 ảnh), khoảng cách Hamming 16 là quá lỏng. Máy sẽ nhận định sai các bức ảnh chụp cùng bối cảnh góc phố hay cùng điều kiện ánh sáng thành "ảnh trùng" và tự động xoá nhầm dữ liệu tốt của dự án.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
* **Chứng minh Gate chặn đúng khi còn lỗi bắt buộc:**
  Thực nghiệm chạy pipeline không có người duyệt bằng lệnh:
  `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`
  Kết quả thực tế: Do không có người duyệt, 6 ảnh thiếu file nhãn (`MISSING_LABEL_FILE`) không được gán nhãn, dẫn đến QC vòng 3 còn nguyên 6 lỗi bắt buộc (`ERROR`). Cửa chặn đã kích hoạt chuẩn xác: đưa ra kết luận **`Rework`**, trả về mã thoát **`20`**, và hoàn toàn **KHÔNG xuất** thư mục dữ liệu `work/exp_nb`.
* **Hai điểm mù pipeline không thể bắt được:**
  1. *Box lỏng nhẹ hoặc lệch mép nhưng IoU vẫn $\ge 0.50$*: Nằm trên ngưỡng `iou_loose` (0.50) nên cả thuật toán lẫn model tham chiếu đều coi là khớp đúng và bỏ qua, chỉ có mắt người thẩm định trực quan mới phát hiện được.
  2. *Vật thể bị che khuất một phần (occlusion) hoặc điều kiện ánh sáng quá tối/ngược sáng*: Cả nhãn người gán lẫn mô hình tham chiếu (`yolo26l`) đều nhìn sót hoặc nhận nhầm lớp như nhau. Khi model và nhãn cùng sai, pipeline rơi vào trạng thái "đồng thuận sai" (`silent false agreement`) và không đưa ra cảnh báo nào.
  3. *Ảnh trùng lặp bị crop xén mạnh (mất > 70% bối cảnh) hoặc xoay góc*: Thuật toán perceptual hash (pHash) bị thay đổi hoàn toàn cấu trúc tần số ảnh DCT, làm lọt ảnh trùng qua cửa intake.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Dữ liệu huấn luyện trên Google Colab GPU T4 (mô hình `yolo26n`, 20 epochs, batch 16, imgsz 640, chạy 2 seeds: seed 0 và seed 1):

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 203 | 2 | 0.695 ± 0.010 | 0.482 ± 0.007 | 0.726 ± 0.005 | 0.619 ± 0.016 |

Chênh mAP50 (clean − raw) = **-0.031**.

**Phân tích & Kết luận trung thực:**
* Mức chênh lệch mAP50 giữa `clean` và `raw` là $-0.031$ (giảm 3.1%). Độ lệch chuẩn giữa các seed của clean là $\pm 0.010$ và độ lệch precision của raw là $\pm 0.061$. Do đó, mức chênh lệch 3% này **nằm sát biên độ nhiễu thống kê ngẫu nhiên** giữa các lần chạy ngẫu nhiên trên tập test nhỏ 100 ảnh.
* **Hai nguyên nhân chính giải thích vì sao mAP raw cao hơn clean:**
  1. *Hiện tượng rò rỉ dữ liệu (Data Leakage) ở tập raw*: Trong tập `raw` có 5 ảnh trùng với tập test (`LEAK_TEST`) và 8 ảnh nhân bản (`DUP_IMAGE_EXACT`). Khi huấn luyện trên `raw`, mô hình đã "học vẹt" trước đề thi của tập test (100 ảnh), tạo ra điểm số mAP cao giả tạo. Mô hình `clean` đã loại bỏ hoàn toàn các ảnh rò rỉ này nên điểm số phản ánh năng lực khái quát hoá thật sự.
  2. *Đánh đổi về kích thước mẫu*: Tập clean bị giảm 21 ảnh (từ 224 xuống 203 ảnh, giảm gần 10% dữ liệu). Với quy mô tập train quá nhỏ và chỉ 20 epoch, việc mất bớt một số mẫu vật thể hiếm có thể làm giảm tạm thời độ bao phủ khi đánh giá trên tập test.
* *Cách kiểm chứng:* Loại bỏ 5 ảnh bị rò rỉ ra khỏi tập Test độc lập rồi đánh giá lại cả 2 mô hình; khi đó điểm số của `raw` sẽ sụt giảm rõ rệt.

## 6. Quyết định và ghi chú AI
* **Quyết định cuối cùng:** **HOLD** (Mã thoát 10). Bản xuất `submission/export/clean_v1/` được gắn nhãn bản nháp thử nghiệm nội bộ (`manifest.json` ghi `decision: Hold`).
* **Điều kiện để chuyển thành Release:**
  1. Tăng ngân sách thẩm định của con người từ 80 ảnh lên ít nhất 130 ảnh để người duyệt xử lý nốt 44 ảnh còn cảnh báo trong hàng đợi, đưa tỷ lệ cảnh báo chưa duyệt từ 21.7% về dưới ngưỡng 10%.
  2. Hoặc nhóm quản lý dự án họp đánh giá mức độ rủi ro đối với các cảnh báo ngữ nghĩa còn lại (chủ yếu là các box lỏng nhẹ hoặc vật thể nhỏ) và điều chỉnh ngưỡng `warn_ratio_hold` trong guideline dự án nếu chấp nhận được chất lượng hiện tại.
* **(Thưởng +2, tùy chọn) Thực nghiệm CVAT:**
  * *Thử nghiệm lọc box trên CVAT theo `docs/CVAT_FILTER.md` với điều kiện `width < 20`:* Trên ảnh `img_0161`, bộ lọc gom đúng 3 box ở dòng 2, 3, 4 (kích thước cạnh ngắn tương ứng: 10.3px, 11.4px, 11.9px) — khớp hoàn toàn với 3 cảnh báo `BOX_TINY` của pipeline trong `02_error_list_v1.csv` (ngưỡng `min_box_pixels = 12.0`). Ngưỡng 12px của pipeline chặt chẽ hơn ngưỡng 20px của slide, tránh bắt nhầm vật thể ở xa hợp lệ.
  * *Thuộc tính `can_review`:* Người gán nhãn tích chọn khi gặp ca khó hoặc mơ hồ (vật thể bị che khuất, thiếu sáng, quá xa) cần chuyên viên kiểm tra lại. Trong pipeline tự động, cơ chế tương đương là mô hình phụ tá phát hiện các ca bất thường (`POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`, `POSSIBLE_LOOSE_BOX`) và tính điểm ưu tiên đẩy vào `05_review_queue.csv` cho con người duyệt.
* **Ghi chú sử dụng AI (theo hướng dẫn docs/PROMPTING.md):**
  * *Prompt chính:* Dán trực tiếp docstring từ `pipeline/steps/autofix.py` và test `test_autofix.py`, mô tả đủ 4 ý: (1) định dạng dữ liệu vào (YOLO txt 5 cột số: `class xc yc w h`), (2) quy tắc kiểm & sửa (clip box về $[0, 1]$, drop dòng lỗi định dạng/toạ độ, không can thiệp dòng WARN), (3) kiểu trả về (danh sách dict ghi nhận hành động sửa để ghi `03_fixes.csv`), (4) giới hạn an toàn (chỉ sửa trên bản sao `ds`, tuyệt đối không ghi đè `data/raw`, đọc tham số ngưỡng từ `cfg` không viết cứng số).
  * *Cách kiểm tra code AI (3 bước chặt chẽ):*
    1. **Đọc lướt (Code Review):** Rà soát code để đảm bảo không nuốt lỗi bằng `except: pass`; xác nhận hàm chỉ thao tác trên bản sao `ds` không đè dữ liệu gốc; kiểm tra các tham số ngưỡng đều lấy từ `cfg`.
    2. **Chạy Test TDD:** Chạy `pytest tests/test_<module>.py -q` với các ca bẫy biên (dòng rỗng ở giữa, file chứa `nan/inf`, dòng thiếu cột, box âm, box tràn viền).
    3. **Kiểm tra tính tái lập:** Chạy toàn bộ pipeline hai lần liên tiếp bằng `test_pipeline_e2e.py` và `python -m pipeline.run` để đối chiếu mã băm SHA-1 của dataset xuất ra.
  * *Một lần AI sai và cách xử lý:*
    Khi sinh hàm `fix` trong `autofix.py`, ban đầu AI thực hiện cắt box (`clip_box`) cho cả trường hợp box có toạ độ âm nằm hoàn toàn ngoài ảnh (ví dụ `1 -0.18 0.46 0.04 0.18`). Sau khi kẹp toạ độ về $[0, 1]$, box bị co về chiều rộng $w' = 0$, nhưng AI vẫn ghi dòng box rỗng đó vào file nhãn với action `clip_box`, làm fail test `test_box_fully_outside_is_dropped_not_negative`. Học viên đã phát hiện khi chạy test đỏ, đọc traceback dòng lỗi và bổ sung điều kiện: nếu sau khi clip mà $w \le 10^{-6}$ hoặc $h \le 10^{-6}$ thì tự động chuyển thành action `drop_line` để xoá hẳn dòng nhãn rỗng.
