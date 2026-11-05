# Đối chiếu Google Sheet với app BẢN QUYỀN

File nghiên cứu:
https://docs.google.com/spreadsheets/d/1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U/edit

Ngày 05-11-2026: app dùng kho bảo mật riêng cho key và trạng thái vận hành. Admin
đọc kế hoạch từ tab 16_KE_HOACH_CAP_PC sau khi xem trước; báo cáo app được ghi
vào các tab 01–12 bằng thao tác riêng. Tab 14 giữ 11 ý kiến chưa chốt. Cấu hình
quyền Google runtime cần được kiểm tra trên dịch vụ triển khai trước khi dùng thật.

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
| 14_V_GOP_Y | File theo dõi quyết định, giữ nguyên khi đồng bộ | Không áp dụng tự động trước khi chốt |
| 15_DONG_BO_APP | Nhật ký các lần ghi bản xuất | Chưa có lịch tự chạy nền |
| 16_KE_HOACH_CAP_PC | Kế hoạch PC và quota SKU theo xã/điểm; Admin xác nhận nạp vào app | Không đưa key đầy đủ hoặc thông tin đăng nhập vào tab này |

Bản V2-20261027-B bổ sung nhãn tiếng Việt, trang hướng dẫn theo vai trò và dữ liệu giả xuyên suốt. Kết quả kiểm tra được ghi trong PR. Chưa triển khai Google Cloud hoặc xác minh kích hoạt Microsoft thực tế.

## Trình tự tiếp tục

1. Anh Vỹ xem cấu trúc và bổ sung cách vận hành; giữ các ô chưa chốt đúng trạng thái.
2. Cấp quyền Google runtime và thử đọc tab 16, xem trước, xác nhận nạp, rồi xuất báo cáo.
3. Kiểm thử một dự án nhỏ với nhiều điểm, PC và SKU trước khi mở rộng dữ liệu.
4. Kiểm tra đồng thời, sao lưu/khôi phục, đăng nhập và phân quyền thật trước khi dùng key thật.

Không nối bảng bằng số dòng, tên người hoặc chỉ serial mainboard. Chưa có kết nối
Google Cloud để triển khai trực tuyến và chưa tự kiểm chứng kích hoạt Microsoft.

