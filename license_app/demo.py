"""Repeatable demo data; no Microsoft requests and no production writes."""
def seed_demo(ledger):
    admin, operator, ktv = 'admin@example.test', 'vy@example.test', 'ktv@example.test'
    ledger.bootstrap(admin)
    ledger.add_user(admin, operator, 'OPERATOR', 'seed-vy')
    ledger.add_user(admin, ktv, 'KTV', 'seed-ktv')
    ledger.add_user(admin, 'ktv2@example.test', 'KTV', 'seed-ktv2')
    ledger.add_user(admin, 'qc@example.test', 'QC', 'seed-qc')
    for n in range(2,7):
        ledger.add_user(admin, f'qc{n}@example.test', 'QC', f'seed-qc-{n}')
    unit = ledger.add_unit(admin, 'DU_AN_THU', 'Đơn vị minh họa', 'seed-unit', project_name='Dự án minh họa')
    account = ledger.add_account(operator, unit, 'office@example.test', 'Người quản lý đơn vị mẫu', 'seed-account')
    for i, key in enumerate([
        'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE',
        'FFFFF-GGGGG-HHHHH-JJJJJ-KKKKK',
        'LLLLL-MMMMM-NNNNN-PPPPP-QQQQQ',
    ], 1):
        ledger.import_keys(admin, 'LO-MAU-01', 'Office', 'Home & Business 2024 (minh họa)',
                           'Retail', 'ACCOUNT_REDEEM', [key], '', f'seed-import-{i}')
    records = ledger.rows(admin, 'licenses')
    for i, tail in [(1,'EEEEE'), (2,'KKKKK')]:
        lic = next(r for r in records if r['tail'] == tail)['id']
        ledger.verify(operator, lic, 'Chứng từ GIẢ dùng thử quy trình', f'seed-verify-{i}')
        ledger.redeem(admin, lic, account, 'Xác nhận GIẢ — không có redeem thật', f'seed-redeem-{i}')
        device = ledger.add_device(admin, unit, f'PC-MAU-0{i}', f'SN-MAU-0{i}',
            f'MB-MAU-0{i}', 'Máy minh họa', f'seed-device-{i}')
        current=ledger.account_assignment_rows(admin)
        if not any(item['id']==account and item['ktv']==ktv for item in current):
            ledger.assign_account_to_ktv(admin,account,ktv,f'seed-account-handoff-{i}')
        job = ledger.assign(admin, lic, device, ktv, f'seed-assign-{i}')
        ledger.report(ktv, job, i == 1, '' if i == 1 else 'LOI-MAU',
            'Báo cáo GIẢ — chưa kiểm tra phần mềm thực tế', '', f'seed-report-{i}')


def seed_activation_demo(ledger):
    """Fresh, isolated activation exercise with synthetic devices and keys only."""
    admin, operator, ktv = 'admin@example.test', 'vy@example.test', 'ktv@example.test'
    ledger.bootstrap(admin)
    ledger.add_user(admin, operator, 'OPERATOR', 'activation-seed-vy')
    ledger.add_user(admin, ktv, 'KTV', 'activation-seed-ktv')
    ledger.add_user(admin, 'ktv2@example.test', 'KTV', 'activation-seed-ktv2')
    ledger.add_user(admin, 'qc@example.test', 'QC', 'activation-seed-qc')
    for n in range(2, 7):
        ledger.add_user(admin, f'qc{n}@example.test', 'QC', f'activation-seed-qc-{n}')

    unit = ledger.add_unit(admin, 'TEST-KICH-HOAT', 'Đơn vị mô phỏng — không có thật',
                           'activation-seed-unit', project_name='Môi trường test nghiệp vụ')
    account = ledger.add_account(operator, unit, 'office@example.test',
                                 'Tài khoản mẫu — không đăng nhập được', 'activation-seed-account')
    ledger.assign_account_to_ktv(admin, account, ktv, 'activation-seed-account-handoff')
    device = ledger.add_device(admin, unit, 'TEST-PC-01', 'SN-MAU-01', 'MB-SERIAL-MAU-01',
                               'PC mô phỏng — không phải thiết bị thật', 'activation-seed-device')
    ledger.set_plan(admin, unit, 1, 'activation-seed-plan')
    ledger.number_device(admin, device, 'activation-seed-number')

    products = [
        ('Office', 'Office Home & Business 2024 — MẪU', 'Retail', 'ACCOUNT_REDEEM',
         'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE'),
        ('Windows', 'Windows Pro — MẪU', 'OEM', 'DIRECT',
         'FFFFF-GGGGG-HHHHH-JJJJJ-KKKKK'),
        ('Antivirus', 'Antivirus — MẪU', 'Vendor', 'DIRECT',
         'LLLLL-MMMMM-NNNNN-PPPPP-QQQQQ'),
    ]
    for index, (product, sku, channel, route, fake_key) in enumerate(products, 1):
        ledger.import_keys(admin, f'LO-TEST-GIA-{index}', product, sku, channel,
                           route, [fake_key], '', f'activation-seed-import-{index}')
        license_row = next(r for r in ledger.rows(admin, 'licenses') if r['tail'] == fake_key[-5:])
        ledger.verify(operator, license_row['id'], 'Xác nhận GIẢ — chỉ thử luồng nghiệp vụ',
                      f'activation-seed-verify-{index}')
        if route == 'ACCOUNT_REDEEM':
            ledger.redeem(admin, license_row['id'], account,
                          'MÔ PHỎNG — không truy cập Microsoft', f'activation-seed-redeem-{index}')
        ledger.assign(admin, license_row['id'], device, ktv, f'activation-seed-assign-{index}')
