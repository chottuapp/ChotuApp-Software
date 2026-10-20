import json,unittest
from khaadi_public_evidence_support import public_product_evidence
URL='https://pk.khaadi.com/black-cambric-kurta/ABC.html'
def page(currency='PKR',sku='ABC'):
    data={'@type':'Product','sku':sku,'name':'Black Cambric Kurta','offers':{'url':URL,'priceCurrency':currency,'price':'6000.00','availability':'http://schema.org/InStock'},'image':['/images/kurta.jpg']}
    return '<link rel="canonical" href="'+URL+'"><script type="application/ld+json">'+json.dumps(data)+'</script><div class="set-item" data-pid="ABC"><div data-attr="size"><div><input class="options-select" data-pid="ABC" data-attr-value="0XS" instock><span>XS</span></div></div></div><div class="set-item" data-pid="PANTS"><span>PKR 3500</span><div data-attr="size"><div><input class="options-select" data-pid="PANTS" data-attr-value="00M"><span>M</span></div></div></div>'
class KhaadiEvidenceTests(unittest.TestCase):
    def test_master_price_and_sizes_do_not_include_matching_pants(self):
        d=public_product_evidence(page(),URL)
        self.assertEqual(d['product_price_pkr'],'6000.00');self.assertEqual([x['label'] for x in d['sizes']],['XS'])
        self.assertEqual(d['images'],['https://pk.khaadi.com/images/kurta.jpg'])
    def test_unselected_stock_and_master_offer_do_not_prove_size_prices(self):
        d=public_product_evidence(page(),URL)
        self.assertFalse(d['import_ready']);self.assertFalse(d['variant_data_verified'])
        self.assertIsNone(d['sizes'][0]['available']);self.assertIsNone(d['sizes'][0]['price'])
    def test_foreign_currency_and_wrong_identity_rejected(self):
        for html in (page('USD'),page(sku='OTHER'),page().replace('href="'+URL,'href="https://us.khaadi.com/other.html')):
            with self.assertRaises(ValueError):public_product_evidence(html,URL)
    def test_offer_must_match_the_canonical_product(self):
        html=page().replace('"url": "'+URL+'"','"url": "https://pk.khaadi.com/pants/OTHER.html"')
        with self.assertRaisesRegex(ValueError,'Offer belongs'):public_product_evidence(html,URL)
