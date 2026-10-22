package com.chotuapp.mobile;
import android.app.job.*;
import android.content.*;
import android.os.PersistableBundle;
import org.json.JSONObject;
/** Durable fallback after the foreground worker exits; credentials stay in Android Keystore. */
public class HeartbeatJobs extends JobService {
    static final int PERIODIC_ID=805;
    static void ensureScheduled(Context context){
        JobScheduler scheduler=context.getSystemService(JobScheduler.class);
        if(scheduler.getPendingJob(PERIODIC_ID)==null){
            JobInfo info=new JobInfo.Builder(PERIODIC_ID,new ComponentName(context,HeartbeatJobs.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPersisted(true)
                .setPeriodic(15*60*1000L).setBackoffCriteria(30000,JobInfo.BACKOFF_POLICY_EXPONENTIAL).build();
            scheduler.schedule(info);
        }
    }
    static boolean send(Context context){
        try{
            String result=FetchService.python(context).getModule("mobile_backend").callAttr("sync_logs",
                FetchService.dataDirectory(context).getPath(),Vault.read(context),FetchService.active.get(),FetchService.paused.get()).toString();
            JSONObject report=new JSONObject(result);
            context.getSharedPreferences("worker",0).edit().remove("telemetry_native_error").apply();
            return report.optString("status").equals("retry_pending");
        }catch(Throwable error){
            context.getSharedPreferences("worker",0).edit().putString("telemetry_native_error","Automatic phone reporting failed ("+error.getClass().getSimpleName()+"); background retry scheduled.").apply();return true;
        }
    }
    @Override public boolean onStartJob(JobParameters params){
        new Thread(()->{boolean retry=send(getApplicationContext());jobFinished(params,retry);},"phone-heartbeat-job").start();return true;
    }
    @Override public boolean onStopJob(JobParameters params){return true;}
}
