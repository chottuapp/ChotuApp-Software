"""Read public JSON-only Next server records; never execute source scripts."""
import json,re

def public_next_product_state(html):
    """Read JSON-only public Next records, including split stream chunks."""
    from bs4 import BeautifulSoup
    fields={'id','name','title','slug','price','basePrice','salePrice','description','images','imageUrls','image','category','categoryId','variants','sizes','colors','stock','stockQuantity','isActive','active','currency','sku','isAvailable','inStock','quantity','sale','discount','sellingPrice','retailPrice','regularPrice','discountPrice','minPrice','maxPrice','stockOnHand','stockReserved','stockAvailable','inventoryQuantity','productId','colorName','sizeName','sizeLabel','colorHex','priceOverride','department','size','color','status','isPublished','trackStock','stockQty','baseRetailPrice','availableStock','value','hexCode','url','imageUrl','position','alt','onHand','reserved','available','isPrimary'}
    result={'hydration_products':[],'object_key_shapes':[],'product_contexts':[],'public_variant_data':[],'public_variant_shapes':[]}
    def clean(value):
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k in fields}
        if isinstance(value,list):return [clean(v) for v in value[:500]]
        return value
    def walk(value):
        if isinstance(value,dict):
            if 'variants' in value or 'product' in value:
                shape=sorted(value)
                if shape not in result['object_key_shapes']:result['object_key_shapes'].append(shape)
            if isinstance(value.get('variants'),list):
                result['public_variant_data'].append(clean(value['variants']))
                result['public_variant_shapes'].append([{k:sorted(v) if isinstance(v,dict) else type(v).__name__ for k,v in variant.items()} for variant in value['variants'][:3] if isinstance(variant,dict)])
            if isinstance(value.get('product'),dict):
                result['product_contexts'].append({k:clean(v) for k,v in value.items() if k in ('product','variants','images','sizes','colors')})
            if value.get('id') and (value.get('name') or value.get('title')):
                candidate=clean(value)
                if len(json.dumps(candidate))<150000 and candidate not in result['hydration_products']:result['hydration_products'].append(candidate)
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    chunks=[]
    for node in BeautifulSoup(html,'html.parser').find_all('script'):
        text=node.get_text()
        for match in re.finditer(r'self\.__next_f\.push\(',text):
            try:array,_=json.JSONDecoder().raw_decode(text[match.end():])
            except ValueError:continue
            if isinstance(array,list) and len(array)>=2 and isinstance(array[1],str):chunks.append(array[1])
    for line in ''.join(chunks).splitlines():
        try:walk(json.loads(line.partition(':')[2]))
        except ValueError:pass
    return result

