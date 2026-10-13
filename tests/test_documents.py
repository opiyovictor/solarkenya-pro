import importlib.util, tempfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('solar_app',Path(__file__).parents[1]/'document_engine.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_calculation_vat():
    items,subtotal,tax,total=mod.calc([{'description':'Panel','qty':2,'unit_price':1000},{'description':'Install','qty':1,'unit_price':500}],16)
    assert subtotal==2500
    assert tax==400
    assert total==2900
    assert items[0]['amount']==2000

def test_zero_vat():
    _,subtotal,tax,total=mod.calc([{'description':'Service','qty':3,'unit_price':250}],0)
    assert (subtotal,tax,total)==(750,0,750)

def test_pdf_created():
    payload={'number':'TEST-0001','doc_type':'Quotation','customer':'Test Customer','customer_email':'test@example.com','customer_phone':'0700000000','customer_address':'Nairobi','issue_date':'2026-10-13','due_date':'2026-11-12','status':'Draft','currency':'KES','vat_rate':16,'notes':'Payment within 30 days','items':[{'description':'Solar panel','qty':2,'unit_price':1000,'amount':2000}],'subtotal':2000,'tax':320,'total':2320}
    with tempfile.TemporaryDirectory() as d:
        p=mod.make_pdf(payload,mod.COMPANY_DEFAULT,Path(d))
        assert p.exists() and p.stat().st_size>1000
        assert p.read_bytes().startswith(b'%PDF')
