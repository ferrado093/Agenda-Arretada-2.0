"""Injeta o codigo nativo do alarme (voz + toque, tela cheia, reinicio) no projeto Android
gerado pelo Capacitor. Roda no GitHub Actions depois de "npx cap add android"."""
import os
import sys

MANIFEST = "android/app/src/main/AndroidManifest.xml"
DESTINO = "android/app/src/main/java/com/agendaarretada/app"

PERMISSOES = [
    "POST_NOTIFICATIONS", "VIBRATE", "WAKE_LOCK", "RECEIVE_BOOT_COMPLETED",
    "SCHEDULE_EXACT_ALARM", "USE_EXACT_ALARM", "USE_FULL_SCREEN_INTENT",
    "RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS", "FOREGROUND_SERVICE",
    "FOREGROUND_SERVICE_MEDIA_PLAYBACK", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
]

COMPONENTES = """
        <receiver android:name=".AlarmeReceiver" android:exported="false" />
        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
                <action android:name="android.intent.action.TIME_SET" />
                <action android:name="android.intent.action.TIMEZONE_CHANGED" />
            </intent-filter>
        </receiver>
        <service android:name=".AlarmeService" android:exported="false" android:foregroundServiceType="mediaPlayback" />
        <activity android:name=".AlarmeActivity" android:exported="false"
            android:showWhenLocked="true" android:turnScreenOn="true"
            android:launchMode="singleInstance" android:excludeFromRecents="true"
            android:theme="@android:style/Theme.Material.NoActionBar" />
"""

ARQUIVOS = {}

ARQUIVOS["AlarmeActivity.java"] = r'''package com.agendaarretada.app;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONObject;

/** Tela cheia que aparece por cima do bloqueio quando o alarme dispara. */
public class AlarmeActivity extends Activity {
    private TextView tTitulo, tCorpo;
    private JSONObject o = new JSONObject();
    private int extra = 0;
    private BroadcastReceiver rec;

    private int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density); }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        if (Build.VERSION.SDK_INT >= 27) { setShowWhenLocked(true); setTurnScreenOn(true); }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD);

        LinearLayout raiz = new LinearLayout(this);
        raiz.setOrientation(LinearLayout.VERTICAL);
        raiz.setGravity(Gravity.CENTER);
        raiz.setBackgroundColor(Color.BLACK);
        raiz.setPadding(dp(24), dp(24), dp(24), dp(24));

        TextView icone = new TextView(this);
        icone.setText("\u23F0");
        icone.setTextSize(64);
        icone.setGravity(Gravity.CENTER);
        raiz.addView(icone);

        tTitulo = new TextView(this);
        tTitulo.setTextColor(Color.WHITE);
        tTitulo.setTextSize(26);
        tTitulo.setTypeface(Typeface.DEFAULT_BOLD);
        tTitulo.setGravity(Gravity.CENTER);
        raiz.addView(tTitulo);

        tCorpo = new TextView(this);
        tCorpo.setTextColor(Color.WHITE);
        tCorpo.setTextSize(20);
        tCorpo.setGravity(Gravity.CENTER);
        tCorpo.setPadding(0, dp(12), 0, dp(24));
        raiz.addView(tCorpo);

        botao(raiz, "Concluir", AlarmeService.ACAO_CONCLUIR, true);
        botao(raiz, "Adiar 5 minutos", AlarmeService.ACAO_ADIAR, true);
        botao(raiz, "Parar o som", AlarmeService.ACAO_PARAR_SOM, false);

        setContentView(raiz);
        ler(getIntent());

        rec = new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent i) { finish(); }
        };
        IntentFilter f = new IntentFilter(AlarmeService.FECHAR);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(rec, f, Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(rec, f);
    }

    private void botao(LinearLayout raiz, String texto, final String acao, final boolean fecha) {
        Button bt = new Button(this);
        bt.setText(texto);
        bt.setTextSize(20);
        bt.setAllCaps(false);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(14);
        raiz.addView(bt, lp);
        bt.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                Intent s = new Intent(AlarmeActivity.this, AlarmeService.class);
                s.setAction(acao);
                s.putExtra("json", o.toString());
                startService(s);
                if (fecha) finish();
            }
        });
    }

    private void ler(Intent i) {
        try { o = new JSONObject(i.getStringExtra("json")); } catch (Exception e) { o = new JSONObject(); }
        extra = i.getIntExtra("extra", 0);
        tTitulo.setText(o.optString("titulo", "Agenda Arretada"));
        String corpo = o.optString("corpo", "");
        if (extra > 0) corpo += "\n(+" + extra + (extra > 1 ? " outros avisos)" : " outro aviso)");
        tCorpo.setText(corpo);
    }

    @Override
    protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        setIntent(i);
        ler(i);
    }

    @Override
    protected void onDestroy() {
        try { unregisterReceiver(rec); } catch (Exception e) { }
        super.onDestroy();
    }
}
'''

