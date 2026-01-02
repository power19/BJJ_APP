# Invictus BJJ Android App

A WebView-based Android app that connects to the Invictus BJJ web application.

## Features

- Full WebView integration with the web app
- NFC tag reading support for RFID check-ins
- Pull-to-refresh functionality
- Offline-aware with connection error handling
- Native splash screen

## Building the APK

### Prerequisites

1. Android Studio (latest version)
2. Java JDK 17+
3. Android SDK 34

### Steps

1. Open the `android` folder in Android Studio
2. Wait for Gradle sync to complete
3. Update the server URL in `app/build.gradle`:
   ```gradle
   buildConfigField "String", "SERVER_URL", "\"https://your-vps-url.com\""
   ```
4. Build → Generate Signed Bundle / APK
5. Select APK and follow the signing wizard

### Debug Build

```bash
cd android
./gradlew assembleDebug
```

The APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

### Release Build

```bash
cd android
./gradlew assembleRelease
```

## Configuration

### Server URL

Edit `app/build.gradle` and change the `SERVER_URL`:

```gradle
buildTypes {
    debug {
        buildConfigField "String", "SERVER_URL", "\"http://192.168.1.100:8000\""
    }
    release {
        buildConfigField "String", "SERVER_URL", "\"https://bjj.yourdomain.com\""
    }
}
```

### App Icon

Replace the launcher icons in:
- `app/src/main/res/mipmap-mdpi/ic_launcher.png` (48x48)
- `app/src/main/res/mipmap-hdpi/ic_launcher.png` (72x72)
- `app/src/main/res/mipmap-xhdpi/ic_launcher.png` (96x96)
- `app/src/main/res/mipmap-xxhdpi/ic_launcher.png` (144x144)
- `app/src/main/res/mipmap-xxxhdpi/ic_launcher.png` (192x192)

## NFC Integration

The app includes NFC support for RFID scanning. When an NFC tag is detected, the tag ID is passed to the web app via JavaScript:

```javascript
// In your web app, listen for NFC tags:
window.onNfcTag = function(tagId) {
    console.log('NFC Tag detected:', tagId);
    // Handle the tag ID (e.g., fill in RFID input)
    document.getElementById('rfidInput').value = tagId;
};
```

## JavaScript Interface

The app exposes native functionality to the web app:

```javascript
// Check if NFC is available
if (window.AndroidApp && window.AndroidApp.hasNfc()) {
    console.log('NFC is available');
}

// Show a native toast
window.AndroidApp.showToast('Hello from web!');
```
