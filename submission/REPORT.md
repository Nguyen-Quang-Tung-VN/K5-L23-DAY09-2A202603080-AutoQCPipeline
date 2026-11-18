# Báo cáo Day 09 — Nguyễn Quang Tùng, 2A202603080

## 1. Kết luận trước
Pipeline đưa ra phán quyết cuối cùng: **HOLD** (mã thoát 10).
* **Số ảnh đầu vào**: Lô dữ liệu thô ban đầu gồm 224 ảnh (`data/raw`).
* **Số ảnh đầu ra dataset sạch**: Sau khi qua cửa intake và autofix, dataset xuất bản nháp tại `submission/export/clean_v1/` giữ lại **203 ảnh** (loại bỏ 21 ảnh gồm: 2 ảnh hỏng, 3 ảnh quá nhỏ, 8 ảnh trùng tuyệt đối, 3 ảnh trùng gần, và 5 ảnh bị rò rỉ từ tập test).
* **Lý do quyết định Hold**: Toàn bộ lỗi bắt buộc nghiêm trọng đã được khắc phục hoàn toàn (`n_errors = 0`). Tuy nhiên, do ngân sách thẩm định của con người có hạn (80 ảnh), trong tổng số 130 ảnh có cảnh báo vẫn còn **44 ảnh** mang các cảnh báo ngữ nghĩa chưa được duyệt. Tỉ lệ cảnh báo tồn đọng là **21.7%** (44/203 ảnh), vượt mức trần an toàn 10.0% (`warn_ratio_hold = 0.10`). Theo đúng quy chuẩn, dữ liệu chỉ được xuất bản nháp để chạy thử nghiệm nội bộ (`manifest.json` ghi `decision: Hold`) chứ chưa được phép phát hành chính thức (Release).

## 2. Lỗi và phân việc
Khi mở xem báo cáo vòng 1 (`02_error_list_v1`), tôi ghi nhận tổng cộng 36 lỗi bắt buộc (`ERROR`) và 171 cảnh báo (`WARN`).
Nguyên tắc phân chia công việc của tôi rất rõ ràng: Việc gì có quy tắc cơ học, xác định 100% thì để máy tự xử lý (autofix/intake). Còn những vấn đề liên quan đến ngữ nghĩa, bối cảnh và thị giác thì bắt buộc phải đưa vào hàng đợi cho con người duyệt.

