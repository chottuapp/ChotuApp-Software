package com.chotuapp.mobile;
import android.app.*;
import android.content.*;
import android.os.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.*;
import java.util.concurrent.*;
public class FetchService extends Service {
    static final AtomicBoolean active=new AtomicBoolean(false),paused=new AtomicBoolean(false);
    private PowerManager.WakeLock wake;
    private ScheduledExecutorService reporter;
    public static boolean hasNativeReporter(){return true;}
    private void startReporting(){
        HeartbeatJobs.ensureScheduled(this);reporter=Executors.newSingleThreadScheduledExecutor();
        reporter.scheduleWithFixedDelay(()->HeartbeatJobs.send(getApplicationContext()),0,30,TimeUnit.SECONDS);
    }
    private void finishReporting(){
        if(reporter!=null){reporter.execute(()->HeartbeatJobs.send(getApplicationContext()));reporter.shutdown();}
    }
    private static Context appContext;
    @Override public void onCreate(){super.onCreate();appContext=getApplicationContext();appContextService=this;}
    public static String githubToken(){return appContext==null?"":Vault.read(appContext);}
    public static void networkWaiting(boolean waiting){if(appContext==null)return;String message=waiting?"Internet / source temporarily unavailable. Waiting; saved work will resume automatically.":"Connected. Fetching saved work…";appContext.getSharedPreferences("worker",0).edit().putString("status",waiting?"waiting_network":"running").putString("message",message).apply();NotificationManager manager=appContext.getSystemService(NotificationManager.class);if(active.get()&&appContextService!=null)manager.notify(804,appContextService.notice(message));}
    private static FetchService appContextService;
    public static boolean isActive(){return active.get();}
    public static boolean isPaused(){return paused.get();}
    static File dataDirectory(Context context){String name=context.getSharedPreferences("worker",0).getString("data_dir","khaadi");if(!name.equals("khaadi")&&!name.matches("khaadi-sessions/fresh804-[0-9]{8}-[a-f0-9]{8}"))name="khaadi";return new File(context.getFilesDir(),name);}
    static File prepareFreshDirectory(Context context,String campaign)throws Exception{
        if(!campaign.matches("fresh804-[0-9]{8}-[a-f0-9]{8}"))throw new IOException("Invalid fresh campaign");
        String relative="khaadi-sessions/"+campaign;File directory=new File(context.getFilesDir(),relative);if(!directory.exists()&&!directory.mkdirs())throw new IOException("Cannot create fresh session");
        File meta=new File(directory,"session-meta.json");if(meta.exists()){JSONObject prior=new JSONObject(MainActivity.read(meta,4000));if(!prior.optString("fresh_campaign_id").equals(campaign))throw new IOException("Session identity mismatch");}
        else try(FileOutputStream stream=new FileOutputStream(meta)){stream.write(new JSONObject().put("fresh_campaign_id",campaign).put("fresh_from_zero",true).toString().getBytes("UTF-8"));}
        context.getSharedPreferences("worker",0).edit().putString("data_dir",relative).putString("fresh_campaign_seen",campaign).commit();return directory;
    }
    static synchronized Python python(Context c){if(!Python.isStarted())Python.start(new AndroidPlatform(c.getApplicationContext()));return Python.getInstance();}
    static void extract(Context c) throws Exception {
        File target=new File(c.getFilesDir(),"engine");target.mkdirs();
        try(ZipInputStream in=new ZipInputStream(c.getAssets().open("engine.zip"))) {
            ZipEntry entry;byte[] buf=new byte[16384];while((entry=in.getNextEntry())!=null){File out=new File(target,entry.getName());if(!out.getCanonicalPath().startsWith(target.getCanonicalPath()+File.separator))throw new IOException("Invalid bundle path");if(entry.isDirectory()){out.mkdirs();continue;}out.getParentFile().mkdirs();try(FileOutputStream stream=new FileOutputStream(out)){int n;while((n=in.read(buf))!=-1)stream.write(buf,0,n);}}
        }
    }
    private Notification notice(String text){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,FetchService.class).setAction("pause"),PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this,"fetch").setSmallIcon(com.chotuapp.mobile.R.drawable.app_icon).setContentTitle("ChotuApp · Khaadi").setContentText(text).setContentIntent(open).setOngoing(active.get()).addAction(new Notification.Action.Builder(null,"Pause",stop).build()).build();
    }
    public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&"pause".equals(intent.getAction())){getSharedPreferences("worker",0).edit().putBoolean("resume_requested",false).commit();paused.set(true);getSharedPreferences("worker",0).edit().putString("message","Pausing after the current request. Saved responses stay on this phone.").apply();if(!active.get())stopSelf();return START_NOT_STICKY;}
        if(intent==null&&!getSharedPreferences("worker",0).getBoolean("resume_requested",false)){stopSelf();return START_NOT_STICKY;}
        if(!active.compareAndSet(false,true))return START_STICKY;
        getSharedPreferences("worker",0).edit().putBoolean("resume_requested",true).commit();
        paused.set(false);NotificationManager manager=getSystemService(NotificationManager.class);manager.createNotificationChannel(new NotificationChannel("fetch","Catalog fetching",NotificationManager.IMPORTANCE_LOW));
        startForeground(804,notice("Fetching public pages. Saved progress is retained."));
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ChotuApp:Fetch");wake.acquire();
        getSharedPreferences("worker",0).edit().putString("status","running").putString("message","Starting saved work…").apply();
        startReporting();
        final String freshCampaign=intent==null?"":intent.getStringExtra("fresh_campaign_id");
        new Thread(()->{
            try {
                extract(this);File data=freshCampaign!=null&&!freshCampaign.isEmpty()?prepareFreshDirectory(this,freshCampaign):dataDirectory(this);data.mkdirs();
                String result=python(this).getModule("mobile_backend").callAttr("run",new File(getFilesDir(),"engine").getPath(),data.getPath(),Vault.read(this)).toString();
                JSONObject parsed=new JSONObject(result);getSharedPreferences("worker",0).edit().putString("source_sha256",parsed.optString("source_sha256","")).putString("status",parsed.getString("status")).putString("message",parsed.getString("message")).apply();
            } catch(Throwable e){getSharedPreferences("worker",0).edit().putString("status",paused.get()?"paused":"attention").putString("message",paused.get()?"Paused. Saved work retained.":"Worker needs attention. "+safe(e.getMessage())).apply();}
            finally{getSharedPreferences("worker",0).edit().putBoolean("resume_requested",false).commit();active.set(false);finishReporting();if(wake!=null&&wake.isHeld())wake.release();manager.notify(804,notice("Fetch stopped. Open ChotuApp for status."));stopForeground(STOP_FOREGROUND_DETACH);stopSelf();}
        },"khaadi-worker").start();return START_STICKY;
    }
    private String safe(String s){if(s==null)return "Open Activity for details.";String token=Vault.read(this);if(!token.isEmpty())s=s.replace(token,"[redacted]");return s.substring(0,Math.min(600,s.length()));}
    @Override public void onTimeout(int startId,int fgsType){paused.set(true);getSharedPreferences("worker",0).edit().putBoolean("resume_requested",false).putString("status","paused").putString("message","Android background time limit reached. Open the app and resume saved work.").apply();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    @Override public void onTaskRemoved(Intent intent){super.onTaskRemoved(intent);}
    @Override public void onDestroy(){paused.set(true);if(wake!=null&&wake.isHeld())wake.release();super.onDestroy();}
    @Override public IBinder onBind(Intent i){return null;}
}
