import pytest
from license_app.core import DomainError
from license_app.sheet_sync import PLAN_HEADERS, PLAN_TAB, read_delivery_plan


class Call:
    def __init__(self,value):self.value=value
    def execute(self):return self.value


class ValuesAPI:
    def __init__(self,values):self._values=values
    def get(self,**kwargs):return Call({'values':self._values})


class SpreadsheetAPI:
    def __init__(self,values):self._values=values
    def get(self,**kwargs):return Call({'sheets':[{'properties':{'title':PLAN_TAB}}]})
    def values(self):return ValuesAPI(self._values)


class Service:
    def __init__(self,values):self._api=SpreadsheetAPI(values)
    def spreadsheets(self):return self._api


def row(*values):return list(values)+['']*(len(PLAN_HEADERS)-len(values))


def test_read_delivery_plan_parses_points_and_sku_quotas():
    values=[PLAN_HEADERS,
        row('P01','Dự án thử','Đơn vị nhận','D01','Xã A',2,'Windows','W11',2),
        row('P01','Dự án thử','Đơn vị nhận','D01','Xã A',2,'Office','O365',1)]
    records=read_delivery_plan(Service(values),'sheet-id')
    assert len(records)==2
    assert records[0]['pc_quantity']==2
    assert records[0]['license_quantity']==2
    assert records[1]['product']=='Office'


@pytest.mark.parametrize('values',[
    [['wrong header']],
    [PLAN_HEADERS,row('P01','Dự án thử','Đơn vị nhận','D01','Xã A',2,'Windows','W11',3)],
    [PLAN_HEADERS,row('P01','Dự án thử','Đơn vị nhận','D01','Xã A',2,'Windows','W11','=2')],
    [PLAN_HEADERS,row('P01','Dự án thử','Đơn vị nhận','D01','Xã A',2,'Windows','',2)],
])
def test_read_delivery_plan_rejects_invalid_sheet_rows(values):
    with pytest.raises(DomainError):read_delivery_plan(Service(values),'sheet-id')