| Mã lỗi | Số ảnh/dòng | Ai sửa | Vì sao phân việc như vậy |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 ảnh | Máy (`intake`) | File ảnh hỏng (không đọc được header bằng PIL), máy tự loại bỏ ngay cửa vào để tránh crash pipeline. |
| `BAD_SIZE` | 3 ảnh | Máy (`intake`) | Kích thước cạnh ngắn < 250px không đủ độ phân giải để train YOLO, máy tự loại bỏ. |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (`intake`) | Trùng lặp tuyệt đối từng byte (MD5 hash), máy tự xoá bản trùng để tránh lãng phí tài nguyên tính toán. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (`intake`) | Ảnh trùng gần đúng (khoảng cách pHash $\le 6$), máy loại ảnh biến thể để tránh thiên lệch (bias) mô hình. |
| `LEAK_TEST` | 5 ảnh | Máy (`intake`) | Ảnh trùng với kho test/val, bắt buộc máy phải loại bỏ ngay để chống "học tủ" (data leakage). |
| `BAD_FORMAT` | 3 dòng | Máy (`autofix`) | Dòng nhãn thiếu cột toạ độ hoặc dính giá trị NaN/Inf, máy xoá dòng rác theo chuẩn YOLO. |
| `BAD_CLASS_ID` | 6 dòng | Máy (`autofix`) | Class ID ngoài khoảng 0..3 (xuất hiện id 93, -1, 7, 4), máy xoá dòng sai cú pháp xác định. |
| `BAD_CLASS_NAME` | 2 lỗi | Máy (`autofix`) | Tên lớp trong `data.yaml` viết hoa sai chuẩn ('Person', 'Bus'), máy chuẩn hoá về danh mục gốc. |
| `BOX_ZERO` | 4 dòng | Máy (`autofix`) | Box có width hoặc height $\le 0$ (diện tích bằng 0), máy xoá dòng vì không có ý nghĩa thực tế. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (`autofix`) | Box tràn nhẹ ra ngoài mép ảnh, máy tự tính toán xén toạ độ về $[0, 1]$ (`clip_box`). |
| `DUP_BOX` | 7 dòng | Máy (`autofix`) | Box cùng lớp đè khít lên nhau (IoU > 0.9), máy giữ box đầu và xoá box trùng phía sau. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (Hàng đợi) | Ảnh thiếu file nhãn; máy tuyệt đối không được tự bịa nhãn mà chuyển diện `needs_label` để người gán. |
| `BOX_TINY` | 6 box | Người (Hàng đợi) | Cảnh báo box quá bé (< 12px), cần mắt người nhìn xem là vật thể ở xa thật hay chỉ là vết nhiễu ảnh. |
| `BOX_HUGE` | 3 box | Người (Hàng đợi) | Cảnh báo box bao trùm > 95% diện tích ảnh, cần người kiểm tra xem do chụp cận cảnh hay do gán nhầm bao trùm ảnh. |
| `EMPTY_LABEL` | 12 ảnh | Người (Hàng đợi) | File nhãn rỗng; người duyệt cần thẩm định đây là ảnh nền (background không vật thể) hay do người gán nhãn bỏ sót. |
| `CLASS_RARE` | 4 lớp | Người (Hàng đợi) | Cảnh báo mất cân bằng tập dữ liệu khi có lớp chỉ xuất hiện 1-2 lần trong toàn bộ tập. |
| `POSSIBLE_MISSING` | 68 vị trí | Người (Hàng đợi) | Model phụ tá phát hiện vật thể rõ ràng nhưng nhãn không có; cần người duyệt xem có phải bỏ sót không. |
| `POSSIBLE_WRONG_CLASS` | 18 vị trí | Người (Hàng đợi) | Cùng vị trí vật thể nhưng nhãn và model khác lớp nhau; cần người phân xử xem bên nào đúng. |
| `POSSIBLE_LOOSE_BOX` | 31 dòng | Người (Hàng đợi) | Box nhãn vẽ lỏng hoặc lệch (IoU < 0.5) so với model, cần người chỉnh lại viền bao cho khít. |
| `POSSIBLE_FALSE_POS` | 29 dòng | Người (Hàng đợi) | Box nhãn nằm ở vị trí mà model không thấy vật thể nào; cần người xem lại có gán nhầm vật thể lạ hay không. |

**Cơ chế xếp thứ tự ưu tiên của hàng đợi (`05_review_queue.csv`):**
Khi mở file hàng đợi duyệt, tôi thấy cách hệ thống tính điểm rất hợp lý:
* Các ảnh thiếu hẳn file nhãn (`NEEDS_LABEL`) lập tức được cộng 10 điểm để nhảy lên nhóm đầu. Điều này hoàn toàn dễ hiểu vì nếu ảnh thiếu file nhãn không được xử lý, nó sẽ bị tính là lỗi bắt buộc (`ERROR`), khiến toàn bộ pipeline bị chặn ở trạng thái Rework.
* Tiếp theo là các ảnh "dính chùm" nhiều lỗi: điển hình là ảnh `img_0020` đứng đầu danh sách với điểm ưu tiên 14.528 vì vừa dính `FIXED_DROP_LINE`, vừa dính cả `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`.
* Với ngân sách cố định là 80 ảnh, người duyệt đã xử lý hết 100% (6/6) ảnh thiếu file nhãn và 74 ảnh có độ bất thường cao nhất. 50 ảnh còn lại ở cuối hàng đợi (tương ứng 44 ảnh mang cảnh báo nhẹ) đành phải gác lại do hết ngân sách.

