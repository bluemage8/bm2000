package com.bm2000.bridge

import android.annotation.SuppressLint
import android.content.res.AssetManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import java.io.ByteArrayInputStream

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        hideSystemUi()

        webView = WebView(this)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_NO_CACHE
            allowFileAccess = true
            mediaPlaybackRequiresUserGesture = false
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            }
        }
        webView.settings.setSupportZoom(false)
        webView.setBackgroundColor(0xFF0B5D2E.toInt())
        // MI 5X / Android 7.1: force an explicit hardware layer so the WebView
        // compositor does not fall back to a broken EGL path (EGL_BAD_DISPLAY).
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null)

        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                val url = request.url.toString()
                // serve the deal table from assets (mirrors the python server's /api/deals)
                if (url.endsWith("/api/deals") || url.endsWith("/api/deals/")) {
                    return assetResponse("deals.json", "application/json; charset=utf-8")
                }
                // also allow direct fetch of deals.json if referenced
                if (url.endsWith("/deals.json")) {
                    return assetResponse("deals.json", "application/json; charset=utf-8")
                }
                return null
            }
            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                android.util.Log.i("BM2000", "pageFinished=" + url)
                // nudge a redraw in case the first composite frame was dropped
                view.postDelayed({ view.invalidate() }, 300)
                // ask JS to export the live stage as a PNG (MI 5X screencap
                // can't capture the WebView layer, so this is our only view).
                view.postDelayed({
                    try {
                        view.evaluateJavascript("window.__dumpGeom && window.__dumpGeom()", null)
                        view.evaluateJavascript("window.__exportStagePNG && window.__exportStagePNG()", null)
                        view.evaluateJavascript("window.__exportBoard && window.__exportBoard()", null)
                        android.util.Log.i("BM2000", "diag requested")
                    } catch (e: Exception) {
                        android.util.Log.e("BM2000", "diag failed: " + e)
                    }
                }, 4000)
            }
        }

        // JS bridge fallback: window.AndroidBridge.getDeals() -> replies via window.__onDeals(json)
        webView.addJavascriptInterface(DealBridge(assets), "AndroidBridge")

        // log the page title -- app.js sets it to "BM2000_OK deals=N lv=M" once the
        // deal table is loaded, so we can confirm data load via logcat.
        webView.webChromeClient = object : android.webkit.WebChromeClient() {
            override fun onReceivedTitle(view: WebView, title: String) {
                if (title != null && title.isNotEmpty()) {
                    android.util.Log.i("BM2000", "title=" + title)
                }
            }
        }

        setContentView(webView)
        webView.loadUrl("file:///android_asset/index.html")
    }

    inner class DealBridge(private val am: AssetManager) {
        @JavascriptInterface
        fun getDeals() {
            val json = try {
                am.open("deals.json").bufferedReader().use { it.readText() }
            } catch (e: Exception) {
                "null"
            }
            // run on the UI thread so the page is ready to receive the callback
            webView.post {
                try {
                    webView.evaluateJavascript("window.__onDeals && window.__onDeals(${json.replace("\\", "\\\\").replace("\n", "\\n")})", null)
                } catch (ignored: Exception) {}
            }
        }

        // JS sends the rendered stage as a base64 PNG; we persist it to
        // /sdcard so it can be pulled off the device and inspected.
        @JavascriptInterface
        fun savePng(b64: String?) {
            if (b64.isNullOrEmpty()) {
                android.util.Log.w("BM2000", "savePng: empty")
                return
            }
            try {
                // android.util.Base64 works on minSdk 24 (java.util.Base64 is 26+)
                val bytes = android.util.Base64.decode(b64, android.util.Base64.DEFAULT)
                // getExternalFilesDir needs no runtime permission (API 19+)
                val dir = getExternalFilesDir(null) ?: filesDir
                val f = java.io.File(dir, "bm2000_stage.png")
                java.io.FileOutputStream(f).use { it.write(bytes) }
                android.util.Log.i("BM2000", "savePng: wrote " + bytes.size + " bytes to " + f.absolutePath)
            } catch (e: Exception) {
                android.util.Log.e("BM2000", "savePng failed: " + e)
            }
        }
    }

    private fun assetResponse(assetPath: String, mime: String): WebResourceResponse? {
        val am: AssetManager = assets
        return try {
            val input = am.open(assetPath)
            WebResourceResponse(mime, "UTF-8", 200, "OK", emptyMap(), input)
        } catch (e: Exception) {
            WebResourceResponse("text/plain", "UTF-8", 404, "Not found", emptyMap(),
                ByteArrayInputStream("not found".toByteArray()))
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
        hideSystemUi()
    }

    override fun onPause() {
        webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }

    @Suppress("DEPRECATION")
    private fun hideSystemUi() {
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            )
    }
}
