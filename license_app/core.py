"""License ledger: authorization, encrypted keys and transactional state changes."""
import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from sqlalchemy import (create_engine, MetaData, Table, Column, String, Text, Integer,
                        ForeignKey, UniqueConstraint, select, update, insert, event)
from sqlalchemy.exc import IntegrityError

meta = MetaData()
units = Table('units', meta, Column('id', String, primary_key=True),
              Column('project', String, nullable=False), Column('name', String, nullable=False),
              UniqueConstraint('project', 'name'))
users = Table('users', meta, Column('email', String, primary_key=True),
              Column('role', String, nullable=False), Column('active', Integer, nullable=False, default=1))
accounts = Table('accounts', meta, Column('id', String, primary_key=True),
                 Column('unit_id', String, ForeignKey('units.id'), nullable=False),
                 Column('email', String, nullable=False, unique=True), Column('owner', String, nullable=False))
licenses = Table('licenses', meta, Column('id', String, primary_key=True),
    Column('batch', String, nullable=False), Column('product', String, nullable=False),
    Column('sku', String, nullable=False), Column('channel', String, nullable=False),
    Column('route', String, nullable=False), Column('cipher', Text, nullable=False),
    Column('fingerprint', String, nullable=False, unique=True), Column('tail', String, nullable=False),
    Column('state', String, nullable=False), Column('account_id', String, ForeignKey('accounts.id')),
    Column('reference', String), Column('expires', String))
devices = Table('devices', meta, Column('id', String, primary_key=True),
    Column('unit_id', String, ForeignKey('units.id'), nullable=False),
    Column('asset_tag', String, nullable=False, unique=True), Column('serial', String, nullable=False),
    Column('board_serial', String, nullable=False), Column('model', String, nullable=False))
jobs = Table('jobs', meta, Column('id', String, primary_key=True),
    Column('license_id', String, ForeignKey('licenses.id'), nullable=False),
    Column('device_id', String, ForeignKey('devices.id'), nullable=False),
    Column('ktv', String, ForeignKey('users.email'), nullable=False), Column('state', String, nullable=False),
    Column('error_code', String), Column('note', Text), Column('evidence', String))
audit = Table('audit', meta, Column('id', String, primary_key=True),
    Column('at', String, nullable=False), Column('actor', String, nullable=False),
    Column('action', String, nullable=False), Column('entity', String, nullable=False),
    Column('details', Text, nullable=False))
operations = Table('operations', meta, Column('id', String, primary_key=True),
                   Column('actor', String, nullable=False), Column('result', String, nullable=False))
ROLES = {'ADMIN', 'OPERATOR', 'KTV'}
PRODUCTS = {'Office', 'Windows', 'Antivirus'}

class DomainError(Exception):
    pass