## 3. Calibration
Tôi chạy sweep tham số trên tập `data/calib/` (39 ảnh có chèn lỗi mẫu) để tìm ngưỡng cân bằng bằng thực nghiệm:

| Tham số | Giá trị ban đầu | Giá trị tôi chọn | P / R (trước → sau) | Phân tích đánh đổi & Lý do tôi chọn |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **6** | P: 1.00 → 1.00<br>R: 0.50 → 0.67 | Ở mức 2, Recall chỉ đạt 0.50 (bỏ sót nửa số ảnh trùng). Nâng lên 6 giúp Recall tăng lên 0.67 (bắt thêm được 2 ảnh biến thể trong tập raw) mà Precision vẫn giữ tuyệt đối 1.00. Vì bước này tự động xoá ảnh (`remove_image`), tôi kiên quyết giữ Precision = 1.00 để không bao giờ xoá nhầm ảnh sạch. |
| `second_opinion.conf` | 0.25 | **0.50** | MISSING P: 0.50 → 0.57<br>WRONG_CLASS P: 0.56 → 0.56<br>R: 1.00 → 1.00 | Ở mức 0.25, model phụ tá quá nhạy, sinh tới 273 cảnh báo làm quá tải hàng đợi. Nâng lên 0.50 giúp giảm 37% cảnh báo rác (còn 171 cảnh báo), Precision của MISSING tăng từ 50% lên 57%, đặc biệt là vẫn giữ nguyên Recall = 1.00 (không bỏ sót lỗi thiếu nhãn thật nào). |

**Chỗ Calibration có thể đánh lừa người làm:**
Nếu chỉ nhìn máy móc vào bảng sweep để chọn F1 cao nhất, tôi rất dễ bị dụ chọn `phash_dist = 16` (F1 trên tập calib lên tới 0.91, Recall 0.83). Tuy nhiên, tôi nhận ra đây là một cái bẫy overfitting: tập calib chỉ có 39 ảnh với các ảnh trùng nhân tạo khá rành mạch. Trong thực tế ở tập raw 224 ảnh, khoảng cách Hamming 16 là quá lỏng — hai bức ảnh chụp hai góc phố khác nhau nhưng có cùng tông màu trời và mặt đường xám rất dễ bị coi là trùng nhau và bị xoá oan. Mở xem ảnh thực tế, tôi thấy ngưỡng 6 là giới hạn an toàn nhất để vừa loại bỏ đúng ảnh biến thể co giãn nhẹ (như cặp `img_0076` và `img_0042` có phash dist = 0), vừa bảo vệ toàn vẹn các ảnh phong cảnh độc lập.

Tương tự, với `second_opinion.conf`, nếu tham lam đẩy lên 0.7 hay 0.8 để giảm số lượng cảnh báo xuống hàng đợi, Recall của `POSSIBLE_MISSING` sẽ tụt mạnh từ 1.00 xuống 0.88 rồi 0.75 (tức bỏ sót tới 25% lỗi thiếu nhãn của người gán nhãn). Điểm ngọt thực tế là 0.50.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
* **Thực nghiệm chứng minh Gate chặn đúng:**
  Để kiểm chứng cửa chặn, tôi giả lập kịch bản hoàn toàn không có người duyệt bằng lệnh:
  `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`
  Kết quả thực tế: Vì ngân sách bằng 0, không có ai duyệt nên 6 ảnh thiếu file nhãn (`MISSING_LABEL_FILE`) còn nguyên. Khi sang vòng QC 3, hệ thống ghi nhận `n_errors = 6`. Gate đã lập tức kích hoạt, kết luận **REWORK**, trả về mã thoát **20** và hoàn toàn **không xuất** thư mục dataset `work/exp_nb`. Điều này chứng minh cửa chặn hoạt động hoàn toàn tự động, độc lập và bảo vệ dữ liệu cực kỳ nghiêm ngặt.
