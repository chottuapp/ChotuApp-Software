package com.chotuapp.mobile;
import android.test.ActivityInstrumentationTestCase2;
import java.io.File;
public class AppSmokeTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public AppSmokeTest(){super(MainActivity.class);}
    public void testNativeDashboardAndEmbeddedExporter() throws Exception {
        MainActivity activity=getActivity();assertNotNull(activity);
        FetchService.extract(activity);
        String result=FetchService.python(activity).getModule("mobile_backend").callAttr("self_test",new File(activity.getFilesDir(),"engine").getPath(),new File(activity.getFilesDir(),"smoke-test").getPath()).toString();
        assertEquals("Embedded export verified",result);
        Vault.save(activity,"test-fixture-token");assertEquals("test-fixture-token",Vault.read(activity));Vault.clear(activity);assertEquals("",Vault.read(activity));
    }
}