ARQUIVOS["AlarmePlugin.java"] = r'''package com.agendaarretada.app;

import android.app.NotificationManager;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Base64;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.util.HashSet;
import java.util.Set;

/** Ponte entre o app (JavaScript) e o alarme nativo do Android. */
@CapacitorPlugin(name = "Alarme")
public class AlarmePlugin extends Plugin {
    static AlarmePlugin inst;
    private MediaPlayer previa;
    private final Handler h = new Handler(Looper.getMainLooper());

    @Override
    public void load() { inst = this; }

    static void emitir() {
        if (inst != null) {
            try { inst.notifyListeners("acao", new JSObject()); } catch (Exception e) { }
        }
    }

    @PluginMethod
    public void agendar(PluginCall call) {
        try {
            Context c = getContext();
            JSArray arr = call.getArray("alarmes", new JSArray());
            JSObject cfg = call.getObject("config", new JSObject());
            long agora = System.currentTimeMillis();
            JSONArray nova = new JSONArray();
            // alarmes de teste (compromisso 0) que ainda nao tocaram continuam valendo
            JSONArray antiga = Alarmes.lerArray(c, "lista");
            for (int i = 0; i < antiga.length(); i++) {
                JSONObject o = antiga.getJSONObject(i);
                if (o.optLong("apptId", -1) == 0 && o.optLong("at") > agora) nova.put(o);
            }
            for (int i = 0; i < arr.length(); i++) nova.put(arr.getJSONObject(i));
            Alarmes.gravarArray(c, "lista", nova);
            Alarmes.gravarConfig(c, cfg);
            Alarmes.reagendar(c);
            call.resolve();
        } catch (Exception e) {
            call.reject(String.valueOf(e.getMessage()));
        }
    }

    @PluginMethod
    public void testar(PluginCall call) {
        try {
            Context c = getContext();
            int seg = call.getData().optInt("segundos", 10);
            JSONObject o = new JSONObject();
            o.put("at", System.currentTimeMillis() + seg * 1000L);
            o.put("apptId", 0);
            o.put("titulo", "Agenda Arretada");
            o.put("corpo", "Teste do alarme: se voc\u00EA est\u00E1 ouvindo, est\u00E1 tudo certo!");
            o.put("voz", call.getString("voz", ""));
            JSONArray l = Alarmes.lerArray(c, "lista");
            l.put(o);
            Alarmes.gravarArray(c, "lista", l);
            Alarmes.reagendar(c);
            call.resolve();
        } catch (Exception e) {
            call.reject(String.valueOf(e.getMessage()));
        }
    }

    @PluginMethod
    public void salvarVoz(PluginCall call) {
        String id = call.getString("id");
        String dados = call.getString("dados");
        if (id == null || dados == null || !id.matches("[A-Za-z0-9_-]+")) {
            call.reject("dados invalidos");
            return;
        }
        try {
            byte[] b = Base64.decode(dados, Base64.DEFAULT);
            FileOutputStream f = new FileOutputStream(Alarmes.arquivoVoz(getContext(), id));
            try { f.write(b); } finally { f.close(); }
            call.resolve();
        } catch (Exception e) {
            call.reject(String.valueOf(e.getMessage()));
        }
    }

    @PluginMethod
    public void apagarVoz(PluginCall call) {
        String id = call.getString("id");
        if (id != null && id.matches("[A-Za-z0-9_-]+")) Alarmes.arquivoVoz(getContext(), id).delete();
        call.resolve();
    }

    @PluginMethod
    public void listarVozes(PluginCall call) {
        JSArray ids = new JSArray();
        File[] fs = getContext().getFilesDir().listFiles();
        if (fs != null) {
            for (File f : fs) {
                String n = f.getName();
                if (n.startsWith("voz_") && f.length() > 0) ids.put(n.substring(4));
            }
        }
        JSObject r = new JSObject();
        r.put("ids", ids);
        call.resolve(r);
    }

    @PluginMethod
    public void listarToques(PluginCall call) {
        JSArray out = new JSArray();
        Set<String> vistos = new HashSet<String>();
        int[] tipos = {RingtoneManager.TYPE_ALARM, RingtoneManager.TYPE_RINGTONE};
        for (int tipo : tipos) {
            try {
                RingtoneManager rm = new RingtoneManager(getContext());
                rm.setType(tipo);
                Cursor cur = rm.getCursor();
                while (cur.moveToNext()) {
                    String titulo = cur.getString(RingtoneManager.TITLE_COLUMN_INDEX);
                    String uri = rm.getRingtoneUri(cur.getPosition()).toString();
                    if (!vistos.add(uri)) continue;
                    JSObject t = new JSObject();
                    t.put("titulo", titulo);
                    t.put("uri", uri);
                    out.put(t);
                }
            } catch (Exception e) { }
        }
        JSObject r = new JSObject();
        r.put("toques", out);
        call.resolve(r);
    }

    @PluginMethod
    public void previaToque(PluginCall call) {
        try {
            pararPrevia();
            String s = call.getString("uri", "");
            int vol = call.getData().optInt("volume", 100);
            Uri uri = (s == null || s.isEmpty()) ? RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM) : Uri.parse(s);
            previa = new MediaPlayer();
            previa.setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build());
            previa.setDataSource(getContext(), uri);
            float v = Math.max(0.05f, Math.min(1f, vol / 100f));
            previa.setVolume(v, v);
            previa.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                public void onPrepared(MediaPlayer mp) { mp.start(); }
            });
            previa.prepareAsync();
            h.postDelayed(new Runnable() { public void run() { pararPrevia(); } }, 4000);
        } catch (Exception e) { }
        call.resolve();
    }

    private void pararPrevia() {
        h.removeCallbacksAndMessages(null);
        if (previa != null) {
            try { previa.stop(); } catch (Exception e) { }
            try { previa.release(); } catch (Exception e) { }
            previa = null;
        }
    }

    @PluginMethod
    public void pegarAcoes(PluginCall call) {
        Context c = getContext();
        JSONArray a = Alarmes.lerArray(c, "acoes");
        Alarmes.gravarArray(c, "acoes", new JSONArray());
        JSObject r = new JSObject();
        r.put("acoes", a);
        call.resolve(r);
    }

    /** Se o aviso deste compromisso esta tocando/na tela, para e limpa (usado ao concluir dentro do app). */
    @PluginMethod
    public void cancelarToque(PluginCall call) {
        try {
            Context c = getContext();
            long appt = call.getData().optLong("apptId", -1);
            long ativo = Alarmes.sp(c).getLong("ativo", -1);
            if (ativo == appt) {
                c.stopService(new Intent(c, AlarmeService.class));
                NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
                nm.cancel(AlarmeService.NOTIF);
                c.sendBroadcast(new Intent(AlarmeService.FECHAR).setPackage(c.getPackageName()));
                Alarmes.sp(c).edit().remove("ativo").apply();
            }
        } catch (Exception e) { }
        call.resolve();
    }

    @PluginMethod
    public void estado(PluginCall call) {
        Context c = getContext();
        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        boolean notif = true, tela = true, bateria = true;
        try { notif = nm.areNotificationsEnabled(); } catch (Exception e) { }
        try { if (Build.VERSION.SDK_INT >= 34) tela = nm.canUseFullScreenIntent(); } catch (Exception e) { }
        try {
            PowerManager pm = (PowerManager) c.getSystemService(Context.POWER_SERVICE);
            if (Build.VERSION.SDK_INT >= 23) bateria = pm.isIgnoringBatteryOptimizations(c.getPackageName());
        } catch (Exception e) { }
        JSObject r = new JSObject();
        r.put("notificacoes", notif);
        r.put("telaCheia", tela);
        r.put("bateria", bateria);
        call.resolve(r);
    }

    @PluginMethod
    public void abrir(PluginCall call) {
        Context c = getContext();
        String tipo = call.getString("tipo", "app");
        String pkg = c.getPackageName();
        Intent i;
        try {
            if ("bateria".equals(tipo)) {
                i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + pkg));
            } else if ("telaCheia".equals(tipo) && Build.VERSION.SDK_INT >= 34) {
                i = new Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:" + pkg));
            } else if ("notificacoes".equals(tipo)) {
                i = new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                i.putExtra(Settings.EXTRA_APP_PACKAGE, pkg);
            } else {
                i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + pkg));
            }
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            c.startActivity(i);
        } catch (Exception e) {
            try {
                Intent j = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + pkg));
                j.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                c.startActivity(j);
            } catch (Exception e2) { }
        }
        call.resolve();
    }
}
'''

