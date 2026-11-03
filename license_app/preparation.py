"""Company preparation: plans, stable numbering and independent inspection."""
from sqlalchemy import Table, Column, String, Integer, ForeignKey, UniqueConstraint, select, insert, update
from .core import Ledger, DomainError, meta, units, devices, jobs, users

plans = Table('preparation_plans', meta,
    Column('id', String, ForeignKey('units.id'), primary_key=True),
    Column('quantity', Integer, nullable=False))
slots = Table('preparation_slots', meta,
    Column('id', String, ForeignKey('devices.id'), primary_key=True),
    Column('unit_id', String, ForeignKey('units.id'), nullable=False),
    Column('number', Integer, nullable=False),
    UniqueConstraint('unit_id', 'number'))
inspections = Table('preparation_inspections', meta,
    Column('id', String, ForeignKey('devices.id'), primary_key=True),
    Column('state', String, nullable=False), Column('note', String, nullable=False),
    Column('inspector', String, nullable=False))

class PreparationLedger(Ledger):
    def set_plan(self, actor, unit_id, quantity, op):
        if type(quantity) is not int or quantity < 1:raise DomainError('Số lượng PC phải là số nguyên dương.')
        def fn(c):
            self._get(c, units, unit_id)
            # Serialize edits to a point before checking its allocated slots.
            c.execute(update(units).where(units.c.id==unit_id).values(name=units.c.name))
            numbers=c.execute(select(slots.c.number).where(slots.c.unit_id==unit_id)).scalars().all()
            if numbers and quantity < max(numbers):raise DomainError('Số lượng mới nhỏ hơn số thứ tự máy đã cấp.')
            if c.execute(select(plans.c.id).where(plans.c.id==unit_id)).first():
                c.execute(update(plans).where(plans.c.id==unit_id).values(quantity=quantity))
            else:c.execute(insert(plans).values(id=unit_id, quantity=quantity))
            self._log(c,actor,'SET_PC_PLAN',unit_id,{'quantity':quantity})
            return unit_id
        return self._atomic(actor,{'ADMIN'},op,fn)

    def number_device(self, actor, device_id, op):
        def fn(c):
            d=self._get(c,devices,device_id)
            c.execute(update(units).where(units.c.id==d['unit_id']).values(name=units.c.name))
            existing=c.execute(select(slots).where(slots.c.id==device_id)).mappings().first()
            if existing:return device_id
            plan=self._get(c,plans,d['unit_id'])
            used=set(c.execute(select(slots.c.number).where(slots.c.unit_id==d['unit_id'])).scalars())
            number=next((n for n in range(1,plan['quantity']+1) if n not in used),None)
            if number is None:raise DomainError('Điểm đã đủ số máy theo kế hoạch. Admin cần tăng số lượng trước.')
            c.execute(insert(slots).values(id=device_id,unit_id=d['unit_id'],number=number))
            self._log(c,actor,'NUMBER_PC',device_id,{'number':number})
            return device_id
        return self._atomic(actor,{'ADMIN'},op,fn)

    def preparation_rows(self, actor):
        with self.engine.connect() as c:
            role=self._auth(c,actor,{'ADMIN','OPERATOR','KTV','QC'})
            query=select(devices,units.c.name.label('unit'),units.c.project,
                slots.c.number,plans.c.quantity,inspections.c.state.label('inspection_state')).select_from(
                devices.join(units).outerjoin(slots,slots.c.id==devices.c.id)
                .outerjoin(plans,plans.c.id==units.c.id).outerjoin(inspections,inspections.c.id==devices.c.id))
            if role=='KTV':query=query.where(devices.c.id.in_(select(jobs.c.device_id).where(jobs.c.ktv==actor)))
            result=[dict(r) for r in c.execute(query).mappings()]
            for r in result:
                states=c.execute(select(jobs.c.state).where(jobs.c.device_id==r['id'])).scalars().all()
                r['activation_ready']=bool(states) and all(state=='SUCCESS' for state in states)
            return result

    def inspect_device(self,actor,device_id,passed,note,serial,op):
        if not note.strip():raise DomainError('Nhập nội dung kiểm tra.')
        def fn(c):
            self._auth(c,actor,{'QC'})
            d=self._get(c,devices,device_id)
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            if serial.strip()!=d['serial']:raise DomainError('Serial kiểm tra không khớp serial hồ sơ máy.')
            linked=c.execute(select(jobs).where(jobs.c.device_id==device_id)).mappings().all()
            if not linked or any(j['state']!='SUCCESS' for j in linked):raise DomainError('Máy chưa hoàn tất kích hoạt tất cả bản quyền được giao.')
            if any(j['ktv']==actor for j in linked):raise DomainError('Người kiểm tra phải độc lập với người kích hoạt.')
            self._get(c,slots,device_id)
            old=c.execute(select(inspections).where(inspections.c.id==device_id)).mappings().first()
            if old and old['state']=='PACKED':raise DomainError('Máy đã hoàn tất đóng gói.')
            values={'state':'PASSED' if passed else 'FAILED','note':note.strip(),'inspector':actor}
            if old:c.execute(update(inspections).where(inspections.c.id==device_id).values(**values))
            else:c.execute(insert(inspections).values(id=device_id,**values))
            if not passed:
                for job in linked:
                    self._transition(c,job['license_id'],'ACTIVATED','ASSIGNED')
                    c.execute(update(jobs).where(jobs.c.id==job['id']).values(state='PENDING'))
            self._log(c,actor,'INSPECT_PC',device_id,values)
            return device_id
        return self._atomic(actor,{'QC'},op,fn)

    def close_package(self,actor,device_id,op):
        def fn(c):
            self._auth(c,actor,{'QC'})
            d=self._get(c,devices,device_id)
            c.execute(update(devices).where(devices.c.id==device_id).values(model=devices.c.model))
            linked=c.execute(select(jobs.c.state).where(jobs.c.device_id==device_id)).scalars().all()
            if not linked or any(s!='SUCCESS' for s in linked):raise DomainError('Máy cần kiểm tra lại tình trạng kích hoạt.')
            changed=c.execute(update(inspections).where(inspections.c.id==device_id,
                inspections.c.state=='PASSED',inspections.c.inspector==actor).values(state='PACKED'))
            if changed.rowcount!=1:raise DomainError('Người kiểm tra cần xác nhận máy đạt trước khi đóng gói.')
            self._log(c,actor,'PACK_PC',device_id)
            return device_id
        return self._atomic(actor,{'QC'},op,fn)
