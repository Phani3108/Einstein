package com.einstein.notifications

import android.content.Intent
import android.os.IBinder
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.modules.core.DeviceEventManagerModule

/**
 * Android NotificationListenerService that captures incoming notifications
 * and forwards them to React Native via NativeEventEmitter.
 *
 * Requires the user to grant "Notification Access" in system settings.
 */
class NotificationService : NotificationListenerService() {

    companion object {
        var reactContext: ReactApplicationContext? = null
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val notification = sbn.notification ?: return
        val extras = notification.extras ?: return

        val packageName = sbn.packageName ?: return
        val title = extras.getCharSequence("android.title")?.toString() ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""

        // Skip empty notifications
        if (title.isBlank() && text.isBlank()) return

        // Get app name
        val appName = try {
            val pm = applicationContext.packageManager
            val appInfo = pm.getApplicationInfo(packageName, 0)
            pm.getApplicationLabel(appInfo).toString()
        } catch (e: Exception) {
            packageName
        }

        // Send to React Native
        val params = Arguments.createMap().apply {
            putString("packageName", packageName)
            putString("appName", appName)
            putString("title", title)
            putString("text", text)
            putDouble("timestamp", sbn.postTime.toDouble())
            putString("key", sbn.key ?: "${packageName}_${sbn.postTime}")
        }

        reactContext?.let { context ->
            context
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                ?.emit("onNotificationReceived", params)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        // Not needed for capture
    }
}
