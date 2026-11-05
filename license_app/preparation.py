"""Company preparation: plans, stable numbering and independent inspection."""
from sqlalchemy import Table, Column, String, Integer, ForeignKey, UniqueConstraint, select, insert, update, func
from datetime import datetime, timezone
import uuid
from .core import Ledger, DomainError, meta, units, receiving_points, licenses, devices, jobs, users

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
point_license_plans=Table('point_license_plans',meta,
    Column('id',String,primary_key=True),Column('point_id',String,ForeignKey('receiving_points.id'),nullable=False),
    Column('product',String,nullable=False),Column('sku',String,nullable=False),Column('quantity',Integer,nullable=False),
    UniqueConstraint('point_id','product','sku'))
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
    def save_delivery_plan(self,actor,records,op):
        points={};sku_rows={}
        for row in records or []:
            project=str(row.get('project') or '').strip();project_name=str(row.get('project_name') or '').strip()
            unit_name=str(row.get('unit_name') or '').strip();code=str(row.get('point_code') or '').strip()
            point_name=str(row.get('point_name') or '').strip();pc_qty=row.get('pc_quantity')
            product=str(row.get('product') or '').strip();sku=str(row.get('sku') or '').strip()
            license_qty=row.get('license_quantity',0)
            if not all([project,project_name,unit_name,code,point_name]) or type(pc_qty) is not int or pc_qty<1:
                raise DomainError('Mỗi dòng cần mã/tên dự án, đơn vị, mã điểm, xã/điểm và số PC nguyên dương.')
            point_key=(project.casefold(),unit_name.casefold(),code.casefold())
            point_value={'project':project,'project_name':project_name,'unit_name':unit_name,
                'point_code':code,'point_name':point_name,'pc_quantity':pc_qty}
            if point_key in points and points[point_key]!=point_value:
                raise DomainError('Các dòng cùng điểm phải thống nhất đơn vị, tên xã/điểm và số PC.')
            points[point_key]=point_value
            if bool(product)!=bool(sku):raise DomainError('Mỗi dòng hàng hóa cần có cả loại sản phẩm và SKU.')
            if product and product not in {'Windows','Office','Antivirus'}:
                raise DomainError('Phần mềm phải là Windows, Office hoặc Antivirus.')
            if product and (type(license_qty) is not int or license_qty<0):
                raise DomainError('Số lượng license theo SKU phải là số nguyên từ 0 trở lên.')
            if product and license_qty>pc_qty:
                raise DomainError('Số license của một SKU tại điểm không thể vượt số PC được phân bổ tại điểm đó.')
            if not product:continue
            sku_key=point_key+(product.casefold(),sku.casefold())
            if sku_key in sku_rows:raise DomainError('Trùng dòng SKU trong cùng một xã/điểm.')
            sku_rows[sku_key]={'product':product,'sku':sku,'quantity':license_qty}
        if not points:raise DomainError('Danh sách đơn vị/xã đang trống.')
        def fn(c):
            unit_ids={}
            for row in points.values():
                unit_key=(row['project'],row['unit_name'])
                if unit_key not in unit_ids:
                    unit=c.execute(select(units).where(units.c.project==row['project'],units.c.name==row['unit_name'])).mappings().first()
                    if unit:
                        unit_id=unit['id']
                        c.execute(update(units).where(units.c.id==unit_id).values(project_name=row['project_name']))
                    else:
                        unit_id=str(uuid.uuid4())
                        c.execute(insert(units).values(id=unit_id,project=row['project'],project_name=row['project_name'],name=row['unit_name']))
                        self._log(c,actor,'ADD_UNIT',unit_id,{'project':row['project'],'name':row['unit_name']})
                    unit_ids[unit_key]=unit_id
                unit_id=unit_ids[unit_key]
                point=c.execute(select(receiving_points).where(receiving_points.c.unit_id==unit_id,
                    receiving_points.c.code==row['point_code'])).mappings().first()
                if point:
                    point_id=point['id']
                    device_count=c.execute(select(func.count()).select_from(devices).where(devices.c.point_id==point_id)).scalar_one()
                    if row['pc_quantity']<device_count:raise DomainError('Không thể giảm số PC tại điểm xuống dưới số hồ sơ PC đã khai báo.')
                    c.execute(update(receiving_points).where(receiving_points.c.id==point_id).values(
                        name=row['point_name'],pc_quantity=row['pc_quantity']))
                else:
                    point_id=str(uuid.uuid4())
                    c.execute(insert(receiving_points).values(id=point_id,unit_id=unit_id,code=row['point_code'],
                        name=row['point_name'],pc_quantity=row['pc_quantity']))
                row['_unit_id']=unit_id;row['_point_id']=point_id
                c.execute(update(units).where(units.c.id==unit_id).values(name=units.c.name))
            # Map each normalized location identity to its database point id.
            point_ids={k:v['_point_id'] for k,v in points.items()}
            for key,row in sku_rows.items():
                point_id=point_ids[key[:3]]
                prior=c.execute(select(point_license_plans).where(point_license_plans.c.point_id==point_id,
                    point_license_plans.c.product==row['product'],point_license_plans.c.sku==row['sku'])).mappings().first()
                assigned=c.execute(select(func.count()).select_from(jobs.join(devices,jobs.c.device_id==devices.c.id)
                    .join(licenses,jobs.c.license_id==licenses.c.id)).where(
                    devices.c.point_id==point_id,licenses.c.product==row['product'],licenses.c.sku==row['sku'])).scalar_one()
                if assigned>row['quantity']:raise DomainError('Số lượng SKU không thể giảm xuống dưới số key đã gán cho PC tại điểm.')
                if prior:c.execute(update(point_license_plans).where(point_license_plans.c.id==prior['id']).values(quantity=row['quantity']))
                else:c.execute(insert(point_license_plans).values(id=str(uuid.uuid4()),point_id=point_id,
                    product=row['product'],sku=row['sku'],quantity=row['quantity']))
            # An uploaded schedule is authoritative for the listed points. Any
            # previously allocated SKU omitted from a listed point is reset to
            # zero, provided no PC already consumes that allocation.
            listed_point_ids=set(point_ids.values())
            for point_id in listed_point_ids:
                supplied={(r['product'].casefold(),r['sku'].casefold()) for k,r in sku_rows.items() if point_ids[k[:3]]==point_id}
                existing=c.execute(select(point_license_plans).where(point_license_plans.c.point_id==point_id)).mappings().all()
                for prior in existing:
                    if (prior['product'].casefold(),prior['sku'].casefold()) in supplied:continue
                    assigned=c.execute(select(func.count()).select_from(jobs.join(devices,jobs.c.device_id==devices.c.id)
                        .join(licenses,jobs.c.license_id==licenses.c.id)).where(
                        devices.c.point_id==point_id,licenses.c.product==prior['product'],licenses.c.sku==prior['sku'])).scalar_one()
                    if assigned:raise DomainError('Không thể bỏ phân bổ SKU đã được gán cho PC; giữ dòng SKU và điều chỉnh số lượng phù hợp.')
                    c.execute(update(point_license_plans).where(point_license_plans.c.id==prior['id']).values(quantity=0))
            inventory={(r['product'],r['sku']):r['count'] for r in c.execute(
                select(licenses.c.product,licenses.c.sku,func.count().label('count')).group_by(licenses.c.product,licenses.c.sku)).mappings()}
            planned={(r['product'],r['sku']):r['qty'] for r in c.execute(select(
                point_license_plans.c.product,point_license_plans.c.sku,func.sum(point_license_plans.c.quantity).label('qty')
            ).group_by(point_license_plans.c.product,point_license_plans.c.sku)).mappings()}
            for item,qty in planned.items():
                if qty>inventory.get(item,0):raise DomainError(f'Phân bổ {item[0]} / {item[1]} vượt số key đã nhập kho.')
            for unit_id in set(unit_ids.values()):
                total=c.execute(select(func.coalesce(func.sum(receiving_points.c.pc_quantity),0)).where(
                    receiving_points.c.unit_id==unit_id)).scalar_one()
                assigned=c.execute(select(slots.c.number).where(slots.c.unit_id==unit_id)).scalars().all()
                if assigned and total<max(assigned):raise DomainError('Tổng số PC theo xã/điểm nhỏ hơn số thứ tự PC đã cấp.')
                plan=c.execute(select(plans.c.id).where(plans.c.id==unit_id)).first()
                if plan:c.execute(update(plans).where(plans.c.id==unit_id).values(quantity=total))
                else:c.execute(insert(plans).values(id=unit_id,quantity=total))
                self._log(c,actor,'SET_PC_PLAN',unit_id,{'quantity':total})
            self._log(c,actor,'IMPORT_UNIT_PLAN',op,{'points':len(points),'sku_lines':len(sku_rows)})
            return str(len(points))
        return self._atomic(actor,{'ADMIN'},op,fn)

    def delivery_plan_rows(self,actor):
        with self.engine.connect() as c:
            self._auth(c,actor,{'ADMIN','OPERATOR'})
            stmt=select(units.c.project,units.c.project_name,units.c.name.label('unit'),
                receiving_points.c.id.label('point_id'),receiving_points.c.code,receiving_points.c.name.label('point'),
                receiving_points.c.pc_quantity,plans.c.quantity.label('unit_pc_total'),
                point_license_plans.c.product,point_license_plans.c.sku,point_license_plans.c.quantity.label('license_quantity')
            ).select_from(units.join(receiving_points,receiving_points.c.unit_id==units.c.id)
                .outerjoin(plans,plans.c.id==units.c.id).outerjoin(point_license_plans,
                    point_license_plans.c.point_id==receiving_points.c.id)).order_by(
                        units.c.project,units.c.name,receiving_points.c.name,point_license_plans.c.product,point_license_plans.c.sku)
            return [dict(r) for r in c.execute(stmt).mappings()]

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
                receiving_points.c.name.label('point'),receiving_points.c.code.label('point_code'),
                devices.c.id,devices.c.asset_tag,devices.c.serial,devices.c.board_serial,
                label_batch_items.c.device_id,slots.c.number,plans.c.quantity).select_from(
                label_batches.join(units).join(label_batch_items,label_batch_items.c.batch_id==label_batches.c.id)
                .join(devices,label_batch_items.c.device_id==devices.c.id)
                .outerjoin(receiving_points,devices.c.point_id==receiving_points.c.id).join(slots,slots.c.id==devices.c.id)
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
                units.c.project_name,receiving_points.c.name.label('point'),receiving_points.c.code.label('point_code'),
                slots.c.number,plans.c.quantity).select_from(
                label_batch_items.join(devices,label_batch_items.c.device_id==devices.c.id)
                .join(units,devices.c.unit_id==units.c.id)
                .outerjoin(receiving_points,devices.c.point_id==receiving_points.c.id).join(slots,slots.c.id==devices.c.id)
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
                receiving_points.c.name.label('point'),receiving_points.c.code.label('point_code'),
                slots.c.number,plans.c.quantity,inspections.c.state.label('inspection_state')).select_from(
                devices.join(units).outerjoin(slots,slots.c.id==devices.c.id)
                .outerjoin(receiving_points,devices.c.point_id==receiving_points.c.id)
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
