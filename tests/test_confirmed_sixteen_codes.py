"""Exercise actual XLSX code assignment for every owner-confirmed new store."""
import json,tempfile,unittest,zipfile
from pathlib import Path
from openpyxl import load_workbook
from rule804_pipeline import process
from test_fresh26_pipeline import book
ROOT=Path(__file__).resolve().parents[1]
class ConfirmedSixteenCodesTests(unittest.TestCase):
 def test_all_confirmed_codes_fill_every_product_as_text_and_preserve_source(self):
  request=json.loads((ROOT/'cloud/new-store-fetch-request.json').read_text());codes=json.loads((ROOT/'cloud/confirmed-shop-codes.json').read_text())
  self.assertFalse(request['shop_codes_pending_owner']);self.assertEqual(len(request['stores']),16)
  for site in request['stores']:
   with self.subTest(store=site['name']),tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'source.xlsx';out=Path(tmp)/'checked.xlsx';book(source,price=1499.95)
    b=load_workbook(source);sheet=b['Products'];values=[c.value for c in sheet[2]];values[1]='p2';values[10]='=F3*2';values[11]=5;sheet.append(values);b.save(source);b.close();before=source.read_bytes()
    process(source,out,site['name'],codes)
    b=load_workbook(out);sheet=b['Products']
    self.assertEqual([sheet.cell(r,1).value for r in (2,3)],[site['shop_code']]*2)
    self.assertTrue(all(sheet.cell(r,1).data_type=='s' for r in (2,3)))
    self.assertEqual([sheet.cell(r,6).value for r in (2,3)],[1499.95]*2);self.assertEqual(sheet['K2'].value,'=F2*2');self.assertEqual(sheet['K3'].value,'=F3*2');b.close()
    self.assertEqual(source.read_bytes(),before)
    with zipfile.ZipFile(source) as a,zipfile.ZipFile(out) as z:
     for name in a.namelist():
      if name!='xl/worksheets/sheet1.xml':self.assertEqual(a.read(name),z.read(name),name)
