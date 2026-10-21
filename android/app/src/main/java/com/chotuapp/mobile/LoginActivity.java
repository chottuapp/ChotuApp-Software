package com.chotuapp.mobile;
import android.app.*;import android.os.*;import android.content.*;import android.graphics.Color;import android.text.InputType;import android.widget.*;
public class LoginActivity extends Activity {
 public void onCreate(Bundle state){super.onCreate(state);getWindow().setFlags(8192,8192);if(Profile.authenticated(this)){Profile.unlocked=true;startActivity(new Intent(this,MainActivity.class));finish();return;}boolean create=!Profile.exists(this);
  LinearLayout layout=new LinearLayout(this);layout.setOrientation(1);layout.setPadding(32,90,32,32);layout.setBackgroundColor(Color.rgb(245,247,243));
  TextView title=new TextView(this);title.setText("CHOTUAPP STUDIO\n\nYour catalog, connected.");title.setTextSize(26);title.setTextColor(Color.rgb(23,107,81));layout.addView(title);
  TextView info=new TextView(this);info.setText(create?"Create your private app login. This does not create a Gmail or GitHub account.":"Welcome back. Unlock your local profile.");info.setPadding(0,30,0,24);layout.addView(info);
  EditText email=new EditText(this);email.setSingleLine();email.setInputType(33);email.setText(getSharedPreferences("profile",0).getString("email","Chottuapp@gmail.com"));layout.addView(email);
  EditText password=new EditText(this);password.setSingleLine();password.setHint("Password · at least 8 characters");password.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);layout.addView(password);
  Button submit=new Button(this);submit.setText(create?"Create local profile":"Unlock");layout.addView(submit);setContentView(layout);
  submit.setOnClickListener(v->{String address=email.getText().toString();char[] secret=password.getText().toString().toCharArray();if(!android.util.Patterns.EMAIL_ADDRESS.matcher(address).matches()){email.setError("Enter a valid email");return;}submit.setEnabled(false);
   new Thread(()->{boolean success=false;try{if(create){Profile.create(this,address,secret);success=true;}else success=Profile.login(this,address,secret);}catch(Exception ignored){}finally{java.util.Arrays.fill(secret,'\0');}final boolean ok=success;runOnUiThread(()->{submit.setEnabled(true);password.setText("");if(ok){startActivity(new Intent(this,MainActivity.class));finish();}else password.setError(create?"Use a password with at least 8 characters":"Email or password did not match");});}).start();});
 }
}
