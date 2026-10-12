import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('chotu', ROOT / 'main.py')
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

class GuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = patch.object(main, 'CONFIG', Path(self.tmp.name)/'sites.json')
        self.config.start()
        self.root = main.tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.app = main.App(self.root)
        self.app.sites = [{'name':f'Store {i}', 'url':f'https://fixture{i}.example'} for i in range(40)]
        self.app.redraw()
        self.root.update()

    def tearDown(self):
        main._chotu_pause_gate.set()
        # Cancel scheduled callbacks before destroying interpreter widgets.
        for callback in self.root.tk.splitlist(self.root.tk.call('after', 'info')):
            self.root.tk.call('after', 'cancel', callback)
        self.root.destroy()
        self.config.stop()
        self.tmp.cleanup()
        self.assertFalse(self.errors)

    def wheel(self, widget, sequence='<Button-5>', **kwargs):
        widget.event_generate(sequence, **kwargs)
        self.root.update()

    def test_store_scroll_independent_after_redraw(self):
        a=self.app
        page=a._wheel_workspace._parent_canvas
        page.yview_moveto(.25); self.root.update()
        before=page.yview()
        store=a.store_list._parent_canvas
        before_store=store.yview()
        child=a.store_list.winfo_children()[0].winfo_children()[0]
        self.wheel(child)
        self.assertGreater(store.yview()[0],before_store[0])
        self.assertEqual(page.yview(),before)
        store.yview_moveto(1);self.root.update()
        self.wheel(child)
        self.assertEqual(page.yview(),before)
        a.redraw();self.root.update()
        child=a.store_list.winfo_children()[0].winfo_children()[0]
        self.assertEqual(child.bindtags()[0],a._wheel_tag)

    def test_logs_scroll_without_scrolling_page(self):
        a=self.app;page=a._wheel_workspace._parent_canvas
        page.yview_moveto(1);self.root.update()
        a.logbox.insert('end','line\n'*120);self.root.update()
        a.logbox.yview_moveto(0);before=page.yview()
        self.wheel(a.logbox)
        self.assertGreater(a.logbox.yview()[0],0)
        self.assertEqual(page.yview(),before)

    def test_windows_wheel_event_and_page_scroll(self):
        page=self.app._wheel_workspace._parent_canvas
        page.yview_moveto(0)
        self.wheel(page,'<MouseWheel>',delta=-120)
        self.assertGreater(page.yview()[0],0)

    def test_selection_and_idle_pause(self):
        a=self.app
        self.assertEqual(a.refresh_selected.cget('state'),'normal')
        a.store_checks[a.sites[5]['url']].set(True)
        a._selection_changed()
        self.assertEqual(a._selected_indices(),[5])
        self.assertEqual(a.refresh_selected.cget('state'),'normal')
        a.toggle_pause();self.assertTrue(main._chotu_pause_gate.is_set())
        a.running=True;a.toggle_pause();self.assertFalse(main._chotu_pause_gate.is_set())
        completed=threading.Event()
        t=threading.Thread(target=lambda:(main._chotu_wait(),completed.set()),daemon=True);t.start()
        self.assertFalse(completed.wait(.05))
        a.toggle_pause();self.assertTrue(completed.wait(1));t.join(1)

    def pump_until_done(self):
        deadline=time.monotonic()+3
        while self.app.running and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.assertFalse(self.app.running)

    def test_worker_failure_restores_controls(self):
        a=self.app
        with patch.object(a,'_run_checked',side_effect=RuntimeError('fixture failure')):
            a._launch_jobs([a.sites[0]],'fixture.xlsx')
            self.pump_until_done()
        self.assertTrue(a.job_failed)
        self.assertEqual(a.refresh.cget('state'),'normal')
        self.assertEqual(a.pause_button.cget('state'),'disabled')
        self.assertTrue(main._chotu_pause_gate.is_set())
        self.assertIn('ERROR',a.live_status.cget('text'))

    def test_review_is_distinct_from_completed(self):
        a=self.app
        def job(*args):
            a.events.put('SAVED REVIEW EXCEL: fixture.xlsx')
            a.events.put(('__JOB_RESULT__',True,'Fixture'))
        with patch.object(a,'_run_checked',side_effect=job):
            a._launch_jobs([a.sites[0]],'fixture.xlsx');self.pump_until_done()
        self.assertIn('REVIEW REQUIRED',a.live_status.cget('text'))
        self.assertEqual(a.progress_value.get(),100)

    def test_focus_root_routes_to_hovered_store(self):
        a = self.app
        page = a._wheel_workspace._parent_canvas
        page.yview_moveto(.35); self.root.update()
        canvas = a.store_list._parent_canvas
        canvas.yview_moveto(0); self.root.update()
        before_page = page.yview()
        # Windows wheel messages can name the focused root, not the hovered pane.
        x = canvas.winfo_rootx() + 20
        y = canvas.winfo_rooty() + 20
        from types import SimpleNamespace
        event = SimpleNamespace(widget=self.root, x_root=x, y_root=y, delta=-120, num=None, state=0)
        self.assertEqual(a._route_wheel(event), 'break')
        self.assertGreater(canvas.yview()[0], 0)
        self.assertEqual(page.yview(), before_page)

    def test_fetch_button_visible_at_small_window(self):
        self.root.geometry('900x640'); self.root.update()
        button = self.app.refresh_selected
        self.assertTrue(button.winfo_ismapped())
        self.assertLess(button.winfo_rooty() + button.winfo_height(),
                        self.root.winfo_rooty() + self.root.winfo_height())

    def test_selected_launch_runs_only_ticked_store(self):
        a=self.app
        a.store_checks[a.sites[7]['url']].set(True);a._selection_changed()
        template=Path(self.tmp.name)/'template.xlsx';template.touch();a.template.set(str(template))
        calls=[]
        def job(site,template):
            calls.append(site['url']);a.events.put(('__JOB_RESULT__',True,site['name']))
        with patch.object(a,'_run_checked',side_effect=job):
            a.start_selected();self.pump_until_done()
        self.assertEqual(calls,[a.sites[7]['url']])

