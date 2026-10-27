# Đối chiếu Google Sheet nghiên cứu với app V2

File nghiên cứu:
https://docs.google.com/spreadsheets/d/1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U/edit

Đã đọc lại ngày 27-10-2026: tab 14_V_GOP_Y có 13 mục, đều Chờ V chốt,
cột ý kiến chưa có nội dung. App chưa đọc/ghi tự động vào file này.
Bảng dưới là bản đối chiếu thiết kế, chưa phải cấu hình đồng bộ.

| Tab nghiên cứu | Phần có trong bản app thử | Phần cần hoàn thiện/chốt |
|---|---|---|
| 00_HUONG_DAN | Hướng dẫn chạy thử trong tài liệu | Hướng dẫn chính thức từng vai trò |
| 01_DU_AN_DON_VI | units (đơn vị) kèm mã dự án | Danh mục dự án riêng nếu cần |
| 02_NGUOI_DUNG | users (người dùng) với 3 vai trò | Phạm vi dự án; sửa/vô hiệu quyền |
| 03_SAN_PHAM | Sản phẩm, SKU và kênh trong hồ sơ key | Danh mục chuẩn; điều kiện cấp phép; nhiều suất |
| 04_LO_BAN_GIAO | Mã lô gắn từng key | Hồ sơ lô độc lập và chứng từ |
| 05_KHO_KEY | Mã hóa, chống trùng, trạng thái, đoạn cuối key | Quy trình đổi khóa; KMS (dịch vụ quản lý khóa mã hóa) |
| 06_TK_MICROSOFT | accounts (tài khoản), đơn vị và người quản lý | Tình trạng xác thực và bàn giao |
| 07_REDEEM_LICENSE | Xác nhận thành công và liên kết tài khoản | Mã license riêng, bản ghi từng lần redeem và lỗi |
| 08_THIET_BI | devices (máy), tem, serial máy/mainboard | Nguồn đối soát và trạng thái thiết bị |
| 09_PHAN_BO | jobs (việc giao KTV), chặn cấp trùng key | Thu hồi/giao lại, phân bổ hàng loạt |
| 10_KICH_HOAT | Trạng thái hiện tại + sự kiện audit | Bảng báo cáo từng lần riêng, quy tắc phê duyệt |
| 11_BAO_HANH | Serial trước/sau, chờ xét và duyệt kích hoạt lại | Hồ sơ hỗ trợ tổng quát và chuyển cả máy |
| 12_NHAT_KY | audit (nhật ký sự kiện) | Chính sách lưu và hiển thị giờ địa phương |
| 13_TU_DIEN_COT | Giải thích tiếng Việt trong file nghiên cứu | Chuẩn hóa toàn bộ nhãn/cột trong app |
| 14_V_GOP_Y | File theo dõi quyết định | Không áp dụng tự động trước khi chốt |

Bản V2-20261027-B bổ sung nhãn tiếng Việt, trang hướng dẫn theo vai trò và dữ liệu giả xuyên suốt. Kết quả kiểm tra được ghi trong PR. Chưa triển khai Google Cloud hoặc xác minh kích hoạt Microsoft thực tế.

## Trình tự tiếp tục

1. Anh Vỹ xem cấu trúc và bổ sung cách vận hành; giữ các ô chưa chốt đúng trạng thái.
2. Xác định Sheet dùng nghiên cứu, báo cáo hay nguồn nhập; chốt chiều đồng bộ và quyền.
3. Chốt mã liên kết giữa key, tài khoản, license, máy, phân công và lần báo cáo.
4. Hoàn thiện giao diện theo từ điển cột, minh họa luồng và hướng dẫn theo vai trò.
5. Kiểm tra lại PostgreSQL (cơ sở dữ liệu quan hệ), đăng nhập Google và phân quyền thật.
6. Cấu hình Google Cloud cùng chi phí, sao lưu và dữ liệu dùng thử được phê duyệt.
7. Chỉ đưa key thật vào khi hoàn tất kiểm tra quy trình, quyền và khôi phục dữ liệu.

Không nối bảng bằng số dòng, tên người hoặc chỉ serial mainboard. Chưa có kết nối
Google Cloud để triển khai trực tuyến và chưa tự kiểm chứng kích hoạt Microsoft.

