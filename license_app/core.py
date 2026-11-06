"""License ledger: authorization, encrypted keys and transactional state changes."""
import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from sqlalchemy import (create_engine, MetaData, Table, Column, String, Text, Integer,
                        ForeignKey, UniqueConstraint, select, update, insert, event, delete, inspect, func)
from sqlalchemy.exc import IntegrityError

meta = MetaData()
units = Table('units', meta, Column('id', String, primary_key=True),
              Column('project', String, nullable=False), Column('project_name', String, nullable=False, server_default=''),
              Column('name', String, nullable=False),
              UniqueConstraint('project', 'name'))
receiving_points = Table('receiving_points',meta,
    Column('id',String,primary_key=True),Column('unit_id',String,ForeignKey('units.id'),nullable=False),
    Column('code',String,nullable=False),Column('name',String,nullable=False),Column('pc_quantity',Integer,nullable=False),
    UniqueConstraint('unit_id','code'))
users = Table('users', meta, Column('email', String, primary_key=True),
              Column('role', String, nullable=False), Column('active', Integer, nullable=False, default=1))
accounts = Table('accounts', meta, Column('id', String, primary_key=True),
                 Column('unit_id', String, ForeignKey('units.id'), nullable=False),
                 Column('email', String, nullable=False, unique=True), Column('owner', String, nullable=False))
account_assignments = Table('account_assignments', meta, Column('id', String, primary_key=True),
    Column('account_id', String, ForeignKey('accounts.id'), nullable=False),
    Column('ktv', String, ForeignKey('users.email'), nullable=False),
    Column('assigned_by', String, nullable=False), Column('assigned_at', String, nullable=False),
    Column('released_at', String))
licenses = Table('licenses', meta, Column('id', String, primary_key=True),
    Column('batch', String, nullable=False), Column('product', String, nullable=False),
    Column('sku', String, nullable=False), Column('channel', String, nullable=False),
    Column('route', String, nullable=False), Column('cipher', Text, nullable=False),
    Column('fingerprint', String, nullable=False, unique=True), Column('tail', String, nullable=False),
    Column('state', String, nullable=False), Column('account_id', String, ForeignKey('accounts.id')),
    Column('reference', String), Column('expires', String))
