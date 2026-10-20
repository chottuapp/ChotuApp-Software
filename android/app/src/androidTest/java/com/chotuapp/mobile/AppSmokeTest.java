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
        if(!Profile.exists(context))Profile.create(context,"test@example.com","fixture-password".toCharArray());
        assertFalse(Profile.login(context,"test@example.com","wrong-password".toCharArray()));assertTrue(Profile.login(context,"test@example.com","fixture-password".toCharArray()));
        android.app.Activity activity=instrumentation.startActivitySync(new Intent(context,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));assertNotNull(activity);
        instrumentation.runOnMainSync(()->{try{
            MainActivity main=(MainActivity)activity;
            assertEquals("20 Oct 2026 · 5:30 PM PKT",main.pakistanTime("2026-10-20T12:30:00+00:00"));
            org.json.JSONObject drive=new org.json.JSONObject("{\"uploaded\":{\"Cool and Cool\":{\"folder\":\"F\",\"verified_utc\":\"2026-10-20T12:30:00+00:00\",\"file_url\":\"https://drive.google.com/file/d/id/view\"},\"Adam Cheese\":{\"folder\":\"F\"}}}");
            android.widget.LinearLayout results=main.column();main.populateDrive(results,drive,"COOL");
            assertEquals(3,results.getChildCount());
            android.widget.TextView count=(android.widget.TextView)results.getChildAt(2);assertEquals("1 file shown",count.getText().toString());
            main.populateDrive(results,drive,"no matching file");assertEquals(1,results.getChildCount());
            assertTrue(((android.widget.TextView)results.getChildAt(0)).getText().toString().contains("No matching"));
        }catch(Exception e){throw new AssertionError(e);}});
        FetchService.extract(context);
        String result=FetchService.python(context).getModule("mobile_backend").callAttr("self_test",new File(context.getFilesDir(),"engine").getPath(),new File(context.getFilesDir(),"smoke-test").getPath()).toString();
        assertEquals("Embedded export verified",result);
        Vault.save(context,"test-fixture-token");assertEquals("test-fixture-token",Vault.read(context));Vault.clear(context);assertEquals("",Vault.read(context));
    }
}
