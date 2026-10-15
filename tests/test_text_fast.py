from pathlib import Path
import ast
import html
import random
import re
import sys
import time
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import install_adaptive_speed as installer

class TextFastTests(unittest.TestCase):
    def test_plain_and_html_strings_match_old_normalizer(self):
        before={'re':re,'html':html,'BeautifulSoup':BeautifulSoup};after=dict(before)
        exec(installer.OLD_TEXT,before);exec(installer.NEW_TEXT,after)
        samples=[None,False,0,1,1490,[],{},'','Hello  world','a\r\nb','\x00abc','Vincé Vitamin C','\u200bBrand','A &amp; B','&lt;b&gt;Text','<p>A<br>B &nbsp;</p>','<table><tr><td>Size</td><td>30ML</td></tr></table>','<b>incomplete','5 > 3','https://example.com/product','a<!-- hide -->b']
        rng=random.Random(42);alphabet='abcéپاکستان0123> \t\r\n\x00'
        samples += [''.join(rng.choice(alphabet) for _ in range(rng.randrange(1,100))) for _ in range(500)]
        for value in samples:self.assertEqual(before['txt'](value),after['txt'](value),repr(value))
        values=['Vitamin C Serum 30ML Pack '+str(i%3) for i in range(5000)]
        start=time.perf_counter();old=[before['txt'](v) for v in values];old_time=time.perf_counter()-start
        start=time.perf_counter();new=[after['txt'](v) for v in values];new_time=time.perf_counter()-start
        self.assertEqual(old,new)
        print('Plain-text CPU benchmark only: old %.3fs, new %.3fs.'%(old_time,new_time))
    def test_surgical_text_patch_only_and_idempotent(self):
        source=(ROOT/'main.py').read_text().replace(installer.NEW_TEXT,installer.OLD_TEXT,1)
        changed=installer.text_transform(source.encode())
        self.assertEqual(changed.decode(),source.replace(installer.OLD_TEXT,installer.NEW_TEXT,1))
        self.assertEqual(installer.text_transform(changed),changed)