class ExportTests(unittest.TestCase):
    def export(self,fractional):
        price='999.88' if fractional else '999'
        product={'id':1,'title':'Fixture Cotton Shirt','handle':'fixture-shirt','vendor':'Fixture','product_type':'Shirts','body_html':'<p>Cotton shirt for daily wear.</p>','images':[{'id':1,'src':'https://example.com/shirt.jpg','position':1}],'options':[{'name':'Size'}],'variants':[{'id':11,'price':'699.44' if fractional else '699','available':False,'option1':'Medium'},{'id':12,'price':price,'available':True,'option1':'Big'}]}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith('/products.json'): data={'products':[product]}
                elif self.path.startswith('/products/fixture-shirt.js'):
                    data={'variants':[dict(v,price=int(main.Decimal(v['price'])*100),compare_at_price=None) for v in product['variants']]}
                elif self.path.startswith('/products/fixture-shirt'):
                    self.send_response(200);self.end_headers();self.wfile.write(f'<span class="price-item">PKR {price}</span>'.encode());return
                else:data={'collections':[]}
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);template=folder/'template.xlsx'
                wb=Workbook();wb.remove(wb.active)
                for name,headers in json.loads((ROOT/'tests/schema.json').read_text()).items():wb.create_sheet(name).append(headers)
                wb.save(template);wb.close()
                out=folder/'exports';out.mkdir()
                final=out/'Fixture - FINAL.xlsx'
                final.write_bytes(template.read_bytes());previous_final=final.read_bytes()
                logs=[]
                with patch.object(main,'OUT',out),patch.object(main,'__file__',str(folder/'main.py')):
                    main.run_site(f'http://127.0.0.1:{server.server_port}','Fixture',str(template),logs.append)
                self.assertEqual(final.read_bytes(),previous_final)
                wb=load_workbook(out/'Fixture.xlsx')
                def records(name):
                    rows=list(wb[name].values);return [dict(zip(rows[0],r)) for r in rows[1:]]
                self.assertEqual(len(records('Products')),1)
                variants={str(v['source_variant_id']):v for v in records('Variant Combinations')}
                self.assertEqual(len(variants),2)
                self.assertEqual(variants['11']['available (yes/no)'],'no')
                self.assertEqual(variants['12']['available (yes/no)'],'yes')
                self.assertEqual(variants['11']['base_price (PKR)'],699)
                self.assertEqual(variants['12']['base_price (PKR)'],999)
                wb.close()
                if fractional:
                    self.assertTrue(any('REVIEW REQUIRED:' in line for line in logs))
                    audit=(folder/'audit_reports/Fixture/Fixture - PRICE AUDIT.csv').read_text(encoding='utf-8-sig')
                    self.assertIn('API_PRICES_MATCH',audit)
        finally:
            server.shutdown();server.server_close();thread.join()
    def test_integer_prices_and_unavailable_variants(self):self.export(False)
    def test_fractional_prices_truncate_and_preserve_final(self):self.export(True)

if __name__=='__main__':unittest.main()
