package com.einstein.notifications

import android.content.ComponentName
import android.content.Intent
import android.provider.Settings
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

/**
 * React Native bridge for the NotificationListenerService.
 * Exposes permission checking and settings navigation to JS.
 */
class NotificationModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    init {
        NotificationService.reactContext = reactContext
    }

    override fun getName(): String = "EinsteinNotifications"

    /**
     * Check if the notification listener permission is granted.
     */
    @ReactMethod
    fun isPermissionGranted(promise: Promise) {
        try {
            val cn = ComponentName(reactContext, NotificationService::class.java)
            val flat = Settings.Secure.getString(
                reactContext.contentResolver,
                "enabled_notification_listeners"
            )
            val granted = flat != null && flat.contains(cn.flattenToString())
            promise.resolve(granted)
        } catch (e: Exception) {
            promise.reject("PERMISSION_CHECK_FAILED", e.message)
        }
    }

    /**
     * Open the system notification listener settings screen.
     */
    @ReactMethod
    fun openSettings() {
        try {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            reactContext.startActivity(intent)
        } catch (e: Exception) {
            // Fallback to general settings
            val intent = Intent(Settings.ACTION_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            reactContext.startActivity(intent)
        }
    }
}
