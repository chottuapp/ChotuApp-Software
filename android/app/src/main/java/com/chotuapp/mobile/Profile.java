package com.chotuapp.mobile;
import android.content.Context;
import android.util.Base64;
import java.security.*;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
final class Profile {
 static boolean unlocked=false;
 static boolean exists(Context c){return c.getSharedPreferences("profile",0).contains("hash");}
 static byte[] derive(char[] password,byte[] salt)throws Exception{return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(new PBEKeySpec(password,salt,210000,256)).getEncoded();}
 static void create(Context c,String email,char[] password)throws Exception{
  if(exists(c))throw new IllegalStateException("Profile already exists");
  if(password.length<8)throw new IllegalArgumentException("Use at least 8 characters");
  byte[] salt=new byte[32];new SecureRandom().nextBytes(salt);
  c.getSharedPreferences("profile",0).edit().putString("email",email.trim()).putString("salt",Base64.encodeToString(salt,2)).putString("hash",Base64.encodeToString(derive(password,salt),2)).commit();unlocked=true;
 }
 static boolean login(Context c,String email,char[] password)throws Exception{
  android.content.SharedPreferences p=c.getSharedPreferences("profile",0);
  unlocked=p.getString("email","").equalsIgnoreCase(email.trim())&&MessageDigest.isEqual(Base64.decode(p.getString("hash",""),2),derive(password,Base64.decode(p.getString("salt",""),2)));return unlocked;
 }
}
