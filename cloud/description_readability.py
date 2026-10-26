"""Lossless paragraph layout; never shorten or invent product facts."""
import re

def format_description(value):
 text=str(value or '').replace('\r\n','\n').replace('\r','\n')
 result=[]
 for paragraph in re.split(r'\n\s*\n',text):
  paragraph='\n'.join(line.strip() for line in paragraph.splitlines()).strip()
  if not paragraph:continue
  if len(paragraph.split())>110 and '\n' not in paragraph:
   sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',paragraph)
   group=[];size=0
   for sentence in sentences:
    if group and size+len(sentence.split())>85:
     result.append(' '.join(group));group=[];size=0
    group.append(sentence);size+=len(sentence.split())
   if group:result.append(' '.join(group))
  else:result.append(paragraph)
 return '\n\n'.join(result)

def issues(value):
 text=str(value or '')
 problems=[]
 for paragraph in re.split(r'\n\s*\n',text):
  if '\n' not in paragraph and len(paragraph.split())>110 and len(re.findall(r'[.!?]\s+[A-Z]',paragraph))>=2:
   problems.append('Description readability: split dense prose into clear paragraphs without losing facts');break
 if any(line.startswith(('   ','\t')) for line in text.splitlines()):problems.append('Description alignment: remove inconsistent leading indentation')
 return problems
