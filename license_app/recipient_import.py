"""Template and safe Excel parser for license-stage recipient allocations."""
from io import BytesIO
from pathlib import Path
from openpyxl import Workbook, load_workbook

HEADERS=("Mã dự án","Tên dự án","Tên đơn vị được cấp","Mã điểm",
         "Tên xã/phường/đơn vị","Số PC tại điểm","Phần mềm","SKU","Số license được cấp")
MAX_BYTES=5*1024*1024
MAX_ROWS=2000

def delivery_template_xlsx():
    wb=Workbook();ws=wb.active;ws.title="PHAN_BO_CAP_BAN_QUYEN"
    ws.append(list(HEADERS));ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:I{MAX_ROWS+1}"
    for col,width in zip("ABCDEFGHI",[18,28,32,18,34,18,18,28,24]):
        ws.column_dimensions[col].width=width
    note=wb.create_sheet("HUONG_DAN")
    note.append(["Mỗi dòng ghi một xã/điểm và một loại license. Lặp lại mã điểm, số PC và thông tin đơn vị cho từng SKU."])
    note.append(["Nếu một điểm chưa cấp một loại license, không cần tạo dòng cho SKU đó."])
    note.append(["Phần mềm nhập đúng tên trong kho: Windows, Office hoặc Antivirus; SKU phải trùng kho key."])
    note.append(["Số PC là tổng PC tại điểm; số license là số key của SKU cấp cho điểm."])
    out=BytesIO();wb.save(out);return out.getvalue()

def parse_delivery_xlsx(filename,data):
    if Path(filename).suffix.lower()!=".xlsx":raise ValueError("Chỉ nhận file Excel .xlsx.")
    if not isinstance(data,bytes) or not data or len(data)>MAX_BYTES:raise ValueError("Tệp trống hoặc lớn hơn 5 MB.")
    wb=load_workbook(BytesIO(data),read_only=True,data_only=True)
    try:
        ws=wb.active
        header=next(ws.iter_rows(min_row=1,max_row=1,values_only=True),None)
        if not header:raise ValueError("Excel chưa có dòng tiêu đề.")
        names=[str(v or "").strip() for v in header[:len(HEADERS)]]
        if tuple(names)!=HEADERS:raise ValueError("Tiêu đề/cột Excel chưa đúng mẫu đã tải.")
        result=[]
        for line,row in enumerate(ws.iter_rows(min_row=2,max_row=MAX_ROWS+1,max_col=len(HEADERS),values_only=True),2):
            values=[v if v is not None else "" for v in row]
            if not any(str(v).strip() for v in values):continue
            project,project_name,unit_name,point_code,point_name=map(lambda v:str(v).strip(),values[:5])
            pc_raw=values[5]
            if isinstance(pc_raw,bool):raise ValueError(f"Dòng {line}: số PC không hợp lệ.")
            try:pc_qty=int(pc_raw)
            except (TypeError,ValueError):raise ValueError(f"Dòng {line}: số PC phải là số nguyên.") from None
            if str(pc_raw).strip()!=str(pc_qty) and not (isinstance(pc_raw,float) and pc_raw==pc_qty):
                raise ValueError(f"Dòng {line}: số PC phải là số nguyên.")
            product,sku=str(values[6]).strip(),str(values[7]).strip()
            raw_qty=values[8]
            if bool(product)!=bool(sku):raise ValueError(f"Dòng {line}: điền đủ phần mềm và SKU.")
            if product:
                if isinstance(raw_qty,bool):raise ValueError(f"Dòng {line}: số license không hợp lệ.")
                try:license_qty=int(raw_qty)
                except (TypeError,ValueError):raise ValueError(f"Dòng {line}: số license phải là số nguyên.") from None
                if str(raw_qty).strip()!=str(license_qty) and not (isinstance(raw_qty,float) and raw_qty==license_qty):
                    raise ValueError(f"Dòng {line}: số license phải là số nguyên.")
            else:license_qty=0
            result.append({'project':project,'project_name':project_name,'unit_name':unit_name,
                'point_code':point_code,'point_name':point_name,'pc_quantity':pc_qty,
                'product':product,'sku':sku,'license_quantity':license_qty})
        if not result:raise ValueError("Excel chưa có dòng phân bổ.")
        return result
    finally:wb.close()
