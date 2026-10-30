"""Exact, identity-bound public merchant object types; generic ranges excluded."""
TYPES={
 'smart watches':('Smartwatches','a smartwatch'),'true wireless earbuds':('Earbuds','true wireless earbuds'),
 'lipstick':('Lipsticks','a lipstick'),'liquid lipstick':('Lipsticks','a liquid lipstick'),
 'face wash':('Face Wash','a face wash'),'face serum':('Face Serums','a face serum'),
 'foot cream':('Foot Creams','a foot cream'),'hand cream':('Hand Creams','a hand cream'),
 'nail paint':('Nail Polishes','a nail polish'),'nail polish':('Nail Polishes','a nail polish'),
 'cleanser':('Skin Cleansers','a skin cleanser'),'urifying facial cleanser':('Facial Cleansers','a facial cleanser'),
 'men perfume':('Perfumes & Fragrances','a perfume'),'women perfume':('Perfumes & Fragrances','a perfume'),'unisex perfume':('Perfumes & Fragrances','a perfume'),'perfume':('Perfumes & Fragrances','a perfume'),
 'lip pencil':('Lip Liners','a lip pencil'),'eye liner':('Eyeliners','an eyeliner'),'eyeliners':('Eyeliners','an eyeliner'),
 'moisturizer':('Skin Moisturisers','a skin moisturiser'),'foundation':('Foundations','a foundation'),
 'padded bra':('Bras','a padded bra'),'body suit shapers':('Body Shapers','a body shaper'),
 'highlighter':('Highlighters','a makeup highlighter'),'makeup brush':('Makeup Brushes','a makeup brush'),
 'lip gloss':('Lip Glosses','a lip gloss'),'eye lashes':('False Eyelashes','false eyelashes'),
 'toner':('Facial Toners','a facial toner'),'face powder':('Face Powders','a face powder'),
 'blush':('Blushers','a blusher'),'eyeshade':('Eyeshadows','an eyeshadow'),'eyeshadow':('Eyeshadows','an eyeshadow'),'eye shadow':('Eyeshadows','an eyeshadow'),
 'hair oil':('Hair Oils','a hair oil'),'women body spray':('Body Sprays','a body spray'),'men body spray':('Body Sprays','a body spray'),'body spray':('Body Sprays','a body spray'),
 'hair color':('Hair Colours','a hair colour'),'ampoule pad':('Skincare Pads','an ampoule skincare pad'),
 'hair treatment':('Hair Treatments','a hair treatment'),'mascara':('Mascaras','a mascara'),
 'sunblock':('Sunscreens','a sunblock'),'hair mask':('Hair Masks','a hair mask'),
 'primer':('Makeup Primers','a makeup primer'),'bath sponge':('Bath Sponges','a bath sponge'),
 'hair gel':('Hair Styling Gels','a hair gel'),'talcum powder':('Talcum Powders','a talcum powder'),
 'concealer':('Concealers','a concealer'),'makeup remover/wipes':('Makeup Removers','a makeup remover'),
 'beds':('Beds','a bed'),'room chairs':('Chairs','a chair'),'rocking chairs':('Rocking Chairs','a rocking chair'),
 'knitted throws':('Knitted Throws','a knitted throw'),'shorts':('Shorts','a pair of shorts'),
 'towels':('Towels','a towel'),'tables':('Tables','a table'),'essentials comforter sets':('Comforter Sets','a comforter set'),
 'exotic collection bed spreads':('Bedspreads','a bedspread'),'studio collection bed spreads':('Bedspreads','a bedspread'),
 'sofa sets':('Sofa Sets','a sofa set'),'coffee tables':('Coffee Tables','a coffee table'),
 'breakfast tables':('Breakfast Tables','a breakfast table'),'dining tables':('Dining Tables','a dining table'),
 'exotic collection cushion covers':('Cushion Covers','a cushion cover'),'exotic collection filled cushions':('Filled Cushions','a filled cushion'),
 'exotic collection quilt covers':('Quilt Covers','a quilt cover'),'storage baskets':('Storage Baskets','a storage basket'),
 'alpha collection coverlet sets':('Coverlet Sets','a coverlet set'),'ottomans':('Ottomans','an ottoman'),
 'l-shape sofas':('Sectional Sofas','an L-shaped sofa'),'jeggings':('Jeggings','a pair of jeggings'),
 'co-ord sets':('Clothing Sets','a coordinated clothing set'),'co-ords':('Clothing Sets','a coordinated clothing set'),
 'cap':('Caps','a cap'),'coat':('Coats','a coat'),
 'charms':('Decorative Charms','a decorative charm'),
}
STORES={'Xcessories Hub','Rios','ChenOne','Breakout','Limelight'}
def matched(fact,store):
 return TYPES.get(str(fact.get('product_type') or '').strip().casefold()) if fact and store in STORES else None

# Exact public merchant tags identify sold objects; brand/colour/promotion tags do not.
BATA_TAGS={
 'chappal':('Chappals','A chappal footwear style.'),'chappals':('Chappals','A chappal footwear style.'),
 'kids chappal':('Chappals','A chappal footwear style.'),
 'sneakers':('Sneakers','A sneaker footwear style.'),'men sneakers':('Sneakers','A sneaker footwear style.'),
 'kids sneaker':('Sneakers','A sneaker footwear style.'),'new sneaker':('Sneakers','A sneaker footwear style.'),
 'ladies casual':('Casual Shoes','A casual shoe style.'),'men casual':('Casual Shoes','A casual shoe style.'),'kids casual':('Casual Shoes','A casual shoe style.'),
 'men formal':('Formal Shoes','A formal shoe style.'),'ladies formal':('Formal Shoes','A formal shoe style.'),
 'ladies pumps':('Pumps','A pump footwear style.'),'pumps':('Pumps','A pump footwear style.'),
 'men sandals':('Sandals','A sandal footwear style.'),'ladies sandal':('Sandals','A sandal footwear style.'),
 'kids sandal':('Sandals','A sandal footwear style.'),'boys sandal':('Sandals','A sandal footwear style.'),
 'flip flops':('Flip-Flops','A flip-flop footwear style.'),'football':('Footballs','A football listed by the merchant.'),
}
def merchant_tag_facts(tags,store):
 if store!='Bata' or not isinstance(tags,list) or len(tags)>500:return {}
 matches=[(tag,BATA_TAGS[tag.strip().casefold()]) for tag in tags if isinstance(tag,str) and len(tag)<=300 and tag.strip().casefold() in BATA_TAGS]
 if not matches or len({value[0] for _,value in matches})!=1:return {}
 tag,(category,overview)=matches[0]
 return dict(published_tags=[t for t in tags if isinstance(t,str) and len(t)<=300],reviewed_type_tag=tag,reviewed_tag_category=category,reviewed_tag_overview=overview)
