"""Vietnamese guidance for the currently implemented preview, not final policy."""
ROLE_NAMES = {'QC':'Bộ phận kiểm tra độc lập', 'ADMIN': 'Admin (quản trị)', 'OPERATOR': 'Người quản lý redeem (quy đổi key)', 'KTV': 'KTV (kỹ thuật viên)', 'PRINT':'Trạm in tem'}
FIELD_NAMES = {
    'id':'Mã hồ sơ', 'project':'Mã dự án', 'project_name':'Tên dự án', 'name':'Tên đơn vị', 'email':'Email',
    'role':'Vai trò', 'active':'Đang được cấp quyền', 'unit_id':'Mã đơn vị',
    'owner':'Người quản lý tài khoản', 'batch':'Mã lô bàn giao', 'product':'Phần mềm',
    'sku':'Phiên bản / SKU (mã sản phẩm)', 'channel':'Kênh cấp phép', 'route':'Cách xử lý',
    'tail':'5 ký tự cuối key', 'state':'Trạng thái', 'account_id':'Mã tài khoản Microsoft',
    'reference':'Căn cứ / xác nhận', 'expires':'Ngày hết hạn', 'asset_tag':'Mã tem máy',
    'serial':'Serial máy (số nhận dạng)', 'board_serial':'Serial mainboard (bo mạch chủ)',
    'model':'Hãng / model (kiểu máy)', 'license_id':'Mã bản quyền', 'device_id':'Mã máy',
    'ktv':'KTV được giao', 'error_code':'Mã lỗi', 'note':'Nội dung báo cáo',
    'evidence':'Link minh chứng', 'unit':'Tên đơn vị', 'account':'Email Microsoft được giao',
    'at':'Thời điểm (UTC — giờ quốc tế)', 'actor':'Người thao tác', 'action':'Thao tác',
    'entity':'Mã hồ sơ liên quan', 'details':'Chi tiết sự kiện',
}
ACTION_NAMES = {
    'ADD_USER':'Thêm người dùng', 'UPDATE_USER':'Cập nhật quyền thành viên',
    'CLAIM_CHECK':'Nhận máy kiểm tra','RELEASE_CHECK':'Trả lượt kiểm tra',
    'PACK_PC':'Hoàn tất đóng gói','INSPECT_PC_FAILED':'Kiểm tra không đạt',
    'INSPECT_PC':'Kiểm tra kỹ thuật','SET_PC_PLAN':'Lập kế hoạch PC','NUMBER_PC':'Cấp số thứ tự PC', 'ADD_UNIT':'Thêm đơn vị', 'ADD_ACCOUNT':'Thêm tài khoản Microsoft',
    'IMPORT_BATCH':'Nhập lô key', 'VERIFY':'Xác nhận kiểm tra', 'REVEAL_KEY':'Xem key đầy đủ',
    'REDEEM_CONFIRMED':'Ghi nhận redeem thành công', 'ADD_DEVICE':'Tạo hồ sơ máy',
    'ASSIGN':'Phân bản quyền và giao việc', 'ACTIVATION_SUCCESS':'Báo kích hoạt thành công',
    'ACTIVATION_FAILED':'Báo kích hoạt thất bại', 'BOARD_REPLACED':'Ghi thay mainboard',
    'BIND_BOARD_SERIAL':'Gắn serial mainboard vào việc KTV',
    'KTV_LABELS_APPLIED':'KTV xác nhận dán tem và đóng hộp',
    'IMPORT_UNIT_PLAN':'Nạp đơn vị, điểm và phân bổ license',
    'QUEUE_LABEL_BATCH':'KTV gửi lô tem vào hàng đợi',
    'PRINT_LABEL_BATCH':'Trạm in xác nhận in lô tem',
    'COLLECT_LABEL_BATCH':'KTV xác nhận nhận lô tem',
    'APPROVE_REACTIVATION':'Duyệt kích hoạt lại',
}
PAGE_GUIDES = {
    'Tổng quan': ('Xem tình trạng kho và công việc', [
        'Xem số bản quyền chưa phân bổ, đã giao máy và đã kích hoạt.',
        'Báo cáo CSV (tệp bảng mở được bằng Excel) chỉ chứa thông tin quản lý đã che key.',
        'Số thành công phản ánh báo cáo KTV đã ghi, chưa tự truy vấn trạng thái Microsoft.']),
    'Đơn vị & tài khoản': ('Lập danh mục nhận PC và phân bổ bản quyền', [
        'Nhập mã/tên dự án, đơn vị được cấp, xã/phường/điểm nhận, số PC và quota phần mềm/SKU tại tab 16_KE_HOACH_CAP_PC trong Google Sheet.',
        'Admin đọc, xem trước rồi xác nhận nạp kế hoạch vào app; số license phải nằm trong kho key đã nhập.',
        'Công đoạn BẢN QUYỀN kết thúc khi PC được kích hoạt, đối chiếu thiết bị/serial, ghép đúng cặp tem và QC xác nhận đóng gói. Sau đó mới chuyển sang QUẢN LÝ DỰ ÁN để vận chuyển và lắp đặt.',
        'Admin hoặc người quản lý redeem thêm email Microsoft và người phụ trách tài khoản.',
        'Mật khẩu và MFA (xác thực nhiều bước) do người quản lý tài khoản giữ bên ngoài app.']),
    'Kế hoạch PC theo điểm': ('Theo dõi số PC đã phân bổ theo từng điểm', [
        'Số PC theo từng điểm lấy từ danh sách Excel ở Đơn vị & tài khoản. Màn hình này theo dõi PC đã khai báo, đánh số tem và QC đóng gói.',
        'Số tem chạy liên tục theo tổng PC của đơn vị được cấp, kể cả khi đơn vị có nhiều xã/phường/điểm nhận.']),
    'Kho key': ('Nhận bàn giao và kiểm tra', [
        'Admin nhập mã lô, loại phần mềm, phiên bản/SKU, kênh cấp phép và từng key.',
        'Chọn đúng luồng: Office bán lẻ đã xác minh mới đưa vào redeem tài khoản.',
        'Người kiểm tra ghi căn cứ chứng từ và điều kiện sử dụng trước khi xác nhận.',
        'Kiểm tra hình thức key không xác nhận được key có thật hoặc được nhà cung cấp chấp nhận.']),
    'Redeem Office': ('Ghi nhận kết quả quy đổi key', [
        'Chọn key đã kiểm tra; người có quyền có thể hiện key cho tác vụ hiện tại.',
        'Thực hiện redeem trên trang Microsoft bằng đúng tài khoản đơn vị.',
        'Chỉ xác nhận tại app sau khi đã thấy đúng sản phẩm trong tài khoản.',
        'Trong chế độ minh họa: chỉ ghi kết quả giả trong app, không dùng key giả trên Microsoft.']),
    'Thiết bị': ('Nhận diện máy để theo dõi', [
        'Tạo mã tem máy nội bộ ổn định; chọn đúng đơn vị và xã/phường/điểm nhận PC.',
        'Đọc serial máy và mainboard bằng công cụ cục bộ; đối chiếu tem nếu trả mã rỗng/mặc định.',
        'Serial phục vụ theo dõi thiết bị. Tài khoản/license và quy trình nhà cung cấp quyết định kích hoạt.']),
    'Phân bổ': ('Admin giao bản quyền cho máy và KTV', [
        'Chọn bản quyền đủ điều kiện, máy nhận và KTV được giao.',
        'Với Office đã redeem, tài khoản Microsoft và máy phải cùng đơn vị.',
        'Bản đầu quản lý một bản quyền cho một máy; quy tắc nhiều suất thiết bị chờ anh Vỹ chốt.']),
    'Kích hoạt': ('Theo dõi kết quả công việc', [
        'Admin xem các việc đã giao; người quản lý redeem xem tiến độ.',
        'KTV được giao xác minh trạng thái tại máy và gửi báo cáo.',
        'Thất bại phải có mã lỗi và mô tả; có thể gửi lại kết quả sau khi xử lý.']),
    'Việc của tôi': ('KTV thực hiện việc được giao', [
        'Mỗi việc là một license được giao cho một PC. Làm trọn PC hiện tại rồi mới chuyển PC tiếp theo.',
        'Mở app trên chính PC đang làm, chạy công cụ đọc serial và bấm nút để gắn serial mainboard vào việc được giao.',
        'Cài đúng phiên bản và thực hiện một lượt kích hoạt theo license của PC đó.',
        'Người quản lý tài khoản tham gia đăng nhập; không gửi mật khẩu vào app.',
        'Kiểm tra trạng thái trên phần mềm rồi gửi kết quả. Khi xong lô của đơn vị, ghi serial lên vỏ hộp và chuyển các PC đã thành công sang chờ in.']),
    'Tem của tôi': ('Gửi lô tem và đối chiếu khi nhận', [
        'Chỉ chọn PC đã kích hoạt thành công; app ghép mỗi PC với đúng serial mainboard và số thứ tự của đơn vị.',
        'Ghi serial mainboard lên hộp, chọn các PC cùng đơn vị rồi chuyển lô sang chờ in.',
        'Khi nhận lô tem đã in, so serial trên hộp với cả cặp tem của PC trước khi dán và đóng hộp.']),
    'Hàng đợi in': ('Trạm in xử lý theo lô', [
        'Chọn đúng lô theo đơn vị và KTV. Mỗi PC in hai tem liền nhau theo thứ tự số máy.',
        'Chỉ xác nhận in xong sau khi máy in đã in hết lô; lô đã in sẽ chuyển cho KTV nhận và đối chiếu.']),
    'Bảo hành': ('Ghi thay mainboard và xét kích hoạt lại', [
        'Admin chọn máy, nhập serial mainboard mới và căn cứ bảo hành.',
        'App giữ serial trước/sau trong nhật ký và chuyển công việc đã thành công sang chờ xét.',
        'Admin ghi căn cứ license/nhà cung cấp cho phép xử lý rồi giao KTV kích hoạt lại.',
        'App ghi chép sự kiện; quyết định quyền chuyển máy phải theo license thực tế.']),
    'Nhật ký': ('Tra cứu lịch sử', [
        'Theo dõi ai nhập, kiểm tra, xem key, redeem, giao việc và xử lý bảo hành.',
        'Thời gian được lưu theo UTC (giờ quốc tế). Quy tắc hiển thị chính thức chờ chốt.',
        'Nhật ký giữ cả lần kích hoạt lỗi, kể cả khi công việc sau đó đã thành công.']),
    'Người dùng': ('Admin cấp quyền tham gia app', [
        'Nhập email Google đã xác minh và chọn vai trò phù hợp.',
        'Admin quản lý kho và phân công; người redeem quản lý kiểm tra/tài khoản/redeem; KTV gửi lô tem; trạm in chỉ xem và in hàng đợi.',
        'Bản đầu mới hỗ trợ thêm tài khoản; sửa/vô hiệu hóa quyền cần hoàn thiện trước sử dụng thật.']),
}

def display_record(record, statuses):
    """Translate a safe record without changing underlying storage/API field names."""
    mapped = {}
    for key, value in record.items():
        if key == 'project_name' and not value: value = record.get('project', '')
        elif key == 'state': value = statuses.get(value, value)
        elif key == 'role': value = ROLE_NAMES.get(value, value)
        elif key == 'active': value = 'Có' if value else 'Không'
        elif key == 'route': value = {'DIRECT':'Kích hoạt theo nhà cung cấp', 'ACCOUNT_REDEEM':'Redeem vào tài khoản Microsoft'}.get(value,value)
        elif key == 'action': value = ACTION_NAMES.get(value,value)
        elif key == 'channel': value = {'Retail':'Bán lẻ', 'OEM':'Đi kèm máy', 'Volume':'Cấp phép số lượng lớn', 'Vendor':'Theo nhà cung cấp'}.get(value,value)
        mapped[FIELD_NAMES.get(key,key)] = value
    return mapped
