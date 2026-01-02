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

# SecurityConfig - keep the public methods but obfuscate internals
-keep class com.invictusbjj.app.SecurityConfig {
    public static java.lang.String getServerUrl();
    public static boolean verifyUrl(java.lang.String);
}

# Obfuscate all private methods in SecurityConfig
-keepclassmembernames class com.invictusbjj.app.SecurityConfig {
    private static *** *(...);
}

# Optimize and obfuscate aggressively
-optimizationpasses 5
-allowaccessmodification
-repackageclasses ''

# Remove logging in release builds
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}
