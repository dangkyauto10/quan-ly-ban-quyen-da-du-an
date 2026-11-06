# Đối chiếu Google Sheet với app BẢN QUYỀN

Google Sheet đang dùng:
https://docs.google.com/spreadsheets/d/1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U/edit

App quản lý ba nhóm phần mềm: Windows, Microsoft Office và Antivirus (diệt virus).
Key, SKU, luồng kích hoạt, license, PC, KTV, tem, QC và bảo hành được theo dõi
trong app. Tài khoản Microsoft nhập theo lô tại tab 17 để dùng trong luồng Office
Retail đã redeem; không lưu mật khẩu hoặc mã MFA trong Sheet. Windows và Antivirus
có thể dùng luồng kích hoạt theo nhà cung cấp, tùy SKU và chứng từ thực tế.

## Phân vai Sheet và app

| Tab | Vai trò | Hướng dữ liệu |
|---|---|---|
| `00_HUONG_DAN` | Hướng dẫn xem và vận hành | Tham khảo |
| `01_DU_AN_DON_VI`–`12_NHAT_KY` | Báo cáo đơn vị, sản phẩm, key đã che, tài khoản Microsoft, redeem, PC, phân bổ, kích hoạt, bảo hành và nhật ký | App → Sheet |
| `15_DONG_BO_APP` | Nhật ký lần đồng bộ, số bản ghi và kết quả | App → Sheet |
| `16_KE_HOACH_CAP_PC` | Đơn vị được cấp, xã/điểm, số PC, phần mềm/SKU và số license | Sheet → app sau khi Admin xem trước và xác nhận |
| `17_TAI_KHOAN_MS` | Email tài khoản Microsoft và người quản lý theo dự án/đơn vị | Sheet → app sau khi Admin xem trước và xác nhận |

Các tab `13_TU_DIEN_COT` và `14_V_GOP_Y` đã được gỡ khỏi Sheet chính để gọn phần
theo dõi. Bản sao lưu trước khi dọn giữ nguyên nội dung cũ.

## Điều kiện nạp dữ liệu

- Tab 16 mỗi dòng là một điểm và một SKU. Giá trị phần mềm là `Windows`, `Office`
  hoặc `Antivirus`; số lượng PC phải là số nguyên dương, số license từ 0 đến số PC.
- Tab 17 mỗi dòng là một tài khoản Microsoft gắn với dự án và đơn vị đã nạp ở tab 16.
  Email phải hợp lệ và không trùng trong danh sách. Không nhập mật khẩu, mã MFA,
  recovery code hoặc key đầy đủ.
- App kiểm tra tiêu đề, dữ liệu, quota và trùng lặp. Admin phải đọc/xem trước rồi
  xác nhận; thay đổi Sheet sau bước xem trước sẽ buộc đọc lại.
- KTV nhận tài khoản Office đã redeem theo phân công; từng PC giữ cùng một KTV từ
  kích hoạt tới xác nhận dán tem, đối serial và đóng hộp. Windows và Antivirus được
  theo dõi bằng SKU/license riêng và luồng của nhà cung cấp.

## Đồng bộ báo cáo

Trang “Đồng bộ Google Sheet” ghi dữ liệu từ app vào các tab 01–12 theo mã `APP-`;
tab 15 ghi nhận lần đồng bộ. Dòng mẫu hoặc dòng quản trị không có mã `APP-` được
giữ nguyên. Sheet không đọc báo cáo ngược để sửa trạng thái app; nguồn dữ liệu vận
hành chính là cơ sở dữ liệu của app. Key đầy đủ, mật khẩu và mã MFA không được xuất.

Tài khoản chạy app cần quyền Editor trên file và quyền gọi Google Sheets API. Khi
kiểm thử, dùng dữ liệu giả; chỉ nạp key thật sau khi V xác nhận môi trường, quyền
đăng nhập, cơ sở dữ liệu dùng chung và sao lưu/khôi phục đã sẵn sàng.
