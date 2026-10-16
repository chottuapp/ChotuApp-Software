import tempfile,unittest
from pathlib import Path
from cloud_sync_windows import archive_daily_excel
class ArchiveTests(unittest.TestCase):
 def test_numbering_dates_and_retry_deduplication(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'Seran.xlsx';source.write_bytes(b'first');archive=root/'daily'
   first=archive_daily_excel(source,archive,'1','Seran.xlsx','2026-10-17')
   self.assertEqual(first.name,'Seran.xlsx')
   self.assertEqual(archive_daily_excel(source,archive,'1','Seran.xlsx','2026-10-18'),first)
   second=archive_daily_excel(source,archive,'2','Seran.xlsx','2026-10-17');self.assertEqual(second.name,'Seran (1).xlsx')
   source.write_bytes(b'changed');third=archive_daily_excel(source,archive,'2','Seran.xlsx','2026-10-17');self.assertEqual(third.name,'Seran (2).xlsx');self.assertEqual(first.read_bytes(),b'first')
   nextday=archive_daily_excel(source,archive,'3','Seran.xlsx','2026-10-18');self.assertEqual(nextday.name,'Seran.xlsx');self.assertEqual(nextday.parent.name,'2026-10-18')
if __name__=='__main__':unittest.main()