ARQUIVOS["AlarmeReceiver.java"] = r'''package com.agendaarretada.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

/** Acorda no horario do alarme, entrega ao servico que toca a voz e o toque, e agenda o proximo. */
public class AlarmeReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent in) {
        try {
            long limite = System.currentTimeMillis() + 3000L;
            JSONArray l = Alarmes.lerArray(c, "lista");
            JSONArray resto = new JSONArray();
            JSONObject primeiro = null;
            int extra = 0;
            for (int i = 0; i < l.length(); i++) {
                JSONObject o = l.getJSONObject(i);
                if (o.optLong("at") <= limite) {
                    if (primeiro == null) primeiro = o; else extra++;
                } else {
                    resto.put(o);
                }
            }
            Alarmes.gravarArray(c, "lista", resto);
            if (primeiro != null) {
                Intent s = new Intent(c, AlarmeService.class);
                s.setAction(AlarmeService.ACAO_TOCAR);
                s.putExtra("json", primeiro.toString());
                s.putExtra("extra", extra);
                if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(s);
                else c.startService(s);
            }
        } catch (Exception e) { }
        Alarmes.reagendar(c);
    }
}
'''

ARQUIVOS["AlarmeService.java"] = r'''package com.agendaarretada.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.os.VibrationEffect;
import android.os.Vibrator;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;

/**
 * Toca primeiro a voz gravada e, quando ela termina, o toque escolhido.
 * Roda em primeiro plano para continuar mesmo com o app fechado.
 */
public class AlarmeService extends Service {
    public static final String ACAO_TOCAR = "com.agendaarretada.app.TOCAR";
    public static final String ACAO_CONCLUIR = "com.agendaarretada.app.CONCLUIR";
    public static final String ACAO_ADIAR = "com.agendaarretada.app.ADIAR";
    public static final String ACAO_PARAR_SOM = "com.agendaarretada.app.PARAR_SOM";
    public static final String FECHAR = "com.agendaarretada.app.FECHAR";
    static final String CANAL = "alarme_voz";
    static final int NOTIF = 4242;

    private MediaPlayer voz, toque;
    private Vibrator vib;
    private PowerManager.WakeLock wl;
    private final Handler h = new Handler(Looper.getMainLooper());
    private JSONObject atual = new JSONObject();
    private JSONObject cfg = new JSONObject();
    private int extra = 0, tocadas = 0;
    private float vol = 1f;
    private boolean comToque = true;

    @Override
    public IBinder onBind(Intent i) { return null; }

    @Override
    public int onStartCommand(Intent in, int flags, int startId) {
        String acao = in != null ? in.getAction() : null;
        if (ACAO_TOCAR.equals(acao)) {
            iniciar(in);
            return START_NOT_STICKY;
        }
        JSONObject o = lerJson(in);
        if (ACAO_CONCLUIR.equals(acao)) finalizar("concluir", o);
        else if (ACAO_ADIAR.equals(acao)) finalizar("adiar", o);
        else if (ACAO_PARAR_SOM.equals(acao)) silenciar();
        else stopSelf();
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        pararMidia();
        soltarWake();
        super.onDestroy();
    }

    private JSONObject lerJson(Intent in) {
        try {
            String s = in != null ? in.getStringExtra("json") : null;
            if (s != null) return new JSONObject(s);
        } catch (Exception e) { }
        return atual;
    }

    // ------------------------------------------------------------ inicio
    private void iniciar(Intent in) {
        JSONObject o;
        try { o = new JSONObject(in.getStringExtra("json")); } catch (Exception e) { o = new JSONObject(); }
        extra = in.getIntExtra("extra", 0);
        criarCanal();
        Notification n = montarNotif(o, extra, true);
        try {
            if (Build.VERSION.SDK_INT >= 29)
                startForeground(NOTIF, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            else
                startForeground(NOTIF, n);
        } catch (Exception e) { stopSelf(); return; }

        pararMidia();
        atual = o;
        cfg = Alarmes.config(this);
        tocadas = 0;
        Alarmes.sp(this).edit().putLong("ativo", o.optLong("apptId")).apply();

        try {
            vol = Math.max(0.05f, Math.min(1f, cfg.optInt("volume", 100) / 100f));
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (wl == null) wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "agenda:alarme");
            if (!wl.isHeld()) wl.acquire(10 * 60 * 1000L);
        } catch (Exception e) { }
        vibrar();

        String saida = cfg.optString("saida", "ambos");
        boolean querVoz = !"texto".equals(saida);
        comToque = !"voz".equals(saida);
        String vozId = o.optString("voz", "");
        File f = vozId.isEmpty() ? null : Alarmes.arquivoVoz(this, vozId);
        if (querVoz && f != null && f.exists() && f.length() > 0) {
            try { tocarVoz(f); }
            catch (Exception e) { liberarVoz(); comToque = true; tocarToque(); }
        } else {
            comToque = true; // sem voz disponivel: toca o toque
            tocarToque();
        }
        // seguranca: nunca toca mais de 10 minutos seguidos
        h.postDelayed(new Runnable() { public void run() { silenciar(); } }, 10 * 60 * 1000L);
    }

    private AudioAttributes atributos(int conteudo) {
        return new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(conteudo)
                .build();
    }

    private void tocarVoz(File f) throws Exception {
        voz = new MediaPlayer();
        voz.setAudioAttributes(atributos(AudioAttributes.CONTENT_TYPE_SPEECH));
        voz.setDataSource(f.getAbsolutePath());
        voz.setVolume(vol, vol);
        voz.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
            public void onCompletion(MediaPlayer mp) { liberarVoz(); depoisDaVoz(); }
        });
        voz.setOnErrorListener(new MediaPlayer.OnErrorListener() {
            public boolean onError(MediaPlayer mp, int w, int e) { liberarVoz(); depoisDaVoz(); return true; }
        });
        voz.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
            public void onPrepared(MediaPlayer mp) { mp.start(); }
        });
        voz.prepareAsync();
    }

    private void depoisDaVoz() {
        if (comToque) tocarToque(); else silenciar();
    }

    private void tocarToque() {
        try {
            liberarToque();
            Uri uri = null;
            String s = cfg.optString("toque", "");
            if (!s.isEmpty()) uri = Uri.parse(s);
            if (uri == null) uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (uri == null) uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            toque = new MediaPlayer();
            toque.setAudioAttributes(atributos(AudioAttributes.CONTENT_TYPE_SONIFICATION));
            try {
                toque.setDataSource(this, uri);
            } catch (Exception e) {
                toque.reset();
                toque.setAudioAttributes(atributos(AudioAttributes.CONTENT_TYPE_SONIFICATION));
                toque.setDataSource(this, RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM));
            }
            float inicio = cfg.optBoolean("crescente", true) ? vol * 0.15f : vol;
            toque.setVolume(inicio, inicio);
            toque.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                public void onCompletion(MediaPlayer mp) {
                    tocadas++;
                    int max = cfg.optInt("repeticoes", 10);
                    if (max == 0 || tocadas < max) {
                        try { mp.start(); } catch (Exception e) { silenciar(); }
                    } else {
                        silenciar();
                    }
                }
            });
            toque.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                public boolean onError(MediaPlayer mp, int w, int e) { silenciar(); return true; }
            });
            toque.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                public void onPrepared(MediaPlayer mp) { mp.start(); rampa(); }
            });
            toque.prepareAsync();
        } catch (Exception e) {
            silenciar();
        }
    }

    private void rampa() {
        if (!cfg.optBoolean("crescente", true)) return;
        final long ini = SystemClock.uptimeMillis();
        h.post(new Runnable() {
            public void run() {
                if (toque == null) return;
                float p = Math.min(1f, (SystemClock.uptimeMillis() - ini) / 12000f);
                float v = vol * (0.15f + 0.85f * p);
                try { toque.setVolume(v, v); } catch (Exception e) { return; }
                if (p < 1f) h.postDelayed(this, 500);
            }
        });
    }

    private void vibrar() {
        try {
            vib = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vib == null) return;
            long[] padrao = {0, 700, 700};
            if (Build.VERSION.SDK_INT >= 26)
                vib.vibrate(VibrationEffect.createWaveform(padrao, 0), atributos(AudioAttributes.CONTENT_TYPE_SONIFICATION));
            else
                vib.vibrate(padrao, 0);
        } catch (Exception e) { }
    }

    // ------------------------------------------------------------ parar
    private void liberarVoz() {
        if (voz != null) {
            try { voz.stop(); } catch (Exception e) { }
            try { voz.release(); } catch (Exception e) { }
            voz = null;
        }
    }

    private void liberarToque() {
        if (toque != null) {
            try { toque.stop(); } catch (Exception e) { }
            try { toque.release(); } catch (Exception e) { }
            toque = null;
        }
    }

    private void pararMidia() {
        h.removeCallbacksAndMessages(null);
        liberarVoz();
        liberarToque();
        if (vib != null) { try { vib.cancel(); } catch (Exception e) { } vib = null; }
    }

    private void soltarWake() {
        try { if (wl != null && wl.isHeld()) wl.release(); } catch (Exception e) { }
    }

    /** Para o som mas deixa a notificacao na tela com os botoes Concluir e Adiar. */
    private void silenciar() {
        pararMidia();
        soltarWake();
        try {
            stopForeground(false);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            nm.notify(NOTIF, montarNotif(atual, extra, false));
        } catch (Exception e) { }
        stopSelf();
    }

    private void finalizar(String acao, JSONObject o) {
        pararMidia();
        soltarWake();
        try {
            if (o == null) o = atual;
            long appt = o.optLong("apptId");
            long ate = 0;
            JSONArray lista = Alarmes.lerArray(this, "lista");
            if ("concluir".equals(acao)) {
                if (appt != 0) {
                    JSONArray n = new JSONArray();
                    for (int i = 0; i < lista.length(); i++) {
                        JSONObject x = lista.getJSONObject(i);
                        if (x.optLong("apptId") != appt) n.put(x);
                    }
                    Alarmes.gravarArray(this, "lista", n);
                }
            } else {
                ate = System.currentTimeMillis() + 5 * 60000L;
                JSONObject n = new JSONObject(o.toString());
                n.put("at", ate);
                lista.put(n);
                Alarmes.gravarArray(this, "lista", lista);
            }
            if (appt != 0) Alarmes.registrarAcao(this, acao, o, ate);
            Alarmes.sp(this).edit().remove("ativo").apply();
            Alarmes.reagendar(this);
        } catch (Exception e) { }
        try {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            nm.cancel(NOTIF);
        } catch (Exception e) { }
        sendBroadcast(new Intent(FECHAR).setPackage(getPackageName()));
        stopForeground(true);
        stopSelf();
        AlarmePlugin.emitir();
    }

    // ------------------------------------------------------------ notificacao
    private void criarCanal() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm.getNotificationChannel(CANAL) == null) {
            NotificationChannel ch = new NotificationChannel(CANAL, "Alarmes da agenda", NotificationManager.IMPORTANCE_HIGH);
            ch.setSound(null, null);
            ch.enableVibration(false);
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(ch);
        }
    }

    private PendingIntent botao(int codigo, String acao, JSONObject o) {
        Intent i = new Intent(this, AlarmeService.class);
        i.setAction(acao);
        i.putExtra("json", o.toString());
        return PendingIntent.getService(this, codigo, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private Notification montarNotif(JSONObject o, int outros, boolean tocando) {
        String titulo = o.optString("titulo", "Agenda Arretada");
        String corpo = o.optString("corpo", "");
        if (outros > 0) corpo += " (+" + outros + (outros > 1 ? " outros avisos)" : " outro aviso)");
        Intent ai = new Intent(this, AlarmeActivity.class);
        ai.putExtra("json", o.toString());
        ai.putExtra("extra", outros);
        ai.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent tela = PendingIntent.getActivity(this, 10, ai, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CANAL)
                : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle(titulo)
                .setContentText(corpo)
                .setStyle(new Notification.BigTextStyle().bigText(corpo))
                .setCategory(Notification.CATEGORY_ALARM)
                .setPriority(Notification.PRIORITY_MAX)
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setOngoing(tocando)
                .setAutoCancel(!tocando)
                .setContentIntent(tela)
                .addAction(0, "Concluir", botao(11, ACAO_CONCLUIR, o))
                .addAction(0, "Adiar 5 min", botao(12, ACAO_ADIAR, o));
        if (tocando) {
            b.setFullScreenIntent(tela, true);
            b.addAction(0, "Parar som", botao(13, ACAO_PARAR_SOM, o));
        }
        return b.build();
    }
}
'''

