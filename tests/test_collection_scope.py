import unittest
from types import SimpleNamespace
from collection_scope_support import collection_for,scoped_discover,enable_collection_scope
class CollectionScopeTests(unittest.TestCase):
 def test_only_selected_collection_is_queried(self):
  calls=[]
  def read(url):calls.append(url);return {'products':[{'id':1,'handle':'cup'}]}
  products,complete=scoped_discover({'get_json':read},'https://habitt.com','kitchen',lambda x:None)
  self.assertTrue(complete);self.assertEqual(products[0]['handle'],'cup');self.assertTrue(all('/collections/kitchen/products.json?' in u for u in calls))
 def test_empty_or_repeated_scope_never_falls_back_to_full_catalog(self):
  with self.assertRaises(ValueError):scoped_discover({'get_json':lambda u:{'products':[]}},'https://habitt.com','kitchen',lambda x:None)
  batch=[{'id':i,'handle':str(i)} for i in range(250)]
  with self.assertRaises(ValueError):scoped_discover({'get_json':lambda u:{'products':batch}},'https://habitt.com','kitchen',lambda x:None)
 def test_scope_restores_engine_discovery_after_failure(self):
  old=lambda *a:None
  def failed(*a):raise RuntimeError('source failed')
  g={'_chotuapp_run_site_original':failed,'discover':old,'_chotu_tls':SimpleNamespace()};enable_collection_scope(g)
  with self.assertRaises(RuntimeError):g['_chotuapp_run_site_original']('https://habitt.com','Habitt',None,lambda x:None)
  self.assertIs(g['discover'],old);self.assertIsNone(collection_for('https://zellbury.com'))