* **3 điểm mù mà pipeline hiện tại chưa bắt được:**
  1. *Box vẽ lỏng nhẹ hoặc lệch viền nhưng IoU vẫn $\ge 0.50$*: Khi dùng script `viz_labels.py` soi ảnh `img_0030`, tôi thấy một số box người đi bộ bị vẽ thụng xuống dưới chân, nhưng vì IoU với box dự đoán của model vẫn đạt tầm 0.55 (vượt qua ngưỡng lỏng `iou_loose = 0.50`), pipeline coi như bình thường và bỏ qua.
  2. *Vật thể bị che khuất một phần (occlusion) hoặc trong bóng tối*: Ở những góc khuất phức tạp, cả người gán nhãn ban đầu lẫn model phụ tá `yolo26l` đều nhìn sót hoặc cùng đoán nhầm một lớp. Hiện tượng này gọi là "đồng thuận sai" (`silent false agreement`) — máy tin tưởng model tham chiếu nên khi cả hai cùng sai, pipeline hoàn toàn bất lực.
  3. *Ảnh trùng bị cắt cúp quá mạnh (crop mất trên 70-80% diện tích)*: Thuật toán pHash dựa trên các hệ số tần số thấp của biến đổi cosine rời rạc 2D. Khi ảnh bị crop sâu vào một góc nhỏ, chữ ký băm sẽ thay đổi hoàn toàn khiến cửa intake không thể phát hiện được sự trùng lặp bối cảnh.

## 5. Train: raw vs clean
Tôi đã huấn luyện mô hình `yolo26n` trên Google Colab (sử dụng GPU T4) với cấu hình đồng nhất: 20 epochs, batch 16, imgsz 640 qua 2 seed ngẫu nhiên (seed 0 và seed 1). Đánh giá độc lập trên cùng tập Test (100 ảnh):

| Biến thể | Số ảnh train | Số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|
| **raw** (chưa lọc) | 224 | 2 | **0.726** ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| **clean** (sau pipeline) | 203 | 2 | **0.695** ± 0.010 | 0.482 ± 0.007 | 0.726 ± 0.005 | 0.619 ± 0.016 |

Chênh lệch mAP50 (`clean` − `raw`) = **-0.031**.

**Đánh giá thực nghiệm một cách trung thực:**
Ban đầu khi thấy điểm mAP50 của clean thấp hơn raw 3.1%, tôi cũng hơi bất ngờ. Tuy nhiên, khi nhìn vào độ lệch chuẩn giữa các seed của clean ($\pm 0.010$) và độ lệch precision của raw ($\pm 0.061$), tôi nhận thấy mức chênh -0.031 này nằm sát ranh giới của độ nhiễu thống kê trên một tập test nhỏ (chỉ 100 ảnh).
Tôi rút ra 2 nguyên nhân cốt lõi giải thích cho hiện tượng này:
1. *Tập raw được "học tủ" do rò rỉ dữ liệu (Data Leakage)*: Trong tập `raw` có 5 ảnh trùng trực tiếp với tập test (`LEAK_TEST`) và 8 ảnh trùng lặp tuyệt đối. Khi train trên raw, mô hình đã vô tình ghi nhớ trước câu hỏi của đề thi, dẫn đến điểm mAP cao giả tạo. Trong khi đó, tập clean đã bị pipeline thanh lọc triệt để các ảnh rò rỉ này nên điểm số phản ánh năng lực khái quát hoá trung thực của mô hình.
2. *Lượng dữ liệu huấn luyện bị sụt giảm*: Tập clean bị loại bỏ 21 ảnh (giảm gần 10% tổng lượng mẫu). Với một dataset vốn đã rất nhỏ (~200 ảnh) và thời gian train chỉ vỏn vẹn 20 epoch, việc mất đi 10% lượng ảnh làm giảm mật độ mẫu ở một số góc chụp hiếm, khiến mô hình chưa kịp hội tụ bù đắp lại.
* *Cách tôi kiểm chứng giả thuyết:* Loại bỏ 5 ảnh leak ra khỏi tập test độc lập rồi evaluate lại cả hai mô hình raw và clean; khi đó điểm của raw chắc chắn sẽ tụt dốc.

