"""Download selected NYC 311 fields in monthly gzip CSV files; raw data stays ignored."""
import argparse,csv,gzip,json,time,urllib.parse,urllib.request
from pathlib import Path
FIELDS=['unique_key','created_date','closed_date','agency','complaint_type','descriptor','location_type','incident_zip','borough','community_board','latitude','longitude']
BASE='https://data.cityofnewyork.us/resource/erm2-nwe9.json'
def download_month(month,out,page_size=50000,max_rows=None):
 year,m=map(int,month.split('-'));end=f'{year+1}-01-01' if m==12 else f'{year}-{m+1:02}-01'
 where=f"created_date >= '{month}-01T00:00:00' AND created_date < '{end}T00:00:00'"
 count=0;out.mkdir(parents=True,exist_ok=True);partial='-sample' if max_rows is not None else '';dest=out/f'civicpulse_{month}{partial}.csv.gz';temp=dest.with_suffix(dest.suffix+'.tmp')
 try:
  with gzip.open(temp,'wt',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
   while True:
    limit=min(page_size,max_rows-count) if max_rows is not None else page_size
    query={'$select':','.join(FIELDS),'$where':where,'$order':'created_date,unique_key','$limit':limit,'$offset':count}
    request=urllib.request.Request(BASE+'?'+urllib.parse.urlencode(query),headers={'User-Agent':'CivicPulse-reproducible-research/1.0'})
    for attempt in range(4):
     try:
      with urllib.request.urlopen(request,timeout=90) as r:rows=json.load(r)
      break
     except Exception:
      if attempt==3:raise
      time.sleep(2**attempt)
    for row in rows:writer.writerow({k:row.get(k,'') for k in FIELDS})
    count+=len(rows)
    if len(rows)<limit or (max_rows is not None and count>=max_rows):break
  temp.replace(dest)
 except Exception:
  temp.unlink(missing_ok=True);raise
 return {'month':month,'rows':count,'path':str(dest),'source':BASE,'partial_sample':max_rows is not None}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--month',help='YYYY-MM; omit for all months of 2025');p.add_argument('--output',default='data');p.add_argument('--max-rows',type=int,help='Smoke sample only; never use for reproducing recorded metrics');a=p.parse_args()
 if a.max_rows is not None and a.max_rows<1:p.error('--max-rows must be positive')
 months=[a.month] if a.month else [f'2025-{m:02}' for m in range(1,13)]
 for month in months:print(json.dumps(download_month(month,Path(a.output),max_rows=a.max_rows)),flush=True)