ARQUIVOS["Alarmes.java"] = r'''package com.agendaarretada.app;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;

/** Guarda a lista de alarmes no aparelho e agenda sempre o PROXIMO no AlarmManager. */
public class Alarmes {
    static final String PREFS = "agenda_alarmes";
    public static final String ACAO_DISPARAR = "com.agendaarretada.app.DISPARAR";

    static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static JSONArray lerArray(Context c, String chave) {
        try { return new JSONArray(sp(c).getString(chave, "[]")); }
        catch (Exception e) { return new JSONArray(); }
    }

    public static void gravarArray(Context c, String chave, JSONArray a) {
        sp(c).edit().putString(chave, a.toString()).apply();
    }

    public static JSONObject config(Context c) {
        try { return new JSONObject(sp(c).getString("config", "{}")); }
        catch (Exception e) { return new JSONObject(); }
    }

    public static void gravarConfig(Context c, JSONObject o) {
        sp(c).edit().putString("config", o.toString()).apply();
    }

    public static File arquivoVoz(Context c, String id) {
        return new File(c.getFilesDir(), "voz_" + id);
    }

    public static void registrarAcao(Context c, String acao, JSONObject alarme, long ate) {
        try {
            JSONArray a = lerArray(c, "acoes");
            JSONObject x = new JSONObject();
            x.put("acao", acao);
            x.put("apptId", alarme.optLong("apptId"));
            x.put("ate", ate);
            a.put(x);
            gravarArray(c, "acoes", a);
        } catch (Exception e) { }
    }

    public static void reagendar(Context c) {
        try {
            long agora = System.currentTimeMillis();
            JSONArray l = lerArray(c, "lista");
            JSONArray ok = new JSONArray();
            long prox = Long.MAX_VALUE;
            for (int i = 0; i < l.length(); i++) {
                JSONObject o = l.getJSONObject(i);
                long at = o.optLong("at");
                if (at < agora - 600000L) continue; // perdido ha mais de 10 min: descarta
                ok.put(o);
                if (at < prox) prox = at;
            }
            gravarArray(c, "lista", ok);

            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            Intent disparo = new Intent(c, AlarmeReceiver.class);
            disparo.setAction(ACAO_DISPARAR);
            PendingIntent pi = PendingIntent.getBroadcast(c, 1, disparo,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            if (prox == Long.MAX_VALUE) { am.cancel(pi); return; }

            long quando = Math.max(prox, agora + 1500L);
            PendingIntent mostrar = PendingIntent.getActivity(c, 2, new Intent(c, MainActivity.class),
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            am.setAlarmClock(new AlarmManager.AlarmClockInfo(quando, mostrar), pi);
        } catch (Exception e) { }
    }
}
'''

