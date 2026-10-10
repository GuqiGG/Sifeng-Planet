package com.sifeng.planet;

import android.Manifest;
import android.animation.ObjectAnimator;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.CookieHandler;
import java.net.CookiePolicy;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    final Handler ui = new Handler();
    LinearLayout root, body, nav;
    FrameLayout stage;
    EditText termsInput, searchInput;
    TextView status;
    MediaPlayer player;
    WindowManager wm;
    View capsule;
    ObjectAnimator coverSpin;
    JSONObject current;
    final ArrayList<JSONObject> songs = new ArrayList<>();
    final ArrayList<JSONObject> favorites = new ArrayList<>();
    final ArrayList<JSONObject> history = new ArrayList<>();
    final ExecutorService coverPool = Executors.newFixedThreadPool(4);
    int mediaToken = 0;
    int index = -1, step = 0, mode = 0;
    boolean overlayWanted = false, loading = false, pendingSearch = false;
    int searchPage = 1, searchCount = 0;
    String activeQuery = "";
    String terms = "司凤版,司凤,隆德齐", screen = "";
    final int ink = Color.rgb(25,25,28), muted = Color.rgb(125,125,132), accent = Color.rgb(229,78,101);

    int dp(float v) { return (int)(getResources().getDisplayMetrics().density*v + .5f); }
    GradientDrawable bg(int color, int radius) { GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(radius)); return d; }
    LinearLayout vertical() { LinearLayout v = new LinearLayout(this); v.setOrientation(1); return v; }
    TextView text(String value, int size, boolean bold, int color) {
        TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return t;
    }
    void pad(View v, int l, int t, int r, int b) { v.setPadding(dp(l),dp(t),dp(r),dp(b)); }
    void space(LinearLayout box, int h) { View v = new View(this); box.addView(v,new LinearLayout.LayoutParams(1,dp(h))); }
    Button button(String label, boolean primary, Runnable click) {
        Button b = new Button(this); b.setText(label); b.setTextSize(15); b.setAllCaps(false);
        b.setTextColor(primary ? Color.WHITE : ink); b.setBackground(bg(primary ? ink : 0xfff5f5f6, 16));
        b.setElevation(dp(primary ? 4 : 2)); b.setMinimumHeight(dp(50));
        b.setOnClickListener(v -> click.run()); return b;
    }
    void addButton(LinearLayout box, String label, boolean primary, Runnable click) {
        box.addView(button(label,primary,click),new LinearLayout.LayoutParams(-1,dp(52)));
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); getWindow().setStatusBarColor(Color.WHITE); getWindow().setNavigationBarColor(Color.WHITE);
        CookieHandler.setDefault(new java.net.CookieManager(null, CookiePolicy.ACCEPT_ALL));
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        terms = getPreferences(0).getString("terms",terms); mode=getPreferences(0).getInt("mode",0);
        overlayWanted=getPreferences(0).getBoolean("floating",false);
        restore("favorites", favorites); restore("history", history);
        root=vertical(); root.setBackgroundColor(Color.WHITE); setContentView(root);
        stage=new FrameLayout(this); root.addView(stage,new LinearLayout.LayoutParams(-1,0,1));
        if (getPreferences(0).getBoolean("intro",false)) { show("home"); search(); } else show("intro");
    }
    void show(String target) {
        if (target.equals(screen)) return;
        if (stage.getChildCount()==0) { screen=target; render(); return; }
        stage.animate().alpha(0).translationX(-dp(18)).setDuration(200).withEndAction(() -> {
            screen=target; render(); stage.setTranslationX(dp(18));
            stage.animate().alpha(1).translationX(0).setDuration(320).start();
        }).start();
    }
    void render() {
        stage.removeAllViews();
        ScrollView scroll=new ScrollView(this); scroll.setFillViewport(true); scroll.setVerticalScrollBarEnabled(false);
        LinearLayout page=vertical(); pad(page,24,26,24,28); scroll.addView(page); stage.addView(scroll);
        while(root.getChildCount()>1) root.removeViewAt(1);
        if (screen.equals("intro")) intro(page);
        else if (screen.equals("setup")) setup(page);
        else if (screen.equals("player")) playerPage(page);
        else if (screen.equals("settings")) settings(page);
        else listPage(page);
        if (!screen.equals("intro") && !screen.equals("setup")) nav(root);
    }
    void header(LinearLayout page, String eyebrow, String title, String sub) {
        TextView e=text(eyebrow,11,true,accent); e.setLetterSpacing(.17f); page.addView(e); space(page,10);
        page.addView(text(title,34,true,ink)); space(page,6); page.addView(text(sub,14,false,muted)); space(page,24);
    }
    void intro(LinearLayout page) {
        page.setGravity(Gravity.CENTER_VERTICAL);
        TextView title=text("司凤星球",52,true,ink); page.addView(title); title.setTranslationY(dp(65));
        TextView line=text("听你想听的，通透你想通透的",17,false,muted); page.addView(line); line.setAlpha(0);
        space(page,36);
        Button start=button("开始配置  →",true,()->{step=0;show("setup");});
        page.addView(start,new LinearLayout.LayoutParams(dp(220),dp(58))); start.setAlpha(0); start.setEnabled(false);
        space(page,16); Button skip=button("跳过配置",false,()->finishSetup()); page.addView(skip,new LinearLayout.LayoutParams(dp(160),dp(46)));
        ui.postDelayed(() -> title.animate().translationY(0).setDuration(1500).start(),500);
        ui.postDelayed(() -> line.animate().alpha(1).setDuration(900).start(),1900);
        ui.postDelayed(() -> {start.setEnabled(true);start.animate().alpha(1).translationX(0).setDuration(750).start();},2900);
        start.setTranslationX(dp(26));
    }
    void setup(LinearLayout page) {
        String[] names={"想听什么","播完之后","悬浮胶囊"};
        header(page,String.format("%02d  /  03",step+1),names[step],"按你的习惯选择，之后仍可随时修改。");
        if (step==0) {
            page.addView(text("搜索词",15,true,ink)); space(page,9);
            termsInput=new EditText(this); termsInput.setSingleLine(true); termsInput.setText(terms);
            termsInput.setHint("用逗号分隔，最多 8 个"); termsInput.setTextSize(16); termsInput.setBackground(bg(0xfff4f4f5,14)); pad(termsInput,16,8,16,8);
            page.addView(termsInput,new LinearLayout.LayoutParams(-1,dp(58)));
        } else if(step==1) {
            String[] modes={"顺序播放","单曲循环","随机播放"};
            for(int i=0;i<3;i++){final int choice=i; Button b=button((mode==i?"✓  ":"    ")+modes[i],false,()->{mode=choice;render();});page.addView(b,new LinearLayout.LayoutParams(-1,dp(58)));space(page,12);}
        } else {
            page.addView(text("播放时显示横向小胶囊，封面会缓慢旋转。",15,false,muted));space(page,14);
            addButton(page,overlayWanted?"✓  显示悬浮胶囊":"开启悬浮胶囊",false,()->{
                overlayWanted=!overlayWanted; if(overlayWanted) requestOverlay(); render();
            });
            space(page,12);page.addView(text("仅在开启时请求系统悬浮窗权限。",12,false,muted));
        }
        space(page,42); addButton(page,step==2?"开始听":"继续",true,()->{
            if(step==0){String s=termsInput.getText().toString().trim();if(s.isEmpty()){termsInput.setError("请输入搜索词");return;} terms=s;}
            if(step<2){stepTo(step+1);}else finishSetup();
        });
        space(page,12); addButton(page,step==0?"跳过配置":"上一步",false,()->{if(step==0)finishSetup();else stepTo(step-1);});
    }
    void stepTo(int target){boolean forward=target>step;stage.animate().alpha(0).translationX(forward?-dp(18):dp(18)).setDuration(180).withEndAction(()->{step=target;render();stage.setTranslationX(forward?dp(18):-dp(18));stage.animate().alpha(1).translationX(0).setDuration(300).start();}).start();}
    void finishSetup(){getPreferences(0).edit().putBoolean("intro",true).putString("terms",terms).putInt("mode",mode).putBoolean("floating",overlayWanted).apply();show("home");search();}
    void nav(LinearLayout page) {
        LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);row.setBackground(bg(0xfff6f6f7,20));pad(row,6,6,6,6);row.setElevation(dp(3));
        String[] labels={"发现","收藏","记录","播放","设置"};String[] routes={"home","favorites","history","player","settings"};
        for(int i=0;i<labels.length;i++){ final String route=routes[i];TextView tab=text(labels[i],12,screen.equals(route),screen.equals(route)?ink:muted);tab.setGravity(Gravity.CENTER);row.addView(tab,new LinearLayout.LayoutParams(0,dp(43),1));tab.setOnClickListener(v->show(route));}
        LinearLayout.LayoutParams navParams=new LinearLayout.LayoutParams(-1,dp(58));
        navParams.setMargins(dp(16),0,dp(16),dp(16));
        page.addView(row,navParams);
    }
    void listPage(LinearLayout page) {
        String title=screen.equals("favorites")?"本地收藏":screen.equals("history")?"司凤记录":"只听喜欢的。";
        header(page,"SIFENG RADIO  /  BILIBILI",title,screen.equals("home")?"司凤版、司凤、隆德齐。轻轻点开，音乐就开始了。":"喜欢的歌，随时再听。");
        if(screen.equals("home")){
            searchInput=new EditText(this);searchInput.setSingleLine(true);searchInput.setText(activeQuery);
            searchInput.setHint("搜索歌曲、歌手或视频…");searchInput.setTextSize(16);
            searchInput.setBackground(bg(0xfff4f4f5,14));pad(searchInput,16,8,16,8);
            page.addView(searchInput,new LinearLayout.LayoutParams(-1,dp(56)));space(page,10);
            searchInput.setOnEditorActionListener((v,action,event)->{submitSearch();return true;});
            LinearLayout actions=new LinearLayout(this);
            Button find=button("搜索",true,()->submitSearch());actions.addView(find,new LinearLayout.LayoutParams(0,dp(50),1));
            Button fresh=button("换一批",false,()->refreshSearch());LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(0,dp(50),1);rp.leftMargin=dp(10);actions.addView(fresh,rp);
            page.addView(actions);space(page,10);
            page.addView(text(searchCount%2==1?"本次按播放量排序":"本次随机推荐",12,false,muted));space(page,18);
        }
        ArrayList<JSONObject> list=screen.equals("favorites")?favorites:screen.equals("history")?history:songs;
        if(list.isEmpty()) {page.addView(text(loading?"正在发现音乐…":"这里还没有歌曲",17,true,muted));}
        for(JSONObject song:list)card(page,song);
        space(page,26);
    }
    void card(LinearLayout page,JSONObject song){
        LinearLayout card=new LinearLayout(this);card.setGravity(Gravity.CENTER_VERTICAL);pad(card,10,10,10,10);card.setBackground(bg(0xfff5f5f6,18));
        ImageView cover=new ImageView(this);cover.setScaleType(ImageView.ScaleType.CENTER_CROP);cover.setBackground(bg(0xffe6e6e8,12));
        card.addView(cover,new LinearLayout.LayoutParams(dp(82),dp(72)));loadCover(song.optString("pic"),cover);
        LinearLayout copy=vertical();pad(copy,14,0,0,0);TextView name=text(song.optString("title"),15,true,ink);name.setMaxLines(2);copy.addView(name);
        space(copy,5);copy.addView(text(song.optString("author"),12,false,muted));card.addView(copy,new LinearLayout.LayoutParams(0,-2,1));
        TextView heart=text(contains(favorites,song)?"♥":"♡",25,false,accent);pad(heart,12,6,4,6);card.addView(heart);heart.setOnClickListener(v->{toggleFavorite(song);heart.setText(contains(favorites,song)?"♥":"♡");});
        card.setOnClickListener(v->play(song));page.addView(card,new LinearLayout.LayoutParams(-1,dp(96)));space(page,10);
    }
    void playerPage(LinearLayout page){
        header(page,"正在播放",current==null?"选一首，开始听。":current.optString("title"),current==null?"从发现或收藏里挑一首。":current.optString("author"));
        ImageView cover=new ImageView(this);cover.setScaleType(ImageView.ScaleType.CENTER_CROP);cover.setBackground(bg(0xfff3f3f4,24));
        page.addView(cover,new LinearLayout.LayoutParams(-1,dp(230)));if(current!=null)loadCover(current.optString("pic"),cover);
        space(page,22);status=text(player!=null&&player.isPlaying()?"正在播放":"准备播放",14,false,muted);page.addView(status);space(page,18);
        LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER);Button prev=button("上一首",false,()->next(-1));row.addView(prev,new LinearLayout.LayoutParams(0,dp(52),1));
        Button play=button(player!=null&&player.isPlaying()?"暂停":"播放",true,()->toggle());LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(52),1);p.setMargins(dp(8),0,dp(8),0);row.addView(play,p);
        Button next=button("下一首",false,()->next(1));row.addView(next,new LinearLayout.LayoutParams(0,dp(52),1));page.addView(row);
        space(page,12);addButton(page,current!=null&&contains(favorites,current)?"已收藏":"收藏此曲",false,()->{if(current!=null){toggleFavorite(current);render();}});
        space(page,32);
    }
    void settings(LinearLayout page){
        header(page,"偏好设置","听你想听的。","所有选择都可以随时改动。");
        page.addView(text("搜索词",14,true,ink));space(page,8);
        termsInput=new EditText(this);termsInput.setSingleLine(true);termsInput.setText(terms);termsInput.setBackground(bg(0xfff4f4f5,14));pad(termsInput,16,8,16,8);page.addView(termsInput,new LinearLayout.LayoutParams(-1,dp(56)));
        space(page,22);page.addView(text("播完之后",14,true,ink));space(page,10);
        String[] modes={"顺序播放","单曲循环","随机播放"};for(int i=0;i<3;i++){final int choice=i;addButton(page,(mode==i?"✓  ":"    ")+modes[i],false,()->{String pending=termsInput.getText().toString();mode=choice;render();termsInput.setText(pending);});space(page,8);}
        space(page,10);addButton(page,overlayWanted?"✓  显示悬浮胶囊":"开启悬浮胶囊",false,()->{String pending=termsInput.getText().toString();overlayWanted=!overlayWanted;if(overlayWanted)requestOverlay();else hideCapsule();render();termsInput.setText(pending);});
        space(page,20);addButton(page,"保存设置",true,()->{String s=termsInput.getText().toString().trim();if(!s.isEmpty())terms=s;getPreferences(0).edit().putString("terms",terms).putInt("mode",mode).putBoolean("floating",overlayWanted).apply();show("home");search();});
        space(page,32);
    }
    boolean contains(ArrayList<JSONObject> list,JSONObject item){for(JSONObject x:list)if(x.optString("bvid").equals(item.optString("bvid")))return true;return false;}
    void toggleFavorite(JSONObject song){if(contains(favorites,song))favorites.removeIf(x->x.optString("bvid").equals(song.optString("bvid")));else favorites.add(0,song);save("favorites",favorites);}
    void restore(String key,ArrayList<JSONObject> into){try{JSONArray rows=new JSONArray(getPreferences(0).getString(key,"[]"));for(int i=0;i<rows.length();i++)into.add(rows.getJSONObject(i));}catch(Exception ignored){}}
    void save(String key,ArrayList<JSONObject> list){JSONArray rows=new JSONArray();for(JSONObject item:list)rows.put(item);getPreferences(0).edit().putString(key,rows.toString()).apply();}
    String fetch(String url) throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();c.setConnectTimeout(12000);c.setReadTimeout(15000);c.setRequestProperty("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36");c.setRequestProperty("Referer","https://www.bilibili.com/");
        try(InputStream in=c.getInputStream();BufferedReader r=new BufferedReader(new InputStreamReader(in))){StringBuilder b=new StringBuilder();String line;while((line=r.readLine())!=null)b.append(line);return b.toString();}finally{c.disconnect();}
    }
    JSONObject api(String url,String step) throws Exception {
        JSONObject response=new JSONObject(fetch(url));
        if(response.optInt("code",-1)!=0||response.isNull("data")||!response.has("data"))
            throw new java.io.IOException(step+"：哔哩哔哩返回 "+response.optInt("code",-1)+" "+response.optString("message"));
        return response;
    }
    String encoded(String value){try{return java.net.URLEncoder.encode(value,"UTF-8");}catch(Exception e){return value;}}
    void submitSearch(){activeQuery=searchInput.getText().toString().trim();searchPage=1;if(loading){pendingSearch=true;return;}songs.clear();search();}
    void refreshSearch(){if(loading){pendingSearch=true;return;}songs.clear();search();}
    void search(){if(loading)return;loading=true;final boolean popular=(++searchCount%2)==1;final String query=activeQuery;final int pageNumber=popular?1:1+new Random().nextInt(5);searchPage=pageNumber;if(screen.equals("home"))render();new Thread(()->{
        ArrayList<JSONObject> found=new ArrayList<>();String error="";
        try{fetch("https://www.bilibili.com/");String[] keys=query.isEmpty()?terms.split("[,，、;；]"):new String[]{"司凤","司凤版","隆德齐"};
            for(String key:keys){key=key.trim();if(key.isEmpty())continue;
                String keyword=query.isEmpty()?key:query+" "+key;
                JSONObject result=api("https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword="+encoded(keyword)+"&page="+pageNumber+(popular?"&order=click":""),"搜索");
                JSONArray rows=result.optJSONObject("data").optJSONArray("result");if(rows==null)continue;
                for(int i=0;i<rows.length();i++){JSONObject item=rows.optJSONObject(i);if(item==null)continue;String title=android.text.Html.fromHtml(item.optString("title"),android.text.Html.FROM_HTML_MODE_LEGACY).toString();
                    boolean allowed=false;for(String term:keys)if(!term.trim().isEmpty()&&title.contains(term.trim()))allowed=true;
                    if(!allowed||!item.optString("bvid").matches("BV[0-9A-Za-z]+"))continue;
                    JSONObject clean=new JSONObject();clean.put("title",title);clean.put("bvid",item.optString("bvid"));clean.put("aid",item.optLong("aid",item.optLong("id")));clean.put("play",item.optLong("play"));clean.put("author",item.optString("author"));clean.put("pic",item.optString("pic").startsWith("//")?"https:"+item.optString("pic"):item.optString("pic"));
                    boolean duplicate=false;for(JSONObject old:found)if(old.optString("bvid").equals(clean.optString("bvid")))duplicate=true;if(!duplicate)found.add(clean);
                }
            }
        }catch(Exception e){error=e.getMessage();}
        if(popular)found.sort((a,b)->Long.compare(b.optLong("play"),a.optLong("play")));else Collections.shuffle(found);
        if(found.size()>36)found.subList(36,found.size()).clear();
        String failure=error;ui.post(()->{loading=false;if(pendingSearch){pendingSearch=false;songs.clear();search();return;}songs.clear();songs.addAll(found);if(screen.equals("home")){render();if(!failure.isEmpty()){TextView note=text("搜索暂时未完成："+failure,12,false,muted);bodyNote(note);}}});
    }).start();}
    void bodyNote(TextView note){if(stage.getChildCount()>0&&stage.getChildAt(0) instanceof ScrollView){View child=((ScrollView)stage.getChildAt(0)).getChildAt(0);if(child instanceof LinearLayout)((LinearLayout)child).addView(note,1);}}
    void loadCover(String url,ImageView view){if(url.isEmpty())return;coverPool.submit(()->{try{HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();c.setRequestProperty("Referer","https://www.bilibili.com/");Bitmap b=BitmapFactory.decodeStream(c.getInputStream());c.disconnect();ui.post(()->{if(view.getParent()!=null)view.setImageBitmap(b);});}catch(Exception ignored){}});}
    void play(JSONObject song){hideCapsule();int token=++mediaToken;current=song;index=-1;for(int i=0;i<songs.size();i++)if(songs.get(i).optString("bvid").equals(song.optString("bvid")))index=i;show("player");
        history.removeIf(x->x.optString("bvid").equals(song.optString("bvid")));history.add(0,song);while(history.size()>100)history.remove(history.size()-1);save("history",history);
        if(player!=null){player.release();player=null;}new Thread(()->{
            try{String bvid=song.optString("bvid");long aid=song.optLong("aid");int cid;
                try{JSONArray pages=api("https://api.bilibili.com/x/player/pagelist?bvid="+encoded(bvid),"视频信息").getJSONArray("data");cid=pages.getJSONObject(0).getInt("cid");}
                catch(Exception first){if(aid>0){JSONArray pages=api("https://api.bilibili.com/x/player/pagelist?aid="+aid,"视频信息").getJSONArray("data");cid=pages.getJSONObject(0).getInt("cid");}
                    else cid=api("https://api.bilibili.com/x/web-interface/view?bvid="+encoded(bvid),"视频信息").getJSONObject("data").getInt("cid");}
                String base="https://api.bilibili.com/x/player/playurl?cid="+cid+"&qn=16&fnval=0";
                String[] urlsToTry=aid>0?new String[]{base+"&bvid="+encoded(bvid),base+"&avid="+aid,base+"&bvid="+encoded(bvid)+"&platform=html5",base+"&avid="+aid+"&platform=html5"}:new String[]{base+"&bvid="+encoded(bvid),base+"&bvid="+encoded(bvid)+"&platform=html5"};
                JSONArray urls=null;Exception last=null;
                for(String candidate:urlsToTry){try{urls=api(candidate,"播放地址").getJSONObject("data").optJSONArray("durl");if(urls!=null&&urls.length()>0)break;}catch(Exception e){last=e;if(candidate.equals(urlsToTry[0]))try{fetch("https://www.bilibili.com/");}catch(Exception ignored){}}}
                if(urls==null||urls.length()==0)throw last!=null?last:new java.io.IOException("当前视频没有可用的 MP4 地址");
                String url=urls.getJSONObject(0).getString("url");
                ui.post(()->{if(token==mediaToken)startMedia(url);});
            }catch(Exception e){ui.post(()->{if(token==mediaToken&&status!=null)status.setText("播放准备失败："+e.getMessage());});}
        }).start();}
    void startMedia(String url){try{player=new MediaPlayer();player.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build());
        HashMap<String,String> h=new HashMap<>();h.put("Referer","https://www.bilibili.com/");h.put("User-Agent","Mozilla/5.0");player.setDataSource(this,Uri.parse(url),h);
        player.setOnPreparedListener(p->{p.start();if(status!=null)status.setText("正在播放");showCapsule();});player.setOnCompletionListener(p->{if(mode==1){p.seekTo(0);p.start();}else next(1);});
        player.setOnErrorListener((p,a,b)->{if(status!=null)status.setText("播放器暂时无法继续");return true;});player.prepareAsync();
    }catch(Exception e){if(status!=null)status.setText("播放失败："+e.getMessage());}}
    void toggle(){if(player==null)return;if(player.isPlaying()){player.pause();hideCapsule();}else{player.start();showCapsule();}if(screen.equals("player"))render();}
    void next(int delta){if(songs.isEmpty())return;int next;if(mode==2&&songs.size()>1){do{next=new Random().nextInt(songs.size());}while(next==index);}else next=(index+delta+songs.size())%songs.size();play(songs.get(next));}
    void requestOverlay(){if(Build.VERSION.SDK_INT>=23&&!Settings.canDrawOverlays(this)){Intent i=new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName()));startActivity(i);}}
    @Override protected void onResume(){super.onResume();if(player!=null&&player.isPlaying())showCapsule();}
    void showCapsule(){if(!overlayWanted||player==null||!player.isPlaying()||current==null||!Settings.canDrawOverlays(this)||capsule!=null)return;
        wm=(WindowManager)getSystemService(WINDOW_SERVICE);LinearLayout pill=new LinearLayout(this);pill.setGravity(Gravity.CENTER_VERTICAL);pad(pill,7,7,14,7);pill.setBackground(bg(Color.WHITE,32));pill.setElevation(dp(8));
        ImageView cover=new ImageView(this);cover.setScaleType(ImageView.ScaleType.CENTER_CROP);cover.setBackground(bg(0xffeeeeef,24));cover.setClipToOutline(true);pill.addView(cover,new LinearLayout.LayoutParams(dp(46),dp(46)));loadCover(current.optString("pic"),cover);
        TextView label=text("播放中："+current.optString("title"),12,true,ink);label.setSingleLine(true);label.setEllipsize(android.text.TextUtils.TruncateAt.END);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);lp.leftMargin=dp(12);pill.addView(label,lp);
        pill.setOnClickListener(v->{Intent intent=new Intent(this,MainActivity.class);intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP);startActivity(intent);});
        WindowManager.LayoutParams params=new WindowManager.LayoutParams(dp(300),dp(60),WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,android.graphics.PixelFormat.TRANSLUCENT);params.gravity=Gravity.TOP|Gravity.CENTER_HORIZONTAL;params.y=dp(34);
        try{wm.addView(pill,params);capsule=pill;coverSpin=ObjectAnimator.ofFloat(cover,"rotation",0,360);coverSpin.setDuration(48000);coverSpin.setRepeatCount(ObjectAnimator.INFINITE);coverSpin.setInterpolator(new android.view.animation.LinearInterpolator());coverSpin.start();}catch(Exception ignored){}
    }
    void hideCapsule(){if(coverSpin!=null){coverSpin.cancel();coverSpin=null;}if(capsule!=null){try{wm.removeView(capsule);}catch(Exception ignored){}capsule=null;}}
    @Override protected void onDestroy(){hideCapsule();coverPool.shutdownNow();if(player!=null)player.release();super.onDestroy();}
}



