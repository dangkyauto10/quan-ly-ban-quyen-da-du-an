"""Company preparation: plans, stable numbering and independent inspection."""
from sqlalchemy import Table, Column, String, Integer, ForeignKey, UniqueConstraint, select, insert, update
from datetime import datetime, timezone
import uuid
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
label_batches = Table('label_batches', meta,
    Column('id', String, primary_key=True),
    Column('unit_id', String, ForeignKey('units.id'), nullable=False),
    Column('ktv', String, ForeignKey('users.email'), nullable=False),
    Column('state', String, nullable=False), Column('created_at', String, nullable=False),
    Column('printed_at', String), Column('printed_by', String), Column('collected_at', String))
label_batch_items = Table('label_batch_items', meta,
    Column('device_id', String, ForeignKey('devices.id'), primary_key=True),
    Column('batch_id', String, ForeignKey('label_batches.id'), nullable=False))

class PreparationLedger(Ledger):
    def queue_label_batch(self, actor, unit_id, device_ids, op):
        ids=list(dict.fromkeys(device_ids or []))
        if not ids:raise DomainError('Chọn ít nhất một PC đã kích hoạt để đưa vào lô tem.')
        def fn(c):
            self._auth(c,actor,{'KTV'})
            self._get(c,units,unit_id)
            for device_id in ids:
                d=self._get(c,devices,device_id)
                if d['unit_id']!=unit_id:raise DomainError('Một lô tem chỉ gồm PC của cùng đơn vị.')
                own=c.execute(select(jobs.c.id).where(jobs.c.device_id==device_id,jobs.c.ktv==actor)).first()
                if not own:raise DomainError('Có PC không được giao cho KTV đang đăng nhập.')
                linked=c.execute(select(jobs.c.state,jobs.c.ktv).where(jobs.c.device_id==device_id)).all()
                if not linked or any(state!='SUCCESS' or ktv!=actor for state,ktv in linked):
                    raise DomainError('Chỉ đưa vào lô các PC đã kích hoạt thành công tất cả license được giao.')
                board=(d['board_serial'] or '').strip()
                if not board or board.upper() in {'DEFAULT STRING','TO BE FILLED BY O.E.M.','UNKNOWN','NONE','N/A'}:
                    raise DomainError('Có PC chưa có serial mainboard hợp lệ.')
                self._get(c,slots,device_id);self._get(c,plans,unit_id)
                if c.execute(select(label_batch_items.c.device_id).where(label_batch_items.c.device_id==device_id)).first():
                    raise DomainError('Có PC đã nằm trong lô tem trước đó; không gửi trùng.')
            batch_id=str(uuid.uuid4())
            c.execute(insert(label_batches).values(id=batch_id,unit_id=unit_id,ktv=actor,
                state='WAITING',created_at=datetime.now(timezone.utc).isoformat()))
            c.execute(insert(label_batch_items),[{'device_id':device_id,'batch_id':batch_id} for device_id in ids])
            self._log(c,actor,'QUEUE_LABEL_BATCH',batch_id,{'unit_id':unit_id,'device_ids':ids,'quantity':len(ids)})
            return batch_id
        return self._atomic(actor,{'KTV'},op,fn)

    def label_batches_for_ktv(self,actor):
        with self.engine.connect() as c:
            self._auth(c,actor,{'KTV'})
            query=select(label_batches.c.id,label_batches.c.unit_id,label_batches.c.ktv,
                label_batches.c.state,label_batches.c.created_at,label_batches.c.printed_at,
                label_batches.c.collected_at,units.c.name.label('unit'),units.c.project_name,
                units.c.project,label_batch_items.c.device_id).select_from(label_batches.join(units)
                .join(label_batch_items,label_batch_items.c.batch_id==label_batches.c.id))
            rows=c.execute(query.where(label_batches.c.ktv==actor).order_by(label_batches.c.created_at.desc())).mappings().all()
            batches={}
            for row in rows:
                b=batches.setdefault(row['id'],{k:row[k] for k in row.keys() if k!='device_id'})
                b.setdefault('device_ids',[]).append(row['device_id'])
            return list(batches.values())

    def label_queue_rows(self,actor):
        with self.engine.connect() as c:
            self._auth(c,actor,{'ADMIN','PRINT'})
            query=select(label_batches.c.id.label('batch_id'),label_batches.c.ktv,
                label_batches.c.state.label('batch_state'),label_batches.c.created_at,
                units.c.name.label('unit'),units.c.project,units.c.project_name,
                devices.c.id,devices.c.asset_tag,devices.c.serial,devices.c.board_serial,
                label_batch_items.c.device_id,slots.c.number,plans.c.quantity).select_from(
                label_batches.join(units).join(label_batch_items,label_batch_items.c.batch_id==label_batches.c.id)
                .join(devices,label_batch_items.c.device_id==devices.c.id).join(slots,slots.c.id==devices.c.id)
                .join(plans,plans.c.id==units.c.id))
            rows=c.execute(query.where(label_batches.c.state=='WAITING')
                .order_by(units.c.project,units.c.name,label_batches.c.ktv,slots.c.number)).mappings().all()
            return [dict(r) for r in rows]

    def label_batch_records(self,actor,batch_id):
        with self.engine.connect() as c:
            self._auth(c,actor,{'ADMIN','PRINT'})
            batch=self._get(c,label_batches,batch_id)
            if batch['state']!='WAITING':raise DomainError('Lô tem không còn ở trạng thái chờ in.')
            query=select(devices,units.c.name.label('unit'),units.c.project,
                units.c.project_name,slots.c.number,plans.c.quantity).select_from(
                label_batch_items.join(devices,label_batch_items.c.device_id==devices.c.id)
                .join(units,devices.c.unit_id==units.c.id).join(slots,slots.c.id==devices.c.id)
                .join(plans,plans.c.id==units.c.id))
            rows=c.execute(query.where(label_batch_items.c.batch_id==batch_id).order_by(slots.c.number)).mappings().all()
            return batch,[dict(r) for r in rows]

    def confirm_label_batch_printed(self,actor,batch_id,op):
        def fn(c):
            self._auth(c,actor,{'ADMIN','PRINT'})
            batch=self._get(c,label_batches,batch_id)
            if batch['state']!='WAITING':raise DomainError('Lô đã được trạm in xử lý hoặc không còn chờ in.')
            stamp=datetime.now(timezone.utc).isoformat()
            c.execute(update(label_batches).where(label_batches.c.id==batch_id,label_batches.c.state=='WAITING')
                .values(state='PRINTED',printed_at=stamp,printed_by=actor))
            self._log(c,actor,'PRINT_LABEL_BATCH',batch_id,{'unit_id':batch['unit_id'],'ktv':batch['ktv']})
            return batch_id
        return self._atomic(actor,{'ADMIN','PRINT'},op,fn)

    def confirm_label_batch_collected(self,actor,batch_id,op):
        def fn(c):
            self._auth(c,actor,{'KTV'})
            batch=self._get(c,label_batches,batch_id)
            if batch['ktv']!=actor:raise DomainError('Lô tem này thuộc KTV khác.')
            if batch['state']!='PRINTED':raise DomainError('Lô tem chưa được trạm in xác nhận in xong.')
            stamp=datetime.now(timezone.utc).isoformat()
            c.execute(update(label_batches).where(label_batches.c.id==batch_id,label_batches.c.state=='PRINTED')
                .values(state='COLLECTED',collected_at=stamp))
            self._log(c,actor,'COLLECT_LABEL_BATCH',batch_id,{'unit_id':batch['unit_id']})
            return batch_id
        return self._atomic(actor,{'KTV'},op,fn)

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

    def confirm_labels_applied(self, actor, device_id, op):
        def fn(c):
            self._auth(c, actor, {'KTV'})
            device=self._get(c,devices,device_id)
            linked=c.execute(select(jobs).where(jobs.c.device_id==device_id)).mappings().all()
            own=[job for job in linked if job['ktv']==actor]
            if not own:raise DomainError('PC này không được giao cho tài khoản KTV đang đăng nhập.')
            if any(job['state']!='SUCCESS' for job in linked):raise DomainError('Chỉ kết thúc sau khi mọi license được giao cho PC đã kích hoạt thành công.')
            if not device['board_serial'].strip():raise DomainError('PC chưa có serial mainboard trong hồ sơ.')
            slot=self._get(c,slots,device_id);plan=self._get(c,plans,device['unit_id'])
            self._log(c,actor,'KTV_LABELS_APPLIED',device_id,{
                'asset_tag':device['asset_tag'],'board_serial':device['board_serial'],
                'number':slot['number'],'quantity':plan['quantity']})
            return device_id
        return self._atomic(actor,{'KTV'},op,fn)

    def preparation_rows(self, actor):
        with self.engine.connect() as c:
            role=self._auth(c,actor,{'ADMIN','OPERATOR','KTV','QC'})
            query=select(devices,units.c.name.label('unit'),units.c.project,units.c.project_name,
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
            if serial.strip().upper()!=d['board_serial'].strip().upper():raise DomainError('Serial mainboard kiểm tra không khớp serial hồ sơ máy.')
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