ARQUIVOS["BootReceiver.java"] = r'''package com.agendaarretada.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Depois que o celular reinicia (ou o horario muda), recoloca o proximo alarme. */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent in) {
        Alarmes.reagendar(c);
    }
}
'''

ARQUIVOS["MainActivity.java"] = r'''package com.agendaarretada.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AlarmePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
'''


def main():
    if not os.path.exists(MANIFEST):
        sys.exit("AndroidManifest.xml nao encontrado: rode 'npx cap add android' antes.")
    os.makedirs(DESTINO, exist_ok=True)
    for nome, texto in ARQUIVOS.items():
        with open(os.path.join(DESTINO, nome), "w", encoding="utf-8") as f:
            f.write(texto)
        print("escrito", nome)

    with open(MANIFEST, encoding="utf-8") as f:
        m = f.read()
    if "<application" not in m or "</application>" not in m:
        sys.exit("Manifest inesperado.")

    extra = ""
    for p in PERMISSOES:
        if "android.permission." + p + '"' not in m:
            extra += '    <uses-permission android:name="android.permission.%s" />\n' % p
    if "hardware.microphone" not in m:
        extra += '    <uses-feature android:name="android.hardware.microphone" android:required="false" />\n'
    if extra:
        m = m.replace("<application", extra + "    <application", 1)
    if "AlarmeService" not in m:
        m = m.replace("</application>", COMPONENTES + "    </application>", 1)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write(m)
    print("manifest atualizado")


main()
