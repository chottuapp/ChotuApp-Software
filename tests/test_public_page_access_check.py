import unittest
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from public_page_access_check import denied,product_link
class PublicPageAccess(unittest.TestCase):
 def test_access_controls_are_terminal(self):
  for status,body in [(403,'Forbidden'),(429,'Slow down'),(200,'<title>Just a moment</title>'),(200,'Please verify you are human'),(200,'<title>Captcha Verification</title>')]:self.assertTrue(denied(status,body))
  self.assertFalse(denied(200,'Ordinary public product details'))
  self.assertFalse(denied(200,'<script src="https://example.com/recaptcha.js"></script><main>Public product details</main>'))
 def test_only_explicit_same_site_permitted_product_links(self):
  policy=RobotFileParser();policy.parse(['User-agent: *','Disallow: /private'])
  soup=BeautifulSoup('<div class="products"><div class="product"><a href="https://other.example/product/a">a</a><a href="/private/a">a</a><a href="/product/item">actual</a></div></div>','html.parser')
  self.assertEqual(product_link(soup,'https://gift4u.pk',policy),'https://gift4u.pk/product/item')
