"""Download verified Rule 804 copies into the local daily folder without overwriting files."""
import argparse,datetime,hashlib,os,re,shutil,tempfile,urllib.request
from pathlib import Path
FILES=[{'name': 'Miss Rose.xlsx', 'file': 'Miss_Rose_Rule804.xlsx', 'sha256': '7bf942e67eab3ce4b80fec5e34cdcde45c098f507130ae95dbc02935e722b74c'}, {'name': 'Rivaj UK.xlsx', 'file': 'Rivaj_UK_Rule804.xlsx', 'sha256': '7042244e5418141e2e2126d81c8e92bd7b25094630d01a215e6c151e8b162885'}, {'name': 'The Hanger Pakistan.xlsx', 'file': 'The_Hanger_Pakistan_Rule804.xlsx', 'sha256': '46c83cb05f0255f0d5a04a6350fbdb272f5755388671c8fd98fa3343ef47624b'}, {'name': 'Vince Care.xlsx', 'file': 'Vince_Care_Rule804.xlsx', 'sha256': '94bfafa6119de2163faa3710ee34e336039c5b7873b84dba21170816a337e2b7'}]

def save_copy(source,folder,name):
    folder.mkdir(parents=True,exist_ok=True);source=Path(source);base=Path(name);index=0
    digest=hashlib.sha256(source.read_bytes()).digest()
    while True:
        destination=folder/(base.stem+(' ('+str(index)+')' if index else '')+base.suffix)
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).digest()==digest:return destination
            index+=1;continue
        try:stream=destination.open('xb')
        except FileExistsError:continue
        try:
            with stream,source.open('rb') as incoming:shutil.copyfileobj(incoming,stream)
        except BaseException:
            destination.unlink(missing_ok=True);raise
        return destination

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{7,40}',args.revision):parser.error('Invalid revision')
    base='https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/'+args.revision+'/catalog-files/rule804-20261017-run38958847659/'
    folder=Path.home()/'Desktop'/'ANAS_DATA_FETCH'/'Save daily data with dates'/datetime.datetime.now().astimezone().date().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        for record in FILES:
            file=Path(tmp)/record['file'];urllib.request.urlretrieve(base+record['file'],file)
            if hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:raise RuntimeError('Download verification failed: '+record['file'])
        for record in FILES:print('Rule 804 saved:',save_copy(Path(tmp)/record['file'],folder,record['name']))
    print('Done. Existing files preserved.')
    os.startfile(folder) if os.name=='nt' else None

if __name__=='__main__':main()