## 6. Quyết định và ghi chú AI
* **Quyết định của tôi:** Đồng thuận với kết luận của Gate, giữ trạng thái **HOLD**. Dataset `submission/export/clean_v1/` chỉ lưu hành nội bộ dưới dạng bản nháp (`manifest.json` ghi nhận `decision: Hold`).
* **Kế hoạch hành động để nâng lên Release:**
  1. Xin cấp thêm ngân sách duyệt từ 80 ảnh lên tối thiểu 130 ảnh để con người xử lý nốt 44 ảnh còn tồn đọng cảnh báo trong hàng đợi, đưa tỷ lệ cảnh báo về dưới ngưỡng 10%.
  2. Nếu không có thêm kinh phí nhân sự, đội ngũ kỹ thuật cần họp rà soát mức độ rủi ro của 44 cảnh báo còn lại; nếu rủi ro trong tầm chấp nhận được, nhóm có thể cập nhật lại guideline dự án để nới ngưỡng `warn_ratio_hold` từ 10% lên 25%.
* **(Thưởng +2) Thực nghiệm CVAT:**
  * Tôi đã thử nghiệm quy trình lọc box trên CVAT theo hướng dẫn `docs/CVAT_FILTER.md`. Khi áp dụng bộ lọc `width < 20`, CVAT bắt trúng các box nhỏ li ti. Điển hình trên ảnh `img_0161`, bộ lọc này gom đúng 3 box ở dòng 2, 3, 4 (kích thước thực tế lần lượt là 10.3px, 11.4px, 11.9px) — khớp hoàn toàn với 3 cảnh báo `BOX_TINY` mà pipeline của tôi đã tìm ra (với ngưỡng `min_box_pixels = 12.0`). So với ngưỡng 20px của slide thì ngưỡng 12px trong pipeline của tôi chặt chẽ hơn, tránh bắt nhầm các vật thể ở xa hợp lệ.
  * Về thuộc tính `can_review`: Người gán nhãn đánh dấu `can_review = true` khi gặp các ca khó (vật thể bị che khuất nhiều, ánh sáng yếu, góc chụp lạ) cần người có chuyên môn cao hơn thẩm định lại. Trong pipeline tự động, cơ chế tương đương chính là việc model phụ tá phát hiện các ca bất thường (`POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS`, `POSSIBLE_LOOSE_BOX`) rồi tự động tính điểm ưu tiên và đẩy vào `05_review_queue.csv` để con người vào xử lý.
* **Ghi chú về việc sử dụng AI:**
  * *Prompt chính tôi sử dụng:* "Viết 4 module `label_format.py`, `gate.py`, `autofix.py`, `second_opinion.py` theo đúng docstring mẫu và hướng tiếp cận TDD, áp dụng kỹ thuật lập trình phòng thủ để xử lý các ca biên (dòng rỗng, tràn viền box, toạ độ NaN) và tuyệt đối không ghi đè dữ liệu gốc `data/raw/`."
  * *Cách tôi kiểm tra code AI:* Tôi chạy toàn bộ 79 ca unit test bằng lệnh `pytest -q`, đồng thời tự viết thêm các ca kiểm thử khó (như 1 dòng dính đồng thời cả lỗi class lẫn toạ độ tràn, file có dòng trắng xen giữa) và soi chéo từng dòng số liệu trong `08_summary.json` với `manifest.json`.
  * *Một lần AI làm chưa chuẩn:* Trong script `scripts/check_submission.py`, chuỗi đường dẫn tệp trên Windows dùng dấu gạch ngược `\` khiến code so khớp đường dẫn bị lỗi khi so với danh sách mẫu trong `_protected.json` (dùng `/`). Tôi đã phát hiện và chuẩn hoá lại bằng hàm `.as_posix()` để chạy trơn tru trên mọi hệ điều hành.
