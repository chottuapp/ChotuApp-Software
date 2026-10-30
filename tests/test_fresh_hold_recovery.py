"""Regressions for explicit source objects from the 30 October held generation."""
import unittest
from unittest.mock import patch
from hold804_repairs import category, description
from audit804 import issues_for
from audit804_semantics import review


class FreshHoldRecoveryTests(unittest.TestCase):
    def row(self, name, body):
        return dict(name=name, description=body, product_id='fixture',
                    source_url='https://source.example/products/fixture')

    def test_explicit_sold_objects_pass_independent_review(self):
        cases = [
            ('Design by DAS', 'Sunflower Charm', 'Handmade crochet sunflower charm with a hanging loop; use as a keychain or bag charm.', 'Bag & Key Charms'),
            ('Design by DAS', 'Crochet Flower Buttons', 'Handmade crochet flower buttons (Pack of 6) for sewing garments.', 'Sewing Buttons'),
            ('Design by DAS', 'Python Textured Mustard Kimono', 'Fabric: Parachute\nModel: Wearing size M, height 5’10″', 'Kimonos'),
            ('Habitt', 'Glass Oil Jug 1000ml – Transparent Oil Dispenser with Wooden Lid', '1000ml glass oil jug with measurement markings.', 'Oil Dispensers'),
            ('Habitt', 'MILK STRANER', 'Source product options and dimensions retained.', 'Strainers & Colanders'),
            ('Habitt', '1Pc Juice Dispenser with Stand', 'Beverage container with tap; Size: 3.5LTR.', 'Beverage Dispensers'),
            ('Habitt', 'Rotating Rice Dispenser – 5kg Capacity', 'A grain storage container with measuring cup.', 'Grain Dispensers'),
            ('Habitt', 'Stainless Steel Deep Golden Bowl', 'Serving bowl available in 16 cm / 18 cm.', 'Serving Bowls'),
            ('Habitt', 'Dinosaur Kids Sipper Cup', 'Drinking cup with straw and lid.', 'Sipper Cups'),
            ('Habitt', '360° Rotating Snack Tray', 'Multi-compartment serving platter for dry snacks only.', 'Snack Serving Trays'),
            ('Generation', 'Hand-Crochet Bow Tie', 'Hand-crocheted bow charm. Use as a bag tie or hair accessory.', 'Bag & Hair Charms'),
            ('Rios', 'Amrij Matte Lip Color', 'Matte lipcolor for fuller lips. Ingredients and shades retained.', 'Lip Colours'),
            ('Rios', 'RUBY FACE SPONGE BIG GIFT PACKAGE 1 MZGJ01 1PC', 'A face sponge for gentle cleansing and exfoliation. Includes 1 piece.', 'Facial Cleansing Sponges'),
            ('Limelight', '2 Piece Lawn Saree-Embroidered (Pret)', 'Blouse\nDyed blouse with embroidery\nSaree\nGold paste print\nWeight: 748 g', 'Saree & Blouse Sets'),
            ('Shop Modest', 'Girls Rawsilk Blue Formal Outfit', 'Top: Blue kurta style shirt\nBottom: Dhaka pajama trouser\nDupatta: Pink Net Dupatta\nA136', 'Clothing Sets'),
        ]
        for store, name, body, expected in cases:
            with self.subTest(store=store, name=name):
                row = self.row(name, body)
                result = category(row, store)
                self.assertIsNotNone(result)
                self.assertEqual(result[0], expected)
                self.assertEqual(issues_for(dict(row, Category=expected), row), [])

    def test_sparse_explicit_objects_keep_identity_without_new_claims(self):
        for store, name, expected in [
            ('Rios', 'Sensodyne Interdentaires Floss', 'Dental Floss'),
            ('Rios', 'Sensodyne Precision Extra Souple Tooth Brush', 'Toothbrushes'),
            ('Rios', 'RHD MAKEUP FIXER SPRAY SET & SERVE150ML', 'Makeup Setting Sprays'),
            ('Rawayat', 'Zircon Ear-cuff-13 (White)', 'Ear Cuffs'),
        ]:
            with self.subTest(name=name):
                row = self.row(name, name)
                fixed, reason = description(row, store)
                self.assertTrue(reason)
                self.assertIn(name, fixed)
                self.assertNotRegex(fixed, r'(?i)sterling|genuine zircon|hypoallergenic|waterproof|pair of')
                self.assertEqual(category(dict(row, description=fixed), store)[0], expected)
                self.assertEqual(issues_for(dict(row, description=fixed, Category=expected), row), [])

    def test_offer_is_plant_set_only_with_explicit_count_and_included_plants(self):
        body = ('3 Beautiful Fruit Plants for Just Rs. 3,499!\n'
                "What's Included in This Combo?\n"
                'Lemon Plant – Lemon plant description.\n'
                'Guava Plant – Guava plant description.\n'
                'Pomegranate Plant – Pomegranate plant description.')
        row = self.row('Ras Bhari Offer', body)
        with patch('hold804_repairs.public_facts', return_value=None):
            fixed, _ = description(row, 'Hello Maali')
            self.assertIn(body, fixed)
            self.assertEqual(category(dict(row, description=fixed), 'Hello Maali')[0], 'Live Plant Sets')
            self.assertEqual(issues_for(dict(row, description=fixed, Category='Live Plant Sets'), row), [])
            unknown = self.row('Offer', 'Plant-themed gift with refreshing floral fragrance.')
            self.assertIsNone(category(unknown, 'Hello Maali'))
            self.assertNotEqual(review(unknown['name'], unknown['description'], 'Live Plant Sets'), [])

    def test_fragrance_narrative_is_not_plant_or_care_product_evidence(self):
        body = ('A sophisticated fragrance crafted for the man who carries himself with confidence. '
                'It opens with bergamot and mint. Do apply to pulse points. '
                'Do not rub your wrists together after spraying.')
        self.assertEqual(review('Monarchist Pour Homme', body, 'Perfumes & Fragrances'), [])
        self.assertNotEqual(review('Body Lotion', body, 'Perfumes & Fragrances'), [])

    def test_ambiguous_and_component_only_sources_stay_held(self):
        cases = [
            ('Rawayat', 'Short Set-55 (Golden)', 'Short Set-55 (Golden)'),
            ('Bata', 'Sparx - Men', '877-6280\nSize: 40/6, 41/7'),
            ('Design by DAS', 'Kimono Button', 'Button for a kimono.'),
            ('Generation', 'Bow Tie', 'A bow tie with supplied colour options.'),
            ('Limelight', '2 Piece Lawn Saree', 'Fabric care instructions only.'),
        ]
        for store, name, body in cases:
            with self.subTest(name=name), patch('hold804_repairs.public_facts', return_value=None):
                self.assertIsNone(category(self.row(name, body), store))
        for name in ('Replacement Lid for Oil Dispenser', 'Spare Tap for Juice Dispenser'):
            with self.subTest(name=name):
                self.assertNotEqual(review(name, 'Replacement component only.', 'Oil Dispensers'), [])
                result = category(self.row(name, 'Replacement component only.'), 'Habitt')
                self.assertTrue(result is None or result[0] not in ('Oil Dispensers', 'Beverage Dispensers'))
        self.assertNotEqual(review('Unidentified item', 'Unknown source object.', 'Bag & Key Charms'), [])


if __name__ == '__main__':
    unittest.main()
