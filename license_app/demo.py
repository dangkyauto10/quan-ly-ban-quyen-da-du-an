"""Repeatable demo data; no Microsoft requests and no production writes."""
def seed_demo(ledger):
    admin, operator, ktv = 'admin@example.test', 'vy@example.test', 'ktv@example.test'
    ledger.bootstrap(admin)
    ledger.add_user(admin, operator, 'OPERATOR', 'seed-vy')
    ledger.add_user(admin, ktv, 'KTV', 'seed-ktv')
    ledger.add_user(admin, 'ktv2@example.test', 'KTV', 'seed-ktv2')
    unit = ledger.add_unit(admin, 'DU_AN_THU', 'Đơn vị minh họa', 'seed-unit')
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
        ledger.redeem(operator, lic, account, 'Xác nhận GIẢ — không có redeem thật', f'seed-redeem-{i}')
        device = ledger.add_device(admin, unit, f'PC-MAU-0{i}', f'SN-MAU-0{i}',
            f'MB-MAU-0{i}', 'Máy minh họa', f'seed-device-{i}')
        job = ledger.assign(admin, lic, device, ktv, f'seed-assign-{i}')
        ledger.report(ktv, job, i == 1, '' if i == 1 else 'LOI-MAU',
            'Báo cáo GIẢ — chưa kiểm tra phần mềm thực tế', '', f'seed-report-{i}')
