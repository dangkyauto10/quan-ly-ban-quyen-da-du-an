# Đồng bộ Google Sheet — V2-20261027-C

Đích nghiên cứu: https://docs.google.com/spreadsheets/d/1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U/edit

## Đã làm

- Bộ xuất dữ liệu đọc một snapshot (bản chụp dữ liệu nhất quán) của app.
- Đồng bộ một chiều app → 12 tab dữ liệu theo đúng tiêu đề cột file nghiên cứu.
- Admin (quản trị) có màn hình Đồng bộ Google Sheet để xuất JSON (tệp dữ liệu có
  cấu trúc), mở file nghiên cứu và đồng bộ khi runtime có quyền Google.
- Các mã APP- thuộc app: cập nhật theo mã, không thêm bản sao khi gửi lại.
- Không xóa dòng nghiên cứu/mẫu khác; không ghi 13_TU_DIEN_COT hoặc 14_V_GOP_Y.
- Có 15_DONG_BO_APP ghi thời điểm, nguồn, số bản ghi và loại dữ liệu.
- Một bản xuất 37 bản ghi từ demo được B ghi qua kết nối Drive để anh Vỹ nghiên cứu.
  Các mã mẫu cũ vẫn giữ; xem dòng APP- khi đối chiếu bản xuất từ app.

## Phân biệt một lần ghi mẫu và kết nối vận hành

Lần ghi mẫu dùng kết nối Google Drive của cuộc trò chuyện, không phải thông tin
đăng nhập mà app chạy trên Cloud Run có thể tự dùng. V2 chưa triển khai trực tuyến.
Chưa có đồng bộ tự chạy nền, lịch định kỳ hoặc đọc Sheet ngược vào app.
Màn hình cho Admin bấm đồng bộ một chiều khi đã cấu hình danh tính runtime.
Demo cá nhân chỉ cho tải dữ liệu, không ghi vào file dùng chung để tránh các phiên
minh họa có mã ngẫu nhiên làm nhân bản dữ liệu chung.

## Cấp quyền cho app khi triển khai

1. Bật Google Sheets API (cổng để phần mềm làm việc với bảng tính) trong project
   Google Cloud của app.
2. Trên Cloud Run, chọn runtime service account (tài khoản dịch vụ chạy ứng dụng).
3. Trong file Google Sheet, chia sẻ quyền Người chỉnh sửa cho đúng email tài khoản
   dịch vụ đó. App cần quyền trên đúng file; quyền Google Cloud riêng không tự cấp
   quyền sửa Google Drive.
4. Runtime ưu tiên ADC (thông tin xác thực Google do môi trường cấp), không cần
   tải khóa JSON dài hạn. Khi chạy ở nơi khác có thể cấu hình secret
   [google_service_account], không đưa private_key vào GitHub hoặc Google Sheet.
5. Có thể chỉ định file đích trong secret:

       [google_sheets]
       spreadsheet_id = "1H5j9IK1U7CBef94utPNbhUQ1A31bcQD03yCEaP2L7-U"

6. Admin mở Đồng bộ Google Sheet, kiểm tra số lượng và bấm đồng bộ; xem kết quả ở
   15_DONG_BO_APP. Không dùng file minh họa làm kho thực tế trước khi chốt vận hành.

## Cách ghi và bảo toàn dữ liệu

- Kiểm tra đủ tab và đúng header (tiêu đề cột) trước khi gửi batchUpdate (ghi nhiều
  thay đổi trong một lần). Sai cột hoặc mã trùng sẽ dừng, không tự đoán cấu trúc.
- Chỉ upsert (thêm hoặc cập nhật theo mã) dòng APP-. Ý kiến V và mẫu cũ giữ nguyên.
- Khi sửa dòng APP- trực tiếp trên Sheet, lần đồng bộ sau sẽ lấy dữ liệu app để
  cập nhật lại. Ghi đề xuất thay đổi ở 14_V_GOP_Y, chờ chốt cơ chế nhập liệu.
- Không xóa hồ sơ APP- nếu snapshot không còn dòng đó; cần bổ sung quy tắc thu hồi
  sau khi chốt nghiệp vụ. Do đó Sheet là sổ báo cáo cộng dồn/cập nhật, chưa cam kết
  phản ánh xóa dữ liệu từ app.
- Chỉ key đã che và dữ liệu được phép xuất đi vào payload (gói dữ liệu). Không đọc
  cột cipher (key đã mã hóa) hoặc fingerprint (dấu vân tay kiểm tra trùng) để xuất.
- Không xuất link minh chứng; che mẫu key Microsoft đủ 25 ký tự cả trong ghi chú.
- Chuỗi gửi bằng stringValue (văn bản nguyên nghĩa), không gửi formulaValue
  (công thức), tránh nội dung do người dùng nhập chạy thành công thức trên Sheet.
- Lô bàn giao, tên người hiển thị, xác thực tài khoản, nguồn serial và trạng thái
  thiết bị chưa có đủ trường trong app: ô chưa biết để trống hoặc ghi chờ xác minh,
  không tự coi là đã được nhà cung cấp xác nhận. Số key lô là số đang lưu trong app.
- Quyền Microsoft và trạng thái kích hoạt vẫn do người thao tác xác minh thực tế.

## Giới hạn còn cần xác minh

Đã kiểm tra bộ xuất, che key, quyền Admin, giữ dòng người dùng, ghi lại không tạo bản
sao, sai header phải dừng, cùng các kiểm tra bản app. Kết nối runtime bằng tài khoản
dịch vụ/ADC chưa được thử với Google Cloud thật vì chưa được cấu hình quyền.
Hai người cùng bấm đồng bộ khác snapshot chưa có khóa phân tán; vận hành bản đầu
chỉ giao một Admin điều phối đồng bộ, cần hoàn thiện cơ chế đồng thời trước mở rộng.
