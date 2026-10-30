import unittest,tempfile,copy,json
from datetime import datetime,timezone
from unittest.mock import patch
from audit804_automation import validated_facts,refresh
from reviewed_source_types import merchant_tag_facts
from hold804_repairs import category,description
from audit804 import issues_for
class MerchantTagRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.now(timezone.utc);self.sites={'Bata':{'url':'https://www.bata.com.pk'}}
  self.item=dict(store='Bata',product_id='new-product',name='Bata - Women',source_url='https://www.bata.com.pk/products/new-article',product=dict(handle='new-article',title='Bata - Women',type='Bata',description='Article 123. Original product size choices retained.',tags=['Bata','Ladies Casual','Color_Blue']))
 def report(self):return dict(run_id='1',checked_utc=self.now.isoformat(),results=[self.item])
 def test_new_product_uses_exact_source_tag_without_manual_product_record(self):
  fact=validated_facts(self.report(),self.sites,self.now)[0];self.assertEqual(fact['reviewed_tag_category'],'Casual Shoes');self.assertEqual(fact['reviewed_type_tag'],'Ladies Casual')
  row=dict(product_id=self.item['product_id'],name=self.item['name'],source_url=self.item['source_url'],description=self.item['product']['description'])
  with patch('hold804_repairs.public_facts',return_value=fact):
   fixed,_=description(row,'Bata');label=category(dict(row,description=fixed),'Bata')[0]
  self.assertEqual(label,'Casual Shoes');self.assertIn(row['description'],fixed);self.assertEqual(issues_for(dict(row,description=fixed,Category=label),row),[])
 def test_brand_colour_promotion_and_conflicting_types_stay_unresolved(self):
  for tags in (['Reebok','Black','New Arrivals'],['Sneakers','Chappal'],['Sneakers accessory'],None):self.assertEqual(merchant_tag_facts(tags,'Bata'),{})
  self.assertEqual(merchant_tag_facts(['Sneakers'],'Another Store'),{})
 def test_tag_receipt_survives_rotating_source_batches(self):
  with tempfile.TemporaryDirectory() as tmp:
   from pathlib import Path
   (Path(tmp)/'cloud').mkdir();report=self.report()
   digest,_,cache=refresh(tmp,lambda *a:json.dumps(report),self.sites)
   self.assertEqual(cache[0]['reviewed_tag_category'],'Casual Shoes');report['results']=[]
   next_digest,_,cache=refresh(tmp,lambda *a:json.dumps(report),self.sites,cache)
   self.assertEqual(next_digest,digest);self.assertEqual(cache[0]['reviewed_type_tag'],'Ladies Casual')
 def test_unmatched_product_identity_cannot_supply_tag_proof(self):
  self.item['product']['handle']='another-product';self.assertEqual(validated_facts(self.report(),self.sites,self.now),[])
