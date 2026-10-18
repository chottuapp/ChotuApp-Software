"""Build the consolidated public bundle without including user data."""
from pathlib import Path
import hashlib
import json
import zipfile
import remove_daily_auto
import install_speed_patch
import install_fast_fetch
import install_farda_source

ROOT=Path(__file__).resolve().parent

def build():
    source=remove_daily_auto.transform((ROOT/'main.py').read_text())
    source=install_farda_source.transform(install_fast_fetch.transform(source))
    guard="if __name__=='__main__':"
    hook='\nfrom website_order_support import enable_website_order\nenable_website_order(globals())\n\n'
    if source.count(guard)!=1:raise ValueError('Unexpected startup entry point')
    source=source.replace(guard,hook+guard,1)
    integrated,_=install_speed_patch.transform(source.encode())
    compile(integrated,'main.py','exec')
    files={'main.py':integrated}
    for name in ['resume_support.py','manual_mode_support.py','remove_daily_auto.py','fast_fetch_support.py','farda_source_support.py','complete_description_support.py','ranking_support.py','website_order_support.py','requirements.txt','install_complete_update.py','COMPLETE_PACKAGE.md','SAVED_RUNS.md','SPEED_PATCH.md','FAST_FETCH.md']:
        files[name]=(ROOT/name).read_bytes()
    template=(ROOT/'importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx').read_bytes()
    files['ChotuApp_Template.xlsx']=template
    files['Chotu_Products_Import_Template_Discount_Tags.xlsx']=template
    files['PACKAGE_SHA256.json']=json.dumps({name:hashlib.sha256(data).hexdigest() for name,data in files.items()},indent=2).encode()
    output=ROOT/'ChotuApp_Complete_Updated.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr('ChotuApp_Complete_Updated/'+name,data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,data in files.items():assert archive.read('ChotuApp_Complete_Updated/'+name)==data
    print('Verified consolidated ZIP:',output.name,'files',len(files),'bytes',output.stat().st_size)
    return output

if __name__=='__main__':build()
