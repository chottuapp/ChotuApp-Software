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
public class FetchService extends Service {
    static final AtomicBoolean active=new AtomicBoolean(false),paused=new AtomicBoolean(false);
    private PowerManager.WakeLock wake;
    public static boolean isPaused(){return paused.get();}
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
        if(intent!=null&&"pause".equals(intent.getAction())){paused.set(true);getSharedPreferences("worker",0).edit().putString("message","Pausing after the current request. Saved responses stay on this phone.").apply();if(!active.get())stopSelf();return START_NOT_STICKY;}
        if(!active.compareAndSet(false,true))return START_NOT_STICKY;
        paused.set(false);NotificationManager manager=getSystemService(NotificationManager.class);manager.createNotificationChannel(new NotificationChannel("fetch","Catalog fetching",NotificationManager.IMPORTANCE_LOW));
        startForeground(804,notice("Fetching public pages. Saved progress is retained."));
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"ChotuApp:Fetch");wake.acquire(6*60*60*1000L);
        getSharedPreferences("worker",0).edit().putString("status","running").putString("message","Starting saved work…").apply();
        new Thread(()->{
            try {
                extract(this);File data=new File(getFilesDir(),"khaadi");data.mkdirs();
                String result=python(this).getModule("mobile_backend").callAttr("run",new File(getFilesDir(),"engine").getPath(),data.getPath(),Vault.read(this)).toString();
                JSONObject parsed=new JSONObject(result);getSharedPreferences("worker",0).edit().putString("status",parsed.getString("status")).putString("message",parsed.getString("message")).apply();
            } catch(Throwable e){getSharedPreferences("worker",0).edit().putString("status",paused.get()?"paused":"attention").putString("message",paused.get()?"Paused. Saved work retained.":"Worker needs attention. "+safe(e.getMessage())).apply();}
            finally{active.set(false);if(wake!=null&&wake.isHeld())wake.release();manager.notify(804,notice("Fetch stopped. Open ChotuApp for status."));stopForeground(STOP_FOREGROUND_DETACH);stopSelf();}
        },"khaadi-worker").start();return START_NOT_STICKY;
    }
    private String safe(String s){if(s==null)return "Open Activity for details.";String token=Vault.read(this);if(!token.isEmpty())s=s.replace(token,"[redacted]");return s.substring(0,Math.min(600,s.length()));}
    @Override public void onTimeout(int startId,int fgsType){paused.set(true);getSharedPreferences("worker",0).edit().putString("status","paused").putString("message","Android background time limit reached. Open the app and resume saved work.").apply();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    @Override public void onDestroy(){paused.set(true);super.onDestroy();}
    @Override public IBinder onBind(Intent i){return null;}
}
