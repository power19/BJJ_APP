# Proguard rules for Invictus BJJ App

# Keep WebView JavaScript interface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep BuildConfig
-keep class com.invictusbjj.app.BuildConfig { *; }

# Android support libraries
-keep class androidx.** { *; }
-keep interface androidx.** { *; }