class Ledger:
    def __init__(self, url, encryption_key, fingerprint_key):
        self.engine = create_engine(url, pool_pre_ping=True)
        if self.engine.dialect.name == 'sqlite':
            @event.listens_for(self.engine, 'connect')
            def configure(dbapi, _):
                dbapi.execute('PRAGMA foreign_keys=ON')
                dbapi.execute('PRAGMA busy_timeout=15000')
        self.fernet = Fernet(encryption_key.encode())
        if len(fingerprint_key) < 32:
            raise ValueError('FINGERPRINT_KEY cần ít nhất 32 ký tự')
        self.fingerprint_key = fingerprint_key.encode()
        meta.create_all(self.engine)

    def bootstrap(self, email):
        """Only seeds the first administrator; subsequent changes need admin authorization."""
        with self.engine.begin() as c:
            if not c.execute(select(users.c.email).limit(1)).first():
                c.execute(insert(users).values(email=email.lower().strip(), role='ADMIN', active=1))

    def _auth(self, c, actor, allowed):
        user = c.execute(select(users).where(users.c.email == actor.lower())).mappings().first()
        if not user or not user['active'] or user['role'] not in allowed:
            raise DomainError('Bạn không có quyền thực hiện thao tác này.')
        return user['role']

    def role(self, actor):
        with self.engine.connect() as c:
            return self._auth(c, actor, ROLES)

    def _log(self, c, actor, action, entity, details=None):
        c.execute(insert(audit).values(id=str(uuid.uuid4()), at=datetime.now(timezone.utc).isoformat(),
            actor=actor, action=action, entity=entity, details=json.dumps(details or {}, ensure_ascii=False)))

    def _atomic(self, actor, allowed, op, fn):
        try:
            with self.engine.begin() as c:
                self._auth(c, actor, allowed)
                prior = c.execute(select(operations).where(operations.c.id == op)).mappings().first()
                if prior:
                    if prior['actor'] != actor:
                        raise DomainError('Mã thao tác không hợp lệ.')
                    return prior['result']
                result = fn(c)
                c.execute(insert(operations).values(id=op, actor=actor, result=result))
                return result
        except IntegrityError:
            raise DomainError('Bản ghi bị trùng hoặc dữ liệu đã thay đổi. Hãy tải lại danh sách.') from None

    def _get(self, c, table, entity):
        row = c.execute(select(table).where(table.c.id == entity)).mappings().first()
        if not row:
            raise DomainError('Không tìm thấy hồ sơ.')
        return row

    def _transition(self, c, entity, previous, target, **values):
        changed = c.execute(update(licenses).where(licenses.c.id == entity,
            licenses.c.state == previous).values(state=target, **values))
        if changed.rowcount != 1:
            raise DomainError('Trạng thái đã thay đổi; không thể xử lý lặp hoặc cấp trùng.')

    def add_user(self, actor, email, role, op):
        email = email.lower().strip()
        if role not in ROLES or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise DomainError('Email hoặc vai trò không hợp lệ.')
        def fn(c):
            if c.execute(select(users.c.email).where(users.c.email == email)).first():
                raise DomainError('Người dùng đã tồn tại. Bản đầu chỉ hỗ trợ thêm người dùng.')
            c.execute(insert(users).values(email=email, role=role, active=1))
            self._log(c, actor, 'ADD_USER', email, {'role': role})
            return email
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def add_unit(self, actor, project, name, op):
        if not project.strip() or not name.strip(): raise DomainError('Nhập đủ dự án và đơn vị.')
        def fn(c):
            entity = str(uuid.uuid4())
            c.execute(insert(units).values(id=entity, project=project.strip(), name=name.strip()))
            self._log(c, actor, 'ADD_UNIT', entity)
            return entity
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def add_account(self, actor, unit_id, email, owner, op):
        email = email.lower().strip()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or not owner.strip():
            raise DomainError('Nhập email và người quản lý tài khoản hợp lệ.')
        def fn(c):
            self._get(c, units, unit_id)
            entity = str(uuid.uuid4())
            c.execute(insert(accounts).values(id=entity, unit_id=unit_id, email=email, owner=owner.strip()))
            self._log(c, actor, 'ADD_ACCOUNT', entity)
            return entity
        return self._atomic(actor, {'ADMIN', 'OPERATOR'}, op, fn)

    def import_keys(self, actor, batch, product, sku, channel, route, keys, expires, op):
        if not batch.strip() or not sku.strip() or product not in PRODUCTS:
            raise DomainError('Nhập lô, phần mềm và phiên bản/SKU.')
        if route not in {'ACCOUNT_REDEEM', 'DIRECT'} or (route == 'ACCOUNT_REDEEM' and product != 'Office'):
            raise DomainError('Luồng redeem tài khoản chỉ dành cho Office phù hợp.')
        if channel not in {'Retail', 'OEM', 'Volume', 'Vendor'}:
            raise DomainError('Chưa xác định kênh cấp phép.')
        if route == 'ACCOUNT_REDEEM' and channel != 'Retail':
            raise DomainError('Chỉ đưa Office Retail đã xác minh vào luồng redeem tài khoản.')
        normalized = [re.sub(r'\s+', '', k).upper() for k in keys if k.strip()]
        if not normalized: raise DomainError('Chưa nhập key.')
        if product in {'Office', 'Windows'} and any(not re.fullmatch(r'(?:[A-Z0-9]{5}-){4}[A-Z0-9]{5}', k) for k in normalized):
            raise DomainError('Key Microsoft phải gồm 5 nhóm, mỗi nhóm 5 ký tự. Kiểm tra dữ liệu đầu vào.')
        if any(len(k) < 8 for k in normalized): raise DomainError('Key quá ngắn.')
        if expires:
            try: datetime.strptime(expires, '%Y-%m-%d')
            except ValueError: raise DomainError('Ngày hết hạn cần theo YYYY-MM-DD.') from None
        def fn(c):
            for key in normalized:
                entity = str(uuid.uuid4())
                digest = hmac.new(self.fingerprint_key, key.encode(), hashlib.sha256).hexdigest()
                c.execute(insert(licenses).values(id=entity, batch=batch.strip(), product=product,
                    sku=sku.strip(), channel=channel, route=route,
                    cipher=self.fernet.encrypt(key.encode()).decode(), fingerprint=digest,
                    tail=key[-5:], state='RECEIVED', expires=expires or None))
            self._log(c, actor, 'IMPORT_BATCH', batch, {'quantity': len(normalized), 'product': product})
            return str(len(normalized))
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def verify(self, actor, entity, reference, op):
        if not reference.strip(): raise DomainError('Cần ghi căn cứ kiểm tra/chứng từ và điều kiện sử dụng.')
        def fn(c):
            self._transition(c, entity, 'RECEIVED', 'VERIFIED', reference=reference.strip())
            self._log(c, actor, 'VERIFY', entity, {'reference': reference})
            return entity
        return self._atomic(actor, {'ADMIN', 'OPERATOR'}, op, fn)

    def reveal(self, actor, entity):
        with self.engine.begin() as c:
            self._auth(c, actor, {'ADMIN', 'OPERATOR'})
            row = self._get(c, licenses, entity)
            self._log(c, actor, 'REVEAL_KEY', entity)
            return self.fernet.decrypt(row['cipher'].encode()).decode()

    def redeem(self, actor, entity, account_id, reference, op):
        if not reference.strip(): raise DomainError('Ghi xác nhận Microsoft và sản phẩm đã redeem.')
        def fn(c):
            row = self._get(c, licenses, entity)
            if row['route'] != 'ACCOUNT_REDEEM': raise DomainError('License không thuộc luồng redeem tài khoản.')
            self._get(c, accounts, account_id)
            self._transition(c, entity, 'VERIFIED', 'REDEEMED', account_id=account_id, reference=reference.strip())
            self._log(c, actor, 'REDEEM_CONFIRMED', entity, {'account_id': account_id, 'reference': reference})
            return entity
        return self._atomic(actor, {'ADMIN', 'OPERATOR'}, op, fn)

    def add_device(self, actor, unit_id, tag, serial, board, model, op):
        if any(not x.strip() for x in [tag, serial, board, model]):
            raise DomainError('Cần mã máy, serial máy, serial mainboard và model.')
        if any(x.strip().upper() in {'DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE'} for x in [serial, board]):
            raise DomainError('Serial không hợp lệ; xác minh tem vật lý và nhập mã đã đối soát.')
        def fn(c):
            self._get(c, units, unit_id)
            entity = str(uuid.uuid4())
            c.execute(insert(devices).values(id=entity, unit_id=unit_id, asset_tag=tag.strip(),
                serial=serial.strip(), board_serial=board.strip(), model=model.strip()))
            self._log(c, actor, 'ADD_DEVICE', entity)
            return entity
        return self._atomic(actor, {'ADMIN', 'OPERATOR'}, op, fn)

    def assign(self, actor, entity, device_id, ktv, op):
        def fn(c):
            row = self._get(c, licenses, entity)
            device = self._get(c, devices, device_id)
            self._auth(c, ktv, {'KTV'})
            if row['account_id']:
                account = self._get(c, accounts, row['account_id'])
                if account['unit_id'] != device['unit_id']:
                    raise DomainError('Tài khoản và máy thuộc hai đơn vị khác nhau.')
            if row['expires'] and row['expires'] < datetime.now(timezone.utc).date().isoformat():
                raise DomainError('License đã hết hạn.')
            expected = 'REDEEMED' if row['route'] == 'ACCOUNT_REDEEM' else 'VERIFIED'
            self._transition(c, entity, expected, 'ASSIGNED')
            job_id = str(uuid.uuid4())
            c.execute(insert(jobs).values(id=job_id, license_id=entity, device_id=device_id, ktv=ktv, state='PENDING'))
            self._log(c, actor, 'ASSIGN', entity, {'job_id': job_id, 'device_id': device_id, 'ktv': ktv})
            return job_id
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def report(self, actor, job_id, success, error_code, note, evidence, op):
        if not note.strip() or (not success and not error_code.strip()):
            raise DomainError('Ghi thông tin xác minh; trường hợp thất bại cần mã lỗi.')
        if evidence and not evidence.startswith('https://'):
            raise DomainError('Minh chứng chỉ chấp nhận đường dẫn HTTPS.')
        def fn(c):
            role = self._auth(c, actor, {'ADMIN', 'KTV'})
            job = self._get(c, jobs, job_id)
            if role != 'ADMIN' and job['ktv'] != actor:
                raise DomainError('Bạn không được giao công việc này.')
            state = 'SUCCESS' if success else 'FAILED'
            changed = c.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.state.in_(['PENDING', 'FAILED']))
                .values(state=state, error_code=error_code.strip(), note=note.strip(), evidence=evidence))
            if changed.rowcount != 1: raise DomainError('Công việc đã hoàn tất hoặc đã thay đổi.')
            self._transition(c, job['license_id'], 'ASSIGNED', 'ACTIVATED' if success else 'ASSIGNED')
            self._log(c, actor, 'ACTIVATION_' + state, job_id, {'error_code': error_code, 'note': note, 'evidence': evidence})
            return job_id
        return self._atomic(actor, {'ADMIN', 'KTV'}, op, fn)

    def warranty(self, actor, device_id, new_board, reason, op):
        if not new_board.strip() or not reason.strip(): raise DomainError('Nhập serial mới và căn cứ bảo hành.')
        def fn(c):
            device = self._get(c, devices, device_id)
            if device['board_serial'] == new_board.strip(): raise DomainError('Serial mới trùng serial hiện tại.')
            # Compare-and-swap prevents two operators silently overwriting replacement history.
            changed = c.execute(update(devices).where(devices.c.id == device_id,
                devices.c.board_serial == device['board_serial']).values(board_serial=new_board.strip()))
            if changed.rowcount != 1: raise DomainError('Thiết bị vừa thay đổi; tải lại hồ sơ.')
            linked = c.execute(select(jobs).where(jobs.c.device_id == device_id, jobs.c.state == 'SUCCESS')).mappings().all()
            for job in linked:
                self._transition(c, job['license_id'], 'ACTIVATED', 'WARRANTY_REVIEW')
                c.execute(update(jobs).where(jobs.c.id == job['id']).values(state='WARRANTY_REVIEW'))
            self._log(c, actor, 'BOARD_REPLACED', device_id, {'old_board': device['board_serial'],
                'new_board': new_board.strip(), 'reason': reason})
            return device_id
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def approve_reactivation(self, actor, job_id, reference, op):
        if not reference.strip(): raise DomainError('Ghi căn cứ được phép kích hoạt lại theo loại license.')
        def fn(c):
            job = self._get(c, jobs, job_id)
            if job['state'] != 'WARRANTY_REVIEW': raise DomainError('Hồ sơ không ở bước kiểm tra bảo hành.')
            self._transition(c, job['license_id'], 'WARRANTY_REVIEW', 'ASSIGNED')
            changed = c.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.state == 'WARRANTY_REVIEW')
                .values(state='PENDING', error_code='', note='', evidence=''))
            if changed.rowcount != 1: raise DomainError('Hồ sơ vừa thay đổi.')
            self._log(c, actor, 'APPROVE_REACTIVATION', job_id, {'reference': reference})
            return job_id
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def rows(self, actor, name):
        tables = {'units': units, 'users': users, 'accounts': accounts, 'licenses': licenses,
                  'devices': devices, 'jobs': jobs, 'audit': audit}
        if name not in tables: raise DomainError('Danh sách không hợp lệ.')
        with self.engine.connect() as c:
            role = self._auth(c, actor, ROLES)
            if role == 'KTV':
                if name != 'jobs': raise DomainError('KTV chỉ được xem việc được giao.')
                stmt = select(jobs, devices.c.asset_tag, devices.c.serial, devices.c.board_serial,
                    devices.c.model, units.c.project, units.c.name.label('unit'), licenses.c.product,
                    licenses.c.sku, accounts.c.email.label('account')).select_from(
                    jobs.join(devices).join(units).join(licenses, jobs.c.license_id == licenses.c.id)
                    .outerjoin(accounts, licenses.c.account_id == accounts.c.id)).where(jobs.c.ktv == actor)
            else:
                if name == 'users' and role != 'ADMIN': raise DomainError('Chỉ Admin quản lý người dùng.')
                table = tables[name]
                # Explicit output allowlist: ciphertext and key fingerprints never leave this layer.
                stmt = select(*[col for col in table.c if col.name not in {'cipher', 'fingerprint'}])
            return [dict(row) for row in c.execute(stmt).mappings()]
