package com.chotuapp.mobile;
import android.content.Context;
import android.content.Intent;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import java.io.File;
@RunWith(AndroidJUnit4.class)
public class AppSmokeTest {
    @Test public void nativeDashboardAndEmbeddedExporter() throws Exception {
        android.app.Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
        Context context=instrumentation.getTargetContext();
        MainActivity.suppressAutoFreshForTests=true;
        if(!Profile.exists(context))Profile.create(context,"test@example.com","fixture-password".toCharArray());
        assertFalse(Profile.login(context,"test@example.com","wrong-password".toCharArray()));assertTrue(Profile.login(context,"test@example.com","fixture-password".toCharArray()));
        Profile.unlocked=false;assertTrue(Profile.authenticated(context));Profile.lock(context);assertFalse(Profile.authenticated(context));assertTrue(Profile.login(context,"test@example.com","fixture-password".toCharArray()));
        android.app.Activity activity=instrumentation.startActivitySync(new Intent(context,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));assertNotNull(activity);
        instrumentation.runOnMainSync(()->{try{
            MainActivity main=(MainActivity)activity;
            assertEquals("1.6-studio",main.installedVersionName());
            assertEquals("20 Oct 2026 · 5:30 PM PKT",main.pakistanTime("2026-10-20T12:30:00+00:00"));
            org.json.JSONObject drive=new org.json.JSONObject("{\"uploaded\":{\"Cool and Cool\":{\"folder\":\"F\",\"verified_utc\":\"2026-10-20T12:30:00+00:00\",\"file_url\":\"https://drive.google.com/file/d/id/view\"},\"Adam Cheese\":{\"folder\":\"F\"}}}");
            android.widget.LinearLayout results=main.column();main.populateDrive(results,drive,"COOL");
            assertEquals(3,results.getChildCount());
            android.widget.TextView count=(android.widget.TextView)results.getChildAt(2);assertEquals("1 file shown",count.getText().toString());
            drive.put("original_uploads",new org.json.JSONObject("{\"Cool and Cool\":{\"verified_utc\":\"2026-10-19T00:00:00Z\"}}"));
            org.json.JSONObject newest=MainActivity.latestDriveFiles(drive);assertEquals(2,newest.length());assertEquals("2026-10-20T12:30:00+00:00",newest.getJSONObject("Cool and Cool").getString("verified_utc"));
            main.populateDrive(results,drive,"no matching file");assertEquals(1,results.getChildCount());
            assertTrue(((android.widget.TextView)results.getChildAt(0)).getText().toString().contains("No matching"));
        }catch(Exception e){throw new AssertionError(e);}});
        File old=new File(context.getFilesDir(),"khaadi");old.mkdirs();File evidence=new File(old,"old-cache-fixture.txt");try(java.io.FileOutputStream stream=new java.io.FileOutputStream(evidence)){stream.write("saved".getBytes());}
        File fresh=FetchService.prepareFreshDirectory(context,"fresh804-20261021-deadbeef");assertTrue(evidence.exists());assertFalse(new File(fresh,"old-cache-fixture.txt").exists());assertEquals(fresh,FetchService.dataDirectory(context));context.getSharedPreferences("worker",0).edit().remove("data_dir").remove("fresh_campaign_seen").commit();
        HeartbeatJobs.ensureScheduled(context);
        android.app.job.JobInfo heartbeat=context.getSystemService(android.app.job.JobScheduler.class).getPendingJob(HeartbeatJobs.PERIODIC_ID);
        assertNotNull(heartbeat);assertTrue(heartbeat.isPersisted());assertTrue(heartbeat.getIntervalMillis()>=15*60*1000L);
        android.content.pm.ServiceInfo service=context.getPackageManager().getServiceInfo(new android.content.ComponentName(context,HeartbeatJobs.class),0);
        assertEquals("android.permission.BIND_JOB_SERVICE",service.permission);
        assertEquals(7,context.getPackageManager().getPackageInfo(context.getPackageName(),0).getLongVersionCode());
        FetchService.extract(context);
        String result=FetchService.python(context).getModule("mobile_backend").callAttr("self_test",new File(context.getFilesDir(),"engine").getPath(),new File(context.getFilesDir(),"smoke-test").getPath()).toString();
        assertEquals("Embedded export verified",result);
        Vault.save(context,"test-fixture-token");assertEquals("test-fixture-token",Vault.read(context));Vault.clear(context);assertEquals("",Vault.read(context));
    }
}
