"""Concurrent mobile packing: leases and atomic pair-validation/reporting."""
import time
from sqlalchemy import Table,Column,String,Integer,ForeignKey,select,insert,update,delete
from .core import DomainError,meta,devices,jobs,units
from .preparation import PreparationLedger,plans,slots,inspections
from .labels import compare_labels

claims = meta.tables.get('packing_claims')
if claims is None:
    claims = Table('packing_claims',meta,
        Column('id',String,ForeignKey('devices.id'),primary_key=True),
        Column('owner',String,nullable=False),Column('until',Integer,nullable=False))

class PackingLedger(PreparationLedger):
    def claim_for_check(self,actor,device_id,op):
        def fn(c):
            self._get(c,devices,device_id)
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            linked=c.execute(select(jobs).where(jobs.c.device_id==device_id)).mappings().all()
            if not linked or any(j['state']!='SUCCESS' for j in linked):
                raise DomainError('Máy chưa hoàn tất kích hoạt hoặc đang chờ KTV xử lý.')
            if any(j['ktv']==actor for j in linked):raise DomainError('Người kiểm tra phải khác người kích hoạt.')
            record=c.execute(select(inspections).where(inspections.c.id==device_id)).mappings().first()
            if record and record['state']=='PACKED':raise DomainError('Máy đã đóng gói hoàn tất; không nhận lại.')
            now=int(time.time())
            prior=c.execute(select(claims).where(claims.c.id==device_id)).mappings().first()
            if prior and prior['owner']!=actor and prior['until']>now:
                raise DomainError('Máy đang được '+prior['owner']+' kiểm tra. Chọn máy khác.')
            values={'owner':actor,'until':now+15*60}
            if prior:c.execute(update(claims).where(claims.c.id==device_id).values(**values))
            else:c.execute(insert(claims).values(id=device_id,**values))
            self._log(c,actor,'CLAIM_CHECK',device_id,{'seconds':900})
            return device_id
        return self._atomic(actor,{'QC'},op,fn)

    def release_check(self,actor,device_id,op):
        def fn(c):
            role=self._auth(c,actor,{'QC','ADMIN'})
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            prior=c.execute(select(claims).where(claims.c.id==device_id)).mappings().first()
            if prior and role!='ADMIN' and prior['owner']!=actor:raise DomainError('Chỉ được trả máy do mình nhận kiểm tra.')
            c.execute(delete(claims).where(claims.c.id==device_id))
            self._log(c,actor,'RELEASE_CHECK',device_id)
            return device_id
        return self._atomic(actor,{'QC','ADMIN'},op,fn)

    def check_claims(self,actor):
        with self.engine.connect() as c:
            self._auth(c,actor,{'QC','ADMIN'})
            return {r['id']:dict(r) for r in c.execute(select(claims)).mappings()}

    def submit_packing(self,actor,first,second,key,passed,note,serial,op):
        if not note.strip():raise DomainError('Nhập nội dung kiểm tra; nếu không đạt cần nêu lỗi.')
        if type(passed) is not bool:raise DomainError('Kết quả kiểm tra không hợp lệ.')
        matched=compare_labels(first,second,key)
        device_id=matched['id']
        def fn(c):
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            d=self._get(c,devices,device_id)
            unit=self._get(c,units,d['unit_id'])
            # Serialize plan changes with the comparison of printed numbering.
            c.execute(update(units).where(units.c.id==unit['id']).values(name=units.c.name))
            slot=self._get(c,slots,device_id);plan=self._get(c,plans,unit['id'])
            actual={'id':device_id,'asset_tag':d['asset_tag'],'serial':d['board_serial'],
                'unit':unit['name'],'project':unit['project'],'number':slot['number'],'quantity':plan['quantity']}
            if any(actual[k]!=matched[k] for k in actual):raise DomainError('Tem đã cũ hoặc không thuộc hồ sơ hiện tại. In lại cả cặp.')
            if serial.strip().upper()!=d['board_serial'].strip().upper():raise DomainError('Serial mainboard thực không khớp hồ sơ máy/tem.')
            claim=c.execute(select(claims).where(claims.c.id==device_id)).mappings().first()
            if not claim or claim['owner']!=actor or claim['until']<=int(time.time()):
                raise DomainError('Chưa nhận máy hoặc đã hết 15 phút giữ máy. Nhận/gia hạn rồi gửi lại.')
            linked=c.execute(select(jobs).where(jobs.c.device_id==device_id)).mappings().all()
            if not linked or any(j['state']!='SUCCESS' for j in linked):raise DomainError('Máy chưa hoàn tất kích hoạt; cần KTV xử lý.')
            if any(j['ktv']==actor for j in linked):raise DomainError('Người kiểm tra phải khác người kích hoạt.')
            prior=c.execute(select(inspections).where(inspections.c.id==device_id)).mappings().first()
            if prior and prior['state']=='PACKED':raise DomainError('Máy đã hoàn tất đóng gói. Không ghi trùng.')
            values={'state':'PACKED' if passed else 'FAILED','note':note.strip(),'inspector':actor}
            if prior:c.execute(update(inspections).where(inspections.c.id==device_id).values(**values))
            else:c.execute(insert(inspections).values(id=device_id,**values))
            if not passed:
                for job in linked:
                    self._transition(c,job['license_id'],'ACTIVATED','ASSIGNED')
                    c.execute(update(jobs).where(jobs.c.id==job['id']).values(state='PENDING'))
            c.execute(delete(claims).where(claims.c.id==device_id))
            self._log(c,actor,'PACK_PC' if passed else 'INSPECT_PC_FAILED',device_id,
                {**values,'paired_labels':True,'serial_checked':serial.strip()})
            return device_id
        return self._atomic(actor,{'QC'},op,fn)
