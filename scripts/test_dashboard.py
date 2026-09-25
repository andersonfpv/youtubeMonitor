import csv
from pathlib import Path
import tempfile
import unittest
from dashboard_data import load_records, summarize, dashboard, configured_links

HEADER=['timestamp_iso','video_url','video_title','concurrent_viewers','raw_counter_text']
A='https://www.youtube.com/watch?v=aaa'
B='https://www.youtube.com/watch?v=bbb'


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def write(self,name,rows):
        with (self.folder/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(HEADER);w.writerows(rows)
    def row(self,stamp,url,value,raw=None):
        return [stamp,url,'Canal '+url[-3:],value,f'{value} assistindo agora' if raw is None else raw]
    def test_deduplicate_active_and_snapshot(self):
        row=self.row('2026-09-25T10:00:00-03:00',A,100)
        self.write('dados_live.csv',[row]);self.write('__daily_snapshot.csv',[row])
        rows,stats,_=load_records(self.folder)
        self.assertEqual(len(rows),1);self.assertEqual(stats['duplicates'],1)
        self.assertEqual(len(rows[0]['sources']),2)
    def test_peaks_are_max_per_link_day_hour(self):
        self.write('dados_live.csv',[
            self.row('2026-09-25T10:00:00-03:00',A,100),self.row('2026-09-25T10:03:00-03:00',A,200),
            self.row('2026-09-25T11:00:00-03:00',A,150),self.row('2026-09-26T10:00:00-03:00',A,80),
            self.row('2026-09-25T10:00:00-03:00',B,300)])
        rows,_,_=load_records(self.folder);result=summarize(rows)
        self.assertEqual(result['metrics']['peak']['viewers'],300)
        self.assertEqual([(r['date'],r['url'],r['peak']) for r in result['daily']],
                         [('2026-09-25',A,200),('2026-09-25',B,300),('2026-09-26',A,80)])
        group=next(r for r in result['hourly'] if r['date']=='2026-09-25' and r['url']==A and r['hour']==10)
        self.assertEqual(group['peak'],200);self.assertEqual(group['at'],'2026-09-25T10:03:00-03:00')

    def test_link_peak_carries_its_own_date_and_hour(self):
        self.write('dados_live.csv',[
            self.row('2026-09-25T10:00:00-03:00',A,100),
            self.row('2026-09-26T18:00:00-03:00',A,900)])
        rows,_,_=load_records(self.folder); result=summarize(rows)
        peak=result['links'][0]
        self.assertEqual((peak['peak'],peak['date'],peak['hour']), (900,'2026-09-26',18))
    def test_zero_missing_and_conflicting_text(self):
        self.write('dados_live.csv',[self.row('2026-09-25T10:00:00',A,0),
                    self.row('2026-09-25T10:03:00',A,'','falha'),
                    self.row('2026-09-25T10:06:00',A,109,'1.094 assistindo agora')])
        rows,_,_=load_records(self.folder);result=summarize(rows)
        self.assertEqual(result['metrics']['valid'],1);self.assertEqual(result['metrics']['missing'],2)
        self.assertEqual(result['metrics']['peak']['viewers'],0)
    def test_filters_and_timezone_day_boundary(self):
        self.write('dados_live.csv',[self.row('2026-09-26T01:00:00+00:00',A,90),
                    self.row('2026-09-26T08:00:00-03:00',B,150)])
        rows,_,_=load_records(self.folder)
        result=summarize(rows,start='2026-09-25',end='2026-09-25',urls=[A],hour_start=22,hour_end=22)
        self.assertEqual(result['metrics']['total'],1)
        with self.assertRaises(ValueError):summarize(rows,start='2026-09-27',end='2026-09-25')
        self.assertEqual(summarize(rows,quality='missing')['metrics']['peak'],None)
    def test_conflicting_duplicates_are_not_arbitrarily_selected(self):
        self.write('dados_live.csv',[self.row('2026-09-25T10:00:00',A,100)])
        self.write('snapshot.csv',[self.row('2026-09-25T10:00:00',A,900)])
        rows,stats,_=load_records(self.folder)
        self.assertEqual(stats['conflicts'],1);self.assertIsNone(rows[0]['viewers'])
    def test_test_files_opt_in_and_configured_without_data(self):
        self.write('teste_monitor.csv',[self.row('2026-09-25T10:00:00',A,100)])
        (self.folder/'rodar_monitor.bat').write_text('python monitor.py --url "'+B+'"',encoding='utf-8')
        result=dashboard(self.folder,self.folder,{})
        self.assertEqual(result['metrics']['total'],0)
        self.assertEqual(result['catalog'][0]['url'],B)
        self.assertEqual(dashboard(self.folder,self.folder,{'tests':'1'})['metrics']['total'],1)
    def test_malformed_and_canonical_urls(self):
        self.write('dados_live.csv',[self.row('bad',A,1),self.row('2026-09-25T10:00:00','https://youtu.be/aaa',20)])
        rows,stats,_=load_records(self.folder)
        self.assertEqual(stats['malformed'],1);self.assertEqual(rows[0]['url'],A)

if __name__=='__main__':unittest.main()
