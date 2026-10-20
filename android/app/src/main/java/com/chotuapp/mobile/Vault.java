package com.chotuapp.mobile;
import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
final class Vault {
    private static SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(!store.containsAlias("chotu-github")) {
            KeyGenerator gen=KeyGenerator.getInstance("AES","AndroidKeyStore");
            gen.init(new KeyGenParameterSpec.Builder("chotu-github",KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());gen.generateKey();
        }
        return (SecretKey)store.getKey("chotu-github",null);
    }
    static void save(Context c,String token) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());
        c.getSharedPreferences("vault",0).edit().putString("iv",Base64.encodeToString(cipher.getIV(),0)).putString("token",Base64.encodeToString(cipher.doFinal(token.getBytes("UTF-8")),0)).apply();
    }
    static String read(Context c) {
        try { android.content.SharedPreferences p=c.getSharedPreferences("vault",0);String value=p.getString("token","");if(value.isEmpty())return "";Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(p.getString("iv",""),0)));return new String(cipher.doFinal(Base64.decode(value,0)),"UTF-8"); }catch(Exception e){return "";}
    }
    static void clear(Context c){c.getSharedPreferences("vault",0).edit().clear().apply();}
}