devices = Table('devices', meta, Column('id', String, primary_key=True),
    Column('unit_id', String, ForeignKey('units.id'), nullable=False),
    Column('point_id', String, ForeignKey('receiving_points.id')),
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
ROLES = {'ADMIN', 'OPERATOR', 'KTV', 'QC', 'PRINT'}
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
        # create_all does not add columns to an existing ledger. Keep old Neon/SQLite
        # databases readable while introducing the separate project display name.
        if 'project_name' not in {column['name'] for column in inspect(self.engine).get_columns('units')}:
            with self.engine.begin() as c:
                c.exec_driver_sql("ALTER TABLE units ADD COLUMN project_name VARCHAR NOT NULL DEFAULT ''")
        if 'point_id' not in {column['name'] for column in inspect(self.engine).get_columns('devices')}:
            with self.engine.begin() as c:
                c.exec_driver_sql("ALTER TABLE devices ADD COLUMN point_id VARCHAR REFERENCES receiving_points(id)")

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
                if self.engine.dialect.name == 'sqlite':c.exec_driver_sql('BEGIN IMMEDIATE')
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

    def update_user(self,actor,email,role,active,op):
        email=email.lower().strip()
        if role not in ROLES or type(active) is not bool:raise DomainError('Vai trò hoặc trạng thái không hợp lệ.')
        def fn(c):
            # Serialize admin changes so two admins cannot remove the last active admin concurrently.
            c.execute(update(users).where(users.c.role=='ADMIN',users.c.active==1).values(active=users.c.active))
            self._auth(c,actor,{'ADMIN'})
            target=c.execute(select(users).where(users.c.email==email)).mappings().first()
            if not target:raise DomainError('Không tìm thấy thành viên.')
            remaining=c.execute(select(users.c.email).where(users.c.role=='ADMIN',users.c.active==1,users.c.email!=email)).all()
            if target['role']=='ADMIN' and target['active'] and (role!='ADMIN' or not active) and not remaining:
                raise DomainError('Phải giữ ít nhất một Admin đang hoạt động.')
            c.execute(update(users).where(users.c.email==email).values(role=role,active=int(active)))
            self._log(c,actor,'UPDATE_USER',email,{'old_role':target['role'],'role':role,'active':active})
            return email
        return self._atomic(actor,{'ADMIN'},op,fn)

    def add_unit(self, actor, project, name, op, project_name=None):
        project_name = (project_name or project).strip()
        if not project.strip() or not project_name or not name.strip(): raise DomainError('Nhập đủ mã dự án, tên dự án và đơn vị.')
        def fn(c):
            entity = str(uuid.uuid4())
            c.execute(insert(units).values(id=entity, project=project.strip(), project_name=project_name, name=name.strip()))
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

    def import_accounts(self, actor, records, op):
        cleaned=[]
        seen=set()
        for row in records or []:
            project=str(row.get('project') or '').strip()
            unit_name=str(row.get('unit_name') or '').strip()
            email=str(row.get('email') or '').strip().lower()
            owner=str(row.get('owner') or '').strip()
            if not project or not unit_name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
                raise DomainError('Mỗi dòng cần mã dự án, tên đơn vị được cấp và email Microsoft hợp lệ.')
            if email in seen:raise DomainError('Email Microsoft bị lặp trong danh sách nhập.')
            seen.add(email);cleaned.append((project,unit_name,email,owner or 'Chưa ghi người quản lý'))
        if not cleaned:raise DomainError('Tab tài khoản chưa có dòng hợp lệ để nạp.')
        def fn(c):
            added=0;unchanged=0
            for project,unit_name,email,owner in cleaned:
                unit=c.execute(select(units).where(units.c.project==project,units.c.name==unit_name)).mappings().first()
                if not unit:raise DomainError(f'Chưa có đơn vị {unit_name} thuộc dự án {project}; hãy nạp kế hoạch trước.')
                if unit['project_name'] and unit['project_name']!=str(row.get('project_name') or '').strip():
                    raise DomainError(f'Tên dự án của {unit_name} không khớp tab kế hoạch. Hãy cập nhật kế hoạch trước khi nạp tài khoản.')
                prior=c.execute(select(accounts).where(accounts.c.email==email)).mappings().first()
                if prior:
                    if prior['unit_id']!=unit['id'] or prior['owner']!=owner:
                        raise DomainError(f'Tài khoản {email} đã có trong app nhưng khác đơn vị/người quản lý. Không tự chuyển tài khoản.')
                    unchanged+=1;continue
                entity=str(uuid.uuid4())
                c.execute(insert(accounts).values(id=entity,unit_id=unit['id'],email=email,owner=owner))
                self._log(c,actor,'IMPORT_ACCOUNT',entity,{'email':email,'unit_id':unit['id'],'owner':owner})
                added+=1
            self._log(c,actor,'IMPORT_ACCOUNT_ROSTER',op,{'added':added,'unchanged':unchanged})
            return f'{added}:{unchanged}'
        result=self._atomic(actor,{'ADMIN'},op,fn)
        added,unchanged=(int(x) for x in result.split(':'))
        return {'added':added,'unchanged':unchanged}

    def assign_account_to_ktv(self,actor,account_id,ktv,op):
        ktv=ktv.lower().strip()
        def fn(c):
            account=self._get(c,accounts,account_id)
            c.execute(update(accounts).where(accounts.c.id==account_id).values(owner=accounts.c.owner))
            self._auth(c,ktv,{'KTV'})
            prior=c.execute(select(account_assignments).where(account_assignments.c.account_id==account_id,
                account_assignments.c.released_at.is_(None))).mappings().first()
            if prior:
                if prior['ktv']==ktv:return prior['id']
                raise DomainError('Tài khoản Microsoft đang được giao cho '+prior['ktv']+'.')
            entity=str(uuid.uuid4());stamp=datetime.now(timezone.utc).isoformat()
            c.execute(insert(account_assignments).values(id=entity,account_id=account_id,ktv=ktv,
                assigned_by=actor,assigned_at=stamp,released_at=None))
            self._log(c,actor,'ASSIGN_MS_ACCOUNT',account_id,{'ktv':ktv,'email':account['email']})
            return entity
        return self._atomic(actor,{'ADMIN'},op,fn)

    def release_account_from_ktv(self,actor,account_id,op):
        def fn(c):
            account=self._get(c,accounts,account_id)
            c.execute(update(accounts).where(accounts.c.id==account_id).values(owner=accounts.c.owner))
            active=c.execute(select(account_assignments).where(account_assignments.c.account_id==account_id,
                account_assignments.c.released_at.is_(None))).mappings().first()
            if not active:raise DomainError('Tài khoản chưa được giao cho KTV.')
            unfinished=c.execute(select(jobs.c.device_id).select_from(jobs.join(licenses,jobs.c.license_id==licenses.c.id)
                .join(devices,jobs.c.device_id==devices.c.id)).where(licenses.c.account_id==account_id,
                    jobs.c.ktv==active['ktv'],jobs.c.state!='SUCCESS')).first()
            if unfinished:raise DomainError('Còn PC của tài khoản này chưa hoàn tất kích hoạt.')
            inspection=meta.tables.get('preparation_inspections')
            if inspection is not None:
                linked_devices=c.execute(select(jobs.c.device_id,inspection.c.state).select_from(
                    jobs.join(licenses,jobs.c.license_id==licenses.c.id).join(devices,jobs.c.device_id==devices.c.id)
                    .outerjoin(inspection,inspection.c.id==jobs.c.device_id)).where(
                    licenses.c.account_id==account_id,jobs.c.ktv==active['ktv'])).all()
                if any(state!='PACKED' for _device_id,state in linked_devices):
                    raise DomainError('KTV cần hoàn tất đóng gói/QC các PC của tài khoản trước khi thu hồi.')
            stamp=datetime.now(timezone.utc).isoformat()
            c.execute(update(account_assignments).where(account_assignments.c.id==active['id']).values(released_at=stamp))
            self._log(c,actor,'RELEASE_MS_ACCOUNT',account_id,{'ktv':active['ktv'],'email':account['email']})
            return account_id
        return self._atomic(actor,{'ADMIN'},op,fn)

    def account_assignment_rows(self,actor):
        with self.engine.connect() as c:
            self._auth(c,actor,{'ADMIN','OPERATOR'})
            query=select(accounts.c.id,accounts.c.email,accounts.c.owner,units.c.project,units.c.project_name,
                units.c.name.label('unit'),account_assignments.c.ktv,account_assignments.c.assigned_at,
                account_assignments.c.released_at).select_from(accounts.join(units,accounts.c.unit_id==units.c.id)
                .outerjoin(account_assignments,(account_assignments.c.account_id==accounts.c.id)&account_assignments.c.released_at.is_(None)))
            return [dict(r) for r in c.execute(query.order_by(units.c.project,units.c.name,accounts.c.email)).mappings()]

    def device_dossier(self,actor,query_text):
        needle=(query_text or '').strip().casefold()
        if not needle:raise DomainError('Nhập mã dự án, đơn vị, mã máy hoặc serial để tra hồ sơ.')
        with self.engine.connect() as c:
            self._auth(c,actor,{'ADMIN','OPERATOR','QC'})
            stmt=select(devices,units.c.project,units.c.project_name,units.c.name.label('unit')).select_from(
                devices.join(units,devices.c.unit_id==units.c.id))
            records=[]
            event_table=meta.tables.get('audit')
            event_rows=c.execute(select(event_table.c.entity,event_table.c.details).where(
                event_table.c.action=='BOARD_REPLACED')).mappings().all() if event_table is not None else []
            historical={}
            for event_row in event_rows:
                try:details=json.loads(event_row['details'])
                except (TypeError,ValueError):continue
                historical.setdefault(event_row['entity'],[]).extend([details.get('old_board',''),details.get('new_board','')])
            account_emails={}
            account_rows=c.execute(select(jobs.c.device_id,accounts.c.email).select_from(jobs.join(licenses,jobs.c.license_id==licenses.c.id)
                .join(accounts,licenses.c.account_id==accounts.c.id))).all()
            for device_id,email in account_rows:account_emails.setdefault(device_id,[]).append(email)
            for row in c.execute(stmt).mappings():
                d=dict(row);hay=' '.join([str(d.get(k) or '') for k in ['project','project_name','unit','asset_tag','serial','board_serial']]+historical.get(d['id'],[])+account_emails.get(d['id'],[])).casefold()
                if needle in hay:records.append(d)
            return records

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
            self._auth(c, actor, {'ADMIN'})
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
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def add_device(self, actor, unit_id, tag, serial, board, model, op, point_id=None):
        if any(not x.strip() for x in [tag, serial, model]):
            raise DomainError('Cần mã máy, serial máy và model.')
        if any(x.strip().upper() in {'DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE'} for x in [serial] + ([board] if board.strip() else [])):
            raise DomainError('Serial không hợp lệ; xác minh tem vật lý và nhập mã đã đối soát.')
        def fn(c):
            self._get(c, units, unit_id)
            if point_id:
                point=self._get(c,receiving_points,point_id)
                if point['unit_id']!=unit_id:raise DomainError('Điểm nhận không thuộc đơn vị được chọn.')
                point_devices=c.execute(select(func.count()).select_from(devices).where(devices.c.point_id==point_id)).scalar_one()
                if point_devices>=point['pc_quantity']:raise DomainError('Điểm nhận đã đủ số PC được phân bổ.')
            entity = str(uuid.uuid4())
            c.execute(insert(devices).values(id=entity, unit_id=unit_id, point_id=point_id, asset_tag=tag.strip(),
                serial=serial.strip(), board_serial=board.strip(), model=model.strip()))
            self._log(c, actor, 'ADD_DEVICE', entity)
            return entity
        return self._atomic(actor, {'ADMIN', 'OPERATOR'}, op, fn)

    def assign(self, actor, entity, device_id, ktv, op):
        def fn(c):
            row = self._get(c, licenses, entity)
            device = self._get(c, devices, device_id)
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            self._auth(c, ktv, {'KTV'})
            if row['account_id']:
                account = self._get(c, accounts, row['account_id'])
                if account['unit_id'] != device['unit_id']:
                    raise DomainError('Tài khoản và máy thuộc hai đơn vị khác nhau.')
                handoff=c.execute(select(account_assignments).where(account_assignments.c.account_id==account['id'],
                    account_assignments.c.released_at.is_(None))).mappings().first()
                if not handoff or handoff['ktv']!=ktv:
                    raise DomainError('Tài khoản Microsoft chưa được Admin phân bổ cho KTV này.')
            other_ktvs=c.execute(select(jobs.c.ktv).where(jobs.c.device_id==device_id)).scalars().all()
            if other_ktvs and any(owner!=ktv for owner in other_ktvs):
                raise DomainError('Một PC phải được cùng một KTV phụ trách đến khi hoàn thiện.')
            allocation_table=meta.tables.get('point_license_plans')
            if device['point_id'] and allocation_table is not None:
                allocation=c.execute(select(allocation_table.c.quantity).where(
                    allocation_table.c.point_id==device['point_id'],
                    allocation_table.c.product==row['product'],allocation_table.c.sku==row['sku'])).scalar_one_or_none()
                if allocation is None:raise DomainError('Chưa phân bổ SKU này cho xã/điểm nhận PC.')
                used=c.execute(select(func.count()).select_from(jobs.join(devices,jobs.c.device_id==devices.c.id)
                    .join(licenses,jobs.c.license_id==licenses.c.id)).where(
                    devices.c.point_id==device['point_id'],licenses.c.product==row['product'],licenses.c.sku==row['sku'])).scalar_one()
                if used>=allocation:raise DomainError('Đã dùng hết số lượng SKU được phân bổ cho xã/điểm này.')
            if row['expires'] and row['expires'] < datetime.now(timezone.utc).date().isoformat():
                raise DomainError('License đã hết hạn.')
            expected = 'REDEEMED' if row['route'] == 'ACCOUNT_REDEEM' else 'VERIFIED'
            self._transition(c, entity, expected, 'ASSIGNED')
            job_id = str(uuid.uuid4())
            c.execute(insert(jobs).values(id=job_id, license_id=entity, device_id=device_id, ktv=ktv, state='PENDING'))
            self._log(c, actor, 'ASSIGN', entity, {'job_id': job_id, 'device_id': device_id, 'ktv': ktv})
            return job_id
        return self._atomic(actor, {'ADMIN'}, op, fn)

    def bind_board_serial(self, actor, job_id, board_serial, op):
        """Bind the serial read on the workstation to its assigned one-PC job."""
        value = (board_serial or '').strip().upper()
        if not value or len(value) > 120 or value.upper() in {
            'DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE', 'N/A'
        }:
            raise DomainError('Mainboard không trả serial hợp lệ. Kiểm tra serial trên BIOS/tem vật lý.')
        def fn(c):
            self._auth(c, actor, {'KTV'})
            job = self._get(c, jobs, job_id)
            if job['ktv'] != actor:
                raise DomainError('Bạn không được giao công việc này.')
            if job['state'] not in {'PENDING', 'FAILED'}:
                raise DomainError('Việc này đã hoàn tất, không thể đổi serial mainboard.')
            device = self._get(c, devices, job['device_id'])
            duplicate = c.execute(select(devices.c.id, devices.c.asset_tag).where(
                func.upper(devices.c.board_serial) == value, devices.c.id != device['id'])).first()
            if duplicate:
                raise DomainError('Serial mainboard đã gắn với máy ' + duplicate.asset_tag + '.')
            if device['board_serial'] != value:
                c.execute(update(devices).where(devices.c.id == device['id']).values(board_serial=value))
                self._log(c, actor, 'BIND_BOARD_SERIAL', job_id,
                    {'device_id': device['id'], 'board_serial': value})
            return value
        return self._atomic(actor, {'KTV'}, op, fn)

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
            if success:
                device = self._get(c, devices, job['device_id'])
                board = (device['board_serial'] or '').strip()
                if not board or board.upper() in {'DEFAULT STRING', 'TO BE FILLED BY O.E.M.', 'UNKNOWN', 'NONE', 'N/A'}:
                    raise DomainError('Cần đọc và ghi nhận serial mainboard của PC này trước khi báo kích hoạt thành công.')
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
            if 'packing_claims' in meta.tables:
                tab=meta.tables['packing_claims']
                c.execute(delete(tab).where(tab.c.id==device_id))
            if 'preparation_inspections' in meta.tables:
                tab=meta.tables['preparation_inspections']
                c.execute(update(tab).where(tab.c.id==device_id).values(
                    state='FAILED',note='Bảo hành/thay mainboard; cần QC lại.',inspector=actor))
            if 'ktv_pc_completions' in meta.tables:
                completion=meta.tables['ktv_pc_completions']
                c.execute(update(completion).where(completion.c.device_id==device_id).values(state='REWORK_REQUIRED'))
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
        tables = {'units': units, 'receiving_points': receiving_points, 'users': users, 'accounts': accounts, 'licenses': licenses,
                  'devices': devices, 'jobs': jobs, 'audit': audit}
        if name not in tables: raise DomainError('Danh sách không hợp lệ.')
        with self.engine.connect() as c:
            role = self._auth(c, actor, ROLES)
            if role=='PRINT':raise DomainError('Tài khoản trạm in chỉ được truy cập hàng đợi tem.')
            if role == 'QC' and name not in {'jobs','devices','units'}:
                raise DomainError('Bộ phận kiểm tra chỉ xem hồ sơ máy và công việc.')
            if role == 'KTV':
                if name != 'jobs': raise DomainError('KTV chỉ được xem việc được giao.')
                stmt = select(jobs, devices.c.asset_tag, devices.c.serial, devices.c.board_serial,
                    devices.c.model, units.c.project, units.c.name.label('unit'),
                    receiving_points.c.name.label('point'),receiving_points.c.code.label('point_code'),licenses.c.product,
                    licenses.c.sku, licenses.c.tail, accounts.c.email.label('account')).select_from(
                    jobs.join(devices).join(units).join(licenses, jobs.c.license_id == licenses.c.id)
                    .outerjoin(receiving_points,devices.c.point_id==receiving_points.c.id)
                    .outerjoin(accounts, licenses.c.account_id == accounts.c.id)).where(jobs.c.ktv == actor)
            else:
                if name == 'users' and role != 'ADMIN': raise DomainError('Chỉ Admin quản lý người dùng.')
                table = tables[name]
                # Explicit output allowlist: ciphertext and key fingerprints never leave this layer.
                stmt = select(*[col for col in table.c if col.name not in {'cipher', 'fingerprint'}])
            return [dict(row) for row in c.execute(stmt).mappings()]

