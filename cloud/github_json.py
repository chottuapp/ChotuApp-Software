"""Read complete GitHub JSON reports, including files above the Contents 1MB limit."""
import json

def read_json(gh,path):
 payload=gh('api',path,'-H','Accept: application/vnd.github.raw+json')
 if not isinstance(payload,str) or len(payload.encode())>16*1024*1024:raise ValueError('GitHub JSON report exceeds bounded read size')
 result=json.loads(payload)
 if not isinstance(result,dict):raise ValueError('GitHub JSON report must be an object')
 if result.get('encoding')=='none' and 'content' in result:raise ValueError('GitHub returned metadata instead of complete raw report')
 return result
