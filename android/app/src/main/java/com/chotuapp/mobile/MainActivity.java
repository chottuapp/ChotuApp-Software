package com.chotuapp.mobile;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.util.concurrent.*;
public class MainActivity extends Activity {
    static boolean suppressAutoFreshForTests=false;boolean resumed=false;String pendingCampaign="";
    final int INK=Color.rgb(24,43,34),MUTED=Color.rgb(105,119,111),GREEN=Color.rgb(23,107,81),BG=Color.rgb(245,247,243);
    LinearLayout screen,content,nav;String tab="Overview";String driveQuery="";JSONObject cloud=new JSONObject();boolean loading=false,sendingLogs=false;long fetchedAt=0,lastTelemetryAttempt=0;
    final ExecutorService io=Executors.newSingleThreadExecutor(),telemetry=Executors.newSingleThreadExecutor();final Handler handler=new Handler(Looper.getMainLooper());
    final Runnable poll=new Runnable(){public void run(){if(!isFinishing()){if(tab.equals("Overview"))render();if(!FetchService.active.get()&&!sendingLogs&&!Vault.read(MainActivity.this).isEmpty()&&System.currentTimeMillis()-lastTelemetryAttempt>=30000)syncLogs();if(fetchedAt>0&&System.currentTimeMillis()-fetchedAt>30000&&!loading)refresh();handler.postDelayed(this,4000);}}};
    int dp(float n){return (int)(getResources().getDisplayMetrics().density*n+.5f);}
    GradientDrawable bg(int color,int radius){GradientDrawable b=new GradientDrawable();b.setColor(color);b.setCornerRadius(dp(radius));return b;}
    LinearLayout column(){LinearLayout l=new LinearLayout(this);l.setOrientation(1);return l;}
    TextView text(String value,int size,int color,boolean bold){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);v.setTypeface(Typeface.create("sans-serif",bold?Typeface.BOLD:Typeface.NORMAL));v.setLineSpacing(dp(3),1);return v;}
    void gap(LinearLayout p,int h){Space s=new Space(this);p.addView(s,new LinearLayout.LayoutParams(1,dp(h)));}
    TextView label(LinearLayout p,String value,int size,int color,boolean bold){TextView v=text(value,size,color,bold);p.addView(v);return v;}
    LinearLayout card(LinearLayout parent){LinearLayout c=column();c.setPadding(dp(20),dp(20),dp(20),dp(20));c.setBackground(bg(Color.WHITE,22));parent.addView(c,new LinearLayout.LayoutParams(-1,-2));gap(parent,14);return c;}
    Button button(String title,boolean primary,Runnable click){Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextSize(14);b.setTypeface(null,Typeface.BOLD);b.setTextColor(primary?Color.WHITE:GREEN);b.setBackground(bg(primary?GREEN:Color.rgb(233,240,232),14));b.setMinHeight(dp(50));b.setPadding(dp(14),0,dp(14),0);b.setOnClickListener(v->click.run());return b;}
    @Override public void onCreate(Bundle state){super.onCreate(state);if(!Profile.authenticated(this)){startActivity(new Intent(this,LoginActivity.class));finish();return;}screen=column();screen.setBackgroundColor(BG);screen.setOnApplyWindowInsetsListener((v,insets)->{if(Build.VERSION.SDK_INT>=30){android.graphics.Insets i=insets.getInsets(WindowInsets.Type.systemBars());v.setPadding(i.left,i.top,i.right,i.bottom);}else{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());}return insets;});
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);content=column();content.setPadding(dp(22),dp(22),dp(22),dp(16));scroll.addView(content);screen.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));nav=new LinearLayout(this);nav.setPadding(dp(12),dp(8),dp(12),dp(12));screen.addView(nav);setContentView(screen);render();refresh();}
    @Override public void onResume(){super.onResume();resumed=true;if(Profile.authenticated(this)){HeartbeatJobs.ensureScheduled(this);handler.post(poll);if(!Vault.read(this).isEmpty())syncLogs();if(!pendingCampaign.isEmpty())applyFreshCampaign(pendingCampaign);else if(!suppressAutoFreshForTests&&!FetchService.active.get()&&getSharedPreferences("worker",0).getBoolean("resume_requested",false))startFetch();}}
    @Override public void onPause(){resumed=false;handler.removeCallbacks(poll);super.onPause();}
    void render(){content.removeAllViews();nav.removeAllViews();LinearLayout head=new LinearLayout(this);head.setGravity(Gravity.CENTER_VERTICAL);LinearLayout name=column();label(name,"CHOTUAPP STUDIO",12,GREEN,true).setLetterSpacing(.16f);label(name,"Your catalog, connected.",13,MUTED,false);head.addView(name,new LinearLayout.LayoutParams(0,-2,1));TextView icon=text("C",23,Color.WHITE,true);icon.setGravity(Gravity.CENTER);icon.setBackground(bg(GREEN,15));head.addView(icon,new LinearLayout.LayoutParams(dp(46),dp(46)));content.addView(head);gap(content,26);
        label(content,tab.equals("Overview")?"Good to see you, Anas.":tab,27,INK,true);gap(content,6);label(content,tab.equals("Overview")?"A clear view of every fetch and saved file.":tab.equals("Activity")?"Real events. Saved work. Clear next steps.":"One connection. Your files stay yours.",14,MUTED,false);gap(content,24);
        if(tab.equals("Overview"))overview();else if(tab.equals("Activity"))activity();else if(tab.equals("Drive"))driveFiles();else settings();
        for(String title:new String[]{"Overview","Activity","Drive","Settings"}){Button b=button(title,tab.equals(title),()->{tab=title;render();});LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(46),1);lp.setMargins(dp(3),0,dp(3),0);nav.addView(b,lp);}
    }
    JSONObject local(){try{return new JSONObject(read(new File(FetchService.dataDirectory(this),"local-status.json"),12000));}catch(Exception e){return new JSONObject();}}
    String workerMessage(){return getSharedPreferences("worker",0).getString("message","Ready when you are. Start Khaadi on this phone.");}
    String workerStatus(){String value=getSharedPreferences("worker",0).getString("status","ready");if(value.equals("running")&&!FetchService.active.get())return "stopped";return FetchService.active.get()?(FetchService.paused.get()?"pausing":"running"):value;}
    int currentAuditPassCount(JSONObject drive){if(drive==null)return 0;JSONObject files=drive.optJSONObject("uploaded");if(files==null)return 0;int count=0;String campaign=drive.optString("audit804_campaign","");java.util.Iterator<String> keys=files.keys();while(keys.hasNext()){JSONObject file=files.optJSONObject(keys.next());if(file==null)continue;JSONObject audit=file.optJSONObject("audit804");if(audit!=null&&audit.optString("status").equals("pass")&&file.optString("campaign_id").equals(campaign))count++;}return count;}
    void overview(){String status=workerStatus();LinearLayout hero=card(content);hero.setBackground(bg(INK,24));label(hero,"ON THIS PHONE",11,Color.rgb(190,214,198),true).setLetterSpacing(.12f);gap(hero,12);label(hero,"Khaadi",32,Color.WHITE,true);gap(hero,5);label(hero,status.equals("running")?"●  Fetching public product pages":status.equals("pausing")?"●  Saving and pausing…":status.equals("cloud_queued")?"✓  Queued for cloud review":status.equals("attention")?"!  Needs attention":"○  "+status.replace('_',' '),14,Color.rgb(218,239,135),true);gap(hero,14);label(hero,workerMessage(),13,Color.rgb(220,230,223),false);
        JSONObject local=local();String event=local.optString("last_event","");if(FetchService.active.get()&&!event.isEmpty()){gap(hero,12);label(hero,event.replace("Keep CMD open and PC awake; Ctrl+C stops local fetch.","Keep this phone online; Pause saves your progress."),12,Color.rgb(220,230,223),false);}
        gap(hero,12);label(hero,telemetryLine(),12,Color.rgb(218,239,135),false);gap(hero,18);Button start=button(FetchService.active.get()?"Pause safely":"Start / Resume",false,()->{if(FetchService.active.get())startService(new Intent(this,FetchService.class).setAction("pause"));else startFetch();handler.postDelayed(this::render,500);});hero.addView(start,new LinearLayout.LayoutParams(-1,dp(50)));
        JSONObject runners=cloud.optJSONObject("runners"),drive=cloud.optJSONObject("drive");boolean unknown=runners==null||runners.optBoolean("unavailable");LinearLayout row=new LinearLayout(this);
        metric(row,unknown?"—":String.valueOf(runners.optInt("active_runners")),"Cloud runners");metric(row,drive==null||drive.optBoolean("unavailable")?"—":String.valueOf(currentAuditPassCount(drive)),"804 Audit passed");content.addView(row);gap(content,18);
        JSONObject fresh=cloud.optJSONObject("fresh_release");if(fresh!=null){LinearLayout batch=card(content);label(batch,"FRESH FETCH · 804 AUDIT",11,GREEN,true);label(batch,"Complete → 804 → 804 Audit → Drive",15,INK,true);label(batch,"All 29 shop codes are registered. Uncertain categories or descriptions stay on hold. Saved Khaadi work resumes in this campaign.",12,MUTED,false);if(!pendingCampaign.isEmpty())label(batch,"Saving previous phone work before fresh start…",12,GREEN,true);}
        LinearLayout delivery=card(content);label(delivery,"SAVE FLOW",11,GREEN,true).setLetterSpacing(.1f);gap(delivery,12);label(delivery,"Complete → Rule 804 → 804 Audit → Drive",16,INK,true);gap(delivery,8);label(delivery,"ChotuApp 19-10-2026 11-36AM",13,MUTED,false);gap(delivery,7);label(delivery,"Audit-passed versions replace the matching shop code. Other stores stay.",12,MUTED,false);
        if(drive!=null&&!drive.optBoolean("unavailable")){gap(delivery,10);label(delivery,"Cloud sync: "+drive.optString("sync_status","unknown")+"\nLast scan: "+drive.optString("last_scan_utc","not reported"),12,MUTED,false);JSONObject originals=drive.optJSONObject("original_uploads");if(originals!=null&&originals.has("Khaadi")){String source=getSharedPreferences("worker",0).getString("source_sha256","");boolean matches=!source.isEmpty()&&source.equals(originals.optJSONObject("Khaadi").optString("source_sha256"));label(delivery,matches?"✓ This Khaadi workbook verified in Drive":"Previous Khaadi upload verified in Drive",13,GREEN,true);}if(drive.has("sync_error"))label(delivery,"Upload needs attention — open Activity.",12,Color.rgb(155,88,23),true);}
        label(content,loading?"Refreshing cloud reports…":fetchedAt==0?"Cloud reports not loaded":"Fetched "+Math.max(0,(System.currentTimeMillis()-fetchedAt)/60000)+" min ago · source reports may lag",11,MUTED,false);gap(content,10);content.addView(button("Refresh cloud status",false,this::refresh));
    }
    void metric(LinearLayout row,String value,String title){LinearLayout m=column();m.setPadding(dp(18),dp(18),dp(12),dp(18));m.setBackground(bg(Color.WHITE,20));label(m,value,29,INK,true);label(m,title,12,MUTED,false);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);lp.setMargins(0,0,dp(8),0);row.addView(m,lp);}
    void progressCards(){
        JSONArray stores=cloud.optJSONArray("store_progress");if(stores==null)return;
        for(int i=0;i<stores.length();i++){
            JSONObject store=stores.optJSONObject(i);if(store==null)continue;
            String status=store.optString("status","unknown");boolean stale=store.optBoolean("stale");
            boolean error=status.equals("failed")||status.equals("blocked")||status.equals("source_paused");
            int color=stale?MUTED:error?Color.rgb(178,45,45):GREEN;
            LinearLayout box=card(content);label(box,store.optString("store"),18,INK,true);
            label(box,store.optString("execution")+" · "+store.optString("runner_id"),12,MUTED,false);
            label(box,status.replace('_',' ')+(stale?" · stale report":""),13,color,true);
            if(store.has("completed_tasks")){
                label(box,store.optString("stage","Stage progress")+" · "+store.optString("unit"),12,MUTED,false);
                label(box,store.optInt("completed_tasks")+" / "+store.optInt("total_tasks")+" · "+store.optInt("remaining_tasks")+" remaining",14,INK,true);
                if(store.has("stage_percent")&&!store.isNull("stage_percent")){
                    ProgressBar bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);bar.setMax(1000);bar.setProgress((int)(store.optDouble("stage_percent")*10));box.addView(bar,new LinearLayout.LayoutParams(-1,dp(12)));
                    label(box,store.optString("stage_percent")+"% of this stage",12,color,true);
                }
                if(store.has("product_urls_found"))label(box,store.optInt("product_urls_found")+" product URLs discovered",12,MUTED,false);
            }
            label(box,"Overall completion and verified fetched-product count: not reported",11,MUTED,false);
            label(box,"Report: "+store.optString("observed_utc","unavailable"),11,MUTED,false);
        }
    }
    void activity(){progressCards();LinearLayout remote=card(content);label(remote,"LIVE REMOTE LOGS",11,GREEN,true);gap(remote,8);label(remote,telemetryLine(),13,INK,false);gap(remote,12);remote.addView(button(sendingLogs?"Sending…":"Send logs now",false,this::syncLogs));gap(remote,8);remote.addView(button("Refresh this activity",false,this::render));LinearLayout box=card(content);label(box,"PHONE WORKER · "+workerStatus().toUpperCase(),11,GREEN,true);gap(box,10);label(box,workerMessage(),14,INK,false);String logs=read(new File(FetchService.dataDirectory(this),"fetch-log.txt"),6500);if(logs.isEmpty())logs="No local events yet. Start Khaadi from Overview.";gap(box,14);TextView events=label(box,logs.replace("Keep CMD open and PC awake; Ctrl+C stops local fetch.","Keep this phone online; Pause saves your progress."),11,MUTED,false);events.setTypeface(Typeface.MONOSPACE);events.setTextIsSelectable(true);
        JSONObject runners=cloud.optJSONObject("runners");if(runners!=null){JSONArray runs=runners.optJSONArray("runs");if(runs!=null)for(int i=0;i<runs.length();i++){JSONObject run=runs.optJSONObject(i);if(run==null)continue;LinearLayout r=card(content);label(r,run.optString("lane",run.optString("displayTitle","Cloud run")),14,INK,true);label(r,run.optString("status")+" · "+run.optString("conclusion"),12,GREEN,true);label(r,run.optString("snapshot","Snapshot not published yet"),12,MUTED,false);}}
    }
    String pakistanTime(String value){
        if(value==null||value.isEmpty())return "Time not recorded";
        try{return java.time.OffsetDateTime.parse(value).atZoneSameInstant(java.time.ZoneId.of("Asia/Karachi")).format(java.time.format.DateTimeFormatter.ofPattern("dd MMM yyyy · h:mm a",java.util.Locale.ENGLISH))+" PKT";}catch(Exception e){return "Time unavailable";}
    }
    void driveFiles(){
        JSONObject drive=cloud.optJSONObject("drive");
        EditText search=new EditText(this);search.setSingleLine();search.setTextSize(16);search.setHint("Search store or file…");search.setContentDescription("Search Drive files");search.setInputType(InputType.TYPE_CLASS_TEXT);search.setPadding(dp(16),dp(12),dp(16),dp(12));search.setBackground(bg(Color.WHITE,14));search.setText(driveQuery);content.addView(search,new LinearLayout.LayoutParams(-1,dp(54)));gap(content,14);
        LinearLayout heading=card(content);label(heading,"VERIFIED DELIVERY",11,GREEN,true);gap(heading,8);label(heading,"ChotuApp 19-10-2026 11-36AM",16,INK,true);
        if(drive==null||drive.optBoolean("unavailable")){label(heading,"Drive report unavailable",14,MUTED,false);return;}
        JSONObject latest=latestDriveFiles(drive);java.time.LocalDate today=java.time.LocalDate.now(java.time.ZoneId.of("Asia/Karachi"));int uploadedToday=0;java.util.Iterator<String> todayKeys=latest.keys();while(todayKeys.hasNext()){JSONObject f=latest.optJSONObject(todayKeys.next());try{if(java.time.OffsetDateTime.parse(f.optString("verified_utc")).atZoneSameInstant(java.time.ZoneId.of("Asia/Karachi")).toLocalDate().equals(today))uploadedToday++;}catch(Exception ignored){}}
        label(heading,today.format(java.time.format.DateTimeFormatter.ofPattern("dd MMM yyyy",java.util.Locale.ENGLISH))+" · Pakistan",15,INK,true);label(heading,"Today: "+uploadedToday+" stores uploaded",20,GREEN,true);label(heading,"Latest verified version per store · "+latest.length()+" stores saved",12,MUTED,false);
        String folderUrl=drive.optString("folder_url","");
        if(folderUrl.startsWith("https://drive.google.com/drive/folders/")){gap(heading,12);heading.addView(button("Open Google Drive folder",true,()->open(folderUrl)));}
        else heading.addView(button("Find folder in Drive",false,()->open("https://drive.google.com/drive/u/0/search?q=ChotuApp%2019-10-2026%2011-36AM")));
        gap(heading,8);label(heading,"Times shown in Pakistan time · upload checksum verification",12,MUTED,false);JSONObject results804=drive.optJSONObject("audit804_results");int held804=0;if(results804!=null){java.util.Iterator<String> keys804=results804.keys();while(keys804.hasNext()){JSONObject item804=results804.optJSONObject(keys804.next());if(item804!=null&&item804.optString("status").equals("hold"))held804++;}}label(heading,"804 Audit: "+currentAuditPassCount(drive)+" passed · "+held804+" on hold",13,held804>0?Color.rgb(178,45,45):GREEN,true);
        if(drive.has("catalog_checked_utc"))label(heading,"Links checked: "+pakistanTime(drive.optString("catalog_checked_utc")),11,MUTED,false);
        LinearLayout results=column();content.addView(results);populateDrive(results,drive,driveQuery);
        search.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence t,int start,int count,int after){}public void onTextChanged(CharSequence t,int start,int before,int count){driveQuery=t.toString();populateDrive(results,drive,driveQuery);}public void afterTextChanged(android.text.Editable t){}});
    }
    static JSONObject latestDriveFiles(JSONObject drive){
        JSONObject result=new JSONObject();for(String collection:new String[]{"original_uploads","uploaded"}){JSONObject source=drive.optJSONObject(collection);if(source==null)continue;java.util.Iterator<String> keys=source.keys();while(keys.hasNext()){String name=keys.next();JSONObject value=source.optJSONObject(name);if(value==null)continue;JSONObject prior=result.optJSONObject(name);boolean newer=prior==null;try{newer=prior==null||java.time.OffsetDateTime.parse(value.optString("verified_utc")).toInstant().compareTo(java.time.OffsetDateTime.parse(prior.optString("verified_utc")).toInstant())>=0;}catch(Exception ignored){newer=prior==null||(!value.optString("verified_utc").isEmpty()&&prior.optString("verified_utc").isEmpty());}if(newer)try{result.put(name,value);}catch(JSONException ignored){}}}return result;
    }
    void populateDrive(LinearLayout results,JSONObject drive,String query){
        results.removeAllViews();JSONObject files=latestDriveFiles(drive);java.util.TreeSet<String> names=new java.util.TreeSet<>();files.keys().forEachRemaining(names::add);
        int shown=0;String filter=query.trim().toLowerCase(java.util.Locale.ROOT);
        for(String name:names){
            if(!(name+".xlsx").toLowerCase(java.util.Locale.ROOT).contains(filter))continue;
            JSONObject file=files.optJSONObject(name);if(file==null)continue;
            shown++;LinearLayout box=card(results);label(box,"✓ "+name,18,GREEN,true);gap(box,4);label(box,file.optString("file_name",name+".xlsx"),12,MUTED,false);label(box,file.optString("folder","Folder not recorded"),13,INK,false);gap(box,8);label(box,"Upload verified: "+pakistanTime(file.optString("verified_utc","")),13,INK,false);JSONObject audit=file.optJSONObject("audit804");JSONObject audits=drive.optJSONObject("audit804_results");JSONObject result=audits==null?null:audits.optJSONObject(name);boolean auditPass=audit!=null&&audit.optString("status").equals("pass")&&file.optString("campaign_id").equals(drive.optString("audit804_campaign"));boolean auditHold=result!=null&&result.optString("status").equals("hold");label(box,auditPass?"✓ 804 Audit passed":auditHold?"Previous version retained · new 804 Audit on hold":"Previous version · new 804 Audit pending",12,auditPass?GREEN:auditHold?Color.rgb(178,45,45):MUTED,true);if(auditHold)label(box,result.isNull("shop_code")?"Shop code pending or category/description review required":"Category / description attention required",12,MUTED,false);
            String fileUrl=file.optString("file_url","");String folderUrl=file.optString("folder_url",drive.optString("folder_url",""));gap(box,12);
            if(fileUrl.startsWith("https://drive.google.com/file/d/"))box.addView(button("Open Excel file",true,()->open(fileUrl)));
            else box.addView(button("Find file in Drive",false,()->open("https://drive.google.com/drive/u/0/search?q="+Uri.encode(name+".xlsx"))));
            if(folderUrl.startsWith("https://drive.google.com/drive/folders/")){gap(box,8);box.addView(button("Open folder",false,()->open(folderUrl)));}
        }
        label(results,shown+" file"+(shown==1?"":"s")+" shown"+(shown==0?" · No matching store or file":""),12,MUTED,false);
    }
    int installedVersion(){try{return getPackageManager().getPackageInfo(getPackageName(),0).versionCode;}catch(Exception e){return Integer.MAX_VALUE;}}
    void settings(){
        LinearLayout updates=card(content);label(updates,"APP UPDATES",11,GREEN,true);gap(updates,8);label(updates,"Saved work stays with this app",18,INK,true);label(updates,"Checks for a new version when cloud status refreshes. Android asks you to confirm installation. No uninstall needed for future Studio updates.",13,MUTED,false);
        JSONObject update=cloud.optJSONObject("app_update");
        if(update!=null&&!update.optBoolean("unavailable")&&update.optString("package").equals("com.chotuapp.studio")&&update.optInt("version_code")>installedVersion()){gap(updates,12);updates.addView(button("Update to "+update.optString("version"),true,()->open("https://raw.githubusercontent.com/chottuapp/ChotuApp-Software/android-builds/ChotuApp-Studio.apk")));}else{gap(updates,8);label(updates,update==null||update.optBoolean("unavailable")?"Update check unavailable":"You have the current Studio version",12,MUTED,false);}
        updates.addView(button("Check for updates",false,this::refresh));
        LinearLayout conn=card(content);boolean connected=!Vault.read(this).isEmpty();label(conn,"GITHUB CONNECTION",11,GREEN,true);gap(conn,10);label(conn,connected?"GitHub credentials saved":"Connect once for automatic delivery",18,INK,true);gap(conn,8);label(conn,"Your access token is encrypted with Android Keystore. It is never included in reports or backups.",13,MUTED,false);gap(conn,16);label(conn,telemetryLine(),12,MUTED,false);gap(conn,8);conn.addView(button(connected?"Change connection":"Connect GitHub",true,this::connect));if(connected){gap(conn,8);conn.addView(button("Disconnect",false,()->{Vault.clear(this);render();}));}
        LinearLayout battery=card(content);label(battery,"KEEP FETCHING",11,GREEN,true);gap(battery,10);label(battery,"Allow background activity",18,INK,true);gap(battery,8);label(battery,"Keep your phone online. Set battery use to Unrestricted in Android app settings. Android may stop long background jobs; Resume keeps saved responses. The PC can stay off.",13,MUTED,false);gap(battery,12);battery.addView(button("Open app settings",false,()->startActivity(new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())))));
        content.addView(button("Lock app",false,()->{Profile.lock(this);startActivity(new Intent(this,LoginActivity.class));finish();}));LinearLayout about=card(content);label(about,"BUILT FOR YOUR WORKFLOW",11,GREEN,true);gap(about,10);label(about,"ChotuApp Studio · 1.4",17,INK,true);gap(about,8);label(about,"This phone runs Khaadi. Other stores run on GitHub. Unknown source changes need a tested app/adapter repair. Catalog coverage and ambiguous labels remain explicitly unverified.",13,MUTED,false);gap(about,12);about.addView(button("Open Google Drive",false,()->open("https://drive.google.com/drive/u/0/search?q=ChotuApp%2019-10-2026%2011-36AM")));
    }
    void connect(){LinearLayout form=column();form.setPadding(dp(24),dp(8),dp(24),0);label(form,"Create a fine-grained GitHub token for chottuapp/ChotuApp-Software with repository Contents: Read and write. Paste it here only.",13,MUTED,false);gap(form,10);Button help=button("Open GitHub token settings",false,()->open("https://github.com/settings/personal-access-tokens/new?name=ChotuApp%20Mobile&target_name=chottuapp&expires_in=30&contents=write"));form.addView(help);gap(form,12);EditText input=new EditText(this);input.setHint("GitHub access token");input.setSingleLine(true);input.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);form.addView(input);AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Connect GitHub").setView(form).setNegativeButton("Cancel",null).setPositiveButton("Connect",null).create();dialog.setOnShowListener(v->dialog.getButton(-1).setOnClickListener(w->{String token=input.getText().toString().trim();if(token.isEmpty())return;dialog.getButton(-1).setEnabled(false);telemetry.execute(()->{try{JSONObject checked=new JSONObject(FetchService.python(this).getModule("mobile_backend").callAttr("connect_github",FetchService.dataDirectory(this).getPath(),token,FetchService.active.get(),FetchService.paused.get()).toString());if(!checked.optString("status").equals("connected")){String message=checked.optString("message","GitHub heartbeat write failed.");runOnUiThread(()->{dialog.getButton(-1).setEnabled(true);input.setError(message);});return;}Vault.save(this,token);runOnUiThread(()->{input.setText("");dialog.dismiss();render();syncLogs();});}catch(Throwable e){runOnUiThread(()->{dialog.getButton(-1).setEnabled(true);input.setError("Connection failed. Check repository access and token permissions.");});}});}));dialog.show();}
    String telemetryLine(){
        if(Vault.read(this).isEmpty())return "Remote logs: connect GitHub in Settings.";String nativeError=getSharedPreferences("worker",0).getString("telemetry_native_error","");if(!nativeError.isEmpty())return nativeError;
        try{JSONObject report=new JSONObject(read(new File(FetchService.dataDirectory(this),"telemetry-status.json"),5000));return "Remote logs: "+report.optString("status","waiting").replace('_',' ')+"\n"+report.optString("message","")+(report.has("last_success_utc")?"\nLast verified send: "+report.optString("last_success_utc"):"");}catch(Exception e){return "Remote logs: waiting for first sync.";}
    }
    void syncLogs(){
        if(sendingLogs)return;if(Vault.read(this).isEmpty()){connect();return;}sendingLogs=true;lastTelemetryAttempt=System.currentTimeMillis();render();
        telemetry.execute(()->{try{FetchService.python(this).getModule("mobile_backend").callAttr("sync_logs",FetchService.dataDirectory(this).getPath(),Vault.read(this),FetchService.active.get(),FetchService.paused.get());getSharedPreferences("worker",0).edit().remove("telemetry_native_error").apply();}catch(Throwable e){getSharedPreferences("worker",0).edit().putString("telemetry_native_error","Phone log sync failed ("+e.getClass().getSimpleName()+"). Retry Send logs now.").apply();}runOnUiThread(()->{sendingLogs=false;render();});});
    }
    void applyFreshCampaign(String campaign){
        if(suppressAutoFreshForTests||!campaign.matches("fresh804-[0-9]{8}-[a-f0-9]{8}")||getSharedPreferences("worker",0).getString("fresh_campaign_seen","").equals(campaign))return;
        pendingCampaign=campaign;if(!resumed||isFinishing())return;
        if(FetchService.active.get()){
            if(!FetchService.paused.get())startService(new Intent(this,FetchService.class).setAction("pause"));
            handler.postDelayed(()->applyFreshCampaign(campaign),2000);return;
        }
        try{startForegroundService(new Intent(this,FetchService.class).putExtra("fresh_campaign_id",campaign));pendingCampaign="";handler.postDelayed(this::render,800);}catch(Exception e){Toast.makeText(this,"Fresh start waiting. Keep this app open and retry Refresh.",Toast.LENGTH_LONG).show();}
    }
    void startFetch(){if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},804);startForegroundService(new Intent(this,FetchService.class));}
    void refresh(){if(loading)return;loading=true;io.execute(()->{try{String result=FetchService.python(this).getModule("mobile_backend").callAttr("dashboard",Vault.read(this)).toString();JSONObject data=new JSONObject(result);runOnUiThread(()->{cloud=data;fetchedAt=System.currentTimeMillis();loading=false;render();JSONObject fresh=data.optJSONObject("fresh_release");if(fresh!=null&&fresh.optBoolean("khaadi_fresh_enabled"))applyFreshCampaign(fresh.optString("campaign_id",""));});}catch(Throwable e){runOnUiThread(()->{loading=false;Toast.makeText(this,"Cloud status unavailable. Phone fetch is unchanged.",Toast.LENGTH_LONG).show();render();});}});}
    void open(String url){startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url)));}
    static String read(File file,int limit){try(RandomAccessFile in=new RandomAccessFile(file,"r")){long from=Math.max(0,in.length()-limit);in.seek(from);byte[] b=new byte[(int)(in.length()-from)];in.readFully(b);String s=new String(b,"UTF-8");return from>0&&s.contains("\n")?s.substring(s.indexOf('\n')+1):s;}catch(Exception e){return "";}}
}
