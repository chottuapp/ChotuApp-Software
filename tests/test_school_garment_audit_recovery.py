import unittest
from audit804 import issues_for
from subcategory_inference_support import infer
from catalogue_object_rules import classify
class SoldObjectRecoveryTests(unittest.TestCase):
 def test_abaya_colour_is_not_cosmetics(self):
  row={'name':'BLUSH GRACE ABAYA','Category':'Abayas','description':'A Korean Nida abaya with flowing sleeves. Scarf not included.'}
  self.assertFalse(issues_for(row));self.assertTrue(issues_for(dict(row,Category='Blushers')))
 def test_written_piece_count_precedes_colour(self):
  body='Exude vibrancy in this blush pink. A stunning stitched three-piece ensemble adorned with embroidery. Shirt paired with plain trousers and an embroidered shawl.'
  row={'name':'Lotus','description':body,'Category':'Blushers'}
  self.assertEqual(infer('Lotus',body)[0],'Ready-to-Wear Outfits')
  self.assertEqual(classify(row,'Afrozeh')[0],'Ready-to-Wear Outfits')
  self.assertFalse(issues_for(dict(row,Category='Ready-to-Wear Outfits')))
 def test_school_objects_precede_compatible_contents(self):
  cases=[('A5 Blank White Pages Journal','160 pages of blank paper in an A5 notebook.','Notebooks & Journals'),('Black & White Notebooks Set','Lined pages, 60 pages each notebook, 80 grams paper.','Notebooks & Journals'),('Desk Workspace Pen Holder','Plastic desk organizer, 11 x 11 cm. Holds makeup brushes and stationery.','Pen Holders'),('Panda Stationery Set with LED Lamp','A5 notebook, eraser, marker and 2 gel pen.','Stationery Sets')]
  for name,body,expected in cases:
   with self.subTest(name=name):
    self.assertEqual(infer(name,body)[0],expected)
    self.assertFalse(issues_for({'name':name,'description':body,'Category':expected}))
 def test_real_laptop_never_becomes_paper_notebook(self):
  row={'name':'Intel Notebook','description':'Intel Core processor, 16GB RAM, 512GB SSD, Windows 11.','Category':'Notebooks & Journals'}
  self.assertNotEqual(infer(row['name'],row['description'])[0],'Notebooks & Journals');self.assertTrue(issues_for(row))
 def test_footwear_styling_jeans_is_not_sold_jeans(self):
  row={'name':'Meringue','description':'A cream boucle Mary Jane flat with buckle strap, textured upper and flat sole. Style with jeans and dresses.','Category':'Flats'}
  self.assertFalse(issues_for(row));self.assertTrue(issues_for(dict(row,Category='Jeans')))
