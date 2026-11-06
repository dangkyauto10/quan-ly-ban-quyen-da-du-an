# Kết nối app BẢN QUYỀN với Google Sheet

Google Sheet: https://docs.google.com/spreadsheets/d/1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U/edit

## Phân công dữ liệu

- Tab `16_KE_HOACH_CAP_PC` là nguồn kế hoạch: dự án, đơn vị được cấp, xã/điểm,
  số PC và quota Windows/Office/Antivirus theo SKU.
- Admin bấm đọc, xem trước rồi nạp kế hoạch vào app. App kiểm tra định dạng, SKU,
  số lượng theo điểm và tổng quota so với kho key.
- Tab `17_TAI_KHOAN_MS` là danh sách email Microsoft nhập theo lô, theo Mã dự án và
  Tên đơn vị được cấp. Admin xem trước và xác nhận nạp sau khi kế hoạch tab 16 đã có.
- App quản lý Windows, Office và Antivirus (diệt virus) theo sản phẩm/SKU, key,
  phương thức kích hoạt và license riêng. Key đầy đủ được mã hóa trong kho app.
  Tab 17 chỉ đưa email Microsoft và người quản lý vào app; app không lưu mật khẩu
  hoặc MFA. Không ghi key đầy đủ, mật khẩu hoặc MFA lên Sheet.
- Báo cáo do app tạo được ghi theo mã `APP-` vào các tab `01`–`12`; tab `08` có
  thêm mã và tên xã/điểm của PC. Tab `15_DONG_BO_APP` ghi lần xuất báo cáo.
- Sheet không đọc kết quả ngược từ các tab báo cáo để thay đổi hồ sơ trong app.
  Kế hoạch và danh sách email chỉ được lấy từ tab 16/17 sau thao tác xác nhận của Admin.

## Mẫu tab kế hoạch

Mỗi dòng là một điểm nhận và một SKU. Khi một điểm có nhiều SKU, lặp lại thông tin
dự án, đơn vị, điểm và số PC trên từng dòng. Có thể để trống Phần mềm, SKU và số
license để khai báo điểm trước khi phân bổ phần mềm.

Các cột phải giữ nguyên thứ tự và tên:

1. Mã dự án
2. Tên dự án
3. Tên đơn vị được cấp
4. Mã xã/điểm
5. Tên xã/phường/đơn vị
6. Số PC tại điểm
7. Phần mềm: Windows, Office hoặc Antivirus
8. SKU
9. Số license được cấp

Mã dự án + tên đơn vị + mã xã/điểm nhận diện một điểm. Phần mềm + SKU nhận diện
một quota. Số PC phải là số nguyên dương; số license là số nguyên từ 0 đến số PC.
Không nhập công thức vào tab kế hoạch.

## Mẫu danh sách tài khoản Microsoft

Tab `17_TAI_KHOAN_MS` gồm: Mã dự án, Tên dự án, Tên đơn vị được cấp, Email tài khoản
Microsoft, Người quản lý tài khoản. Email phải duy nhất trong lô; đơn vị phải trùng
chính xác với kế hoạch đã nạp. Có thể nạp lặp lại cùng danh sách để app bỏ qua các
dòng đã khớp. Nếu email đã tồn tại ở đơn vị/người quản lý khác, app dừng nạp để Admin
đối chiếu thay vì tự chuyển dữ liệu. Không nhập mật khẩu, mã MFA, key hoặc recovery code.

Tab 17 phục vụ tài khoản Microsoft dùng cho Office Retail đã redeem. Admin giao
riêng từng tài khoản đã redeem cho một KTV. Mọi license Office trên một PC phải do
cùng KTV nhận tài khoản đó phụ trách. Windows và Antivirus được theo dõi theo SKU
và luồng trực tiếp/theo nhà cung cấp; không ép vào luồng redeem Microsoft. Không
thể thu hồi tài khoản KTV khi còn máy chưa kích hoạt hoặc chưa QC đóng gói.

## Đồng bộ báo cáo

Admin dùng trang “Đồng bộ Google Sheet” để ghi báo cáo từ app. Các tab `01`–`12`
phải giữ nguyên tiêu đề cột theo schema trong `license_app/sheet_schema.json`.
Các dòng có mã `MAU-` được giữ làm ví dụ; dòng `APP-` được cập nhật theo mã.
Không sửa trực tiếp dòng `APP-`, vì lần xuất sau sẽ ghi lại theo dữ liệu app.

Google Sheets API cần được bật. Tài khoản runtime của app phải có quyền Editor trên
file. Mặc định app dùng spreadsheet ID ở `SHEET_ID`; secret
`google_sheets.spreadsheet_id` có thể ghi đè. Demo không đọc kế hoạch thật hoặc ghi
báo cáo lên file dùng chung.

## Lưu ý vận hành

- Thay đổi ở tab 16 chỉ vào app khi Admin bấm đọc và nạp lại.
- Điểm không có trong tab 16 được giữ nguyên trong app; không dùng thao tác nạp để
  xóa hồ sơ cũ. SKU đã gán cho PC không thể bị xóa hoặc giảm thấp hơn số đã gán.
- Dữ liệu PC và license trong app chưa tự xác minh trạng thái Microsoft. Người thao
  tác vẫn phải kiểm tra kết quả thực tế.
- KTV gửi lô tới trạm in USB, xác nhận đã nhận tem, sau đó xác nhận riêng từng PC
  rằng serial khớp, hai tem đã dán đúng thân máy/vỏ hộp và máy đã đóng hộp. QC không
  thể nhận PC trước xác nhận này. Nếu bảo hành thay mainboard hoặc QC yêu cầu làm lại,
  app giữ lô tem cũ, cho phép tạo cặp tem mới và lưu từng lần trong nhật ký.
- Giai đoạn bản quyền kết thúc khi QC đối chiếu serial/tem và xác nhận đóng gói.
  Vận chuyển, giao điểm và lắp đặt thuộc app QUẢN LÝ DỰ ÁN.

