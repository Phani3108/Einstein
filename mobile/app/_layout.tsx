/**
 * Root layout — tab navigator with 5 screens.
 */
import { useEffect } from "react";
import { Tabs } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Ionicons } from "@expo/vector-icons";
import { registerBackgroundSync } from "../src/services/sync";

type TabIcon = React.ComponentProps<typeof Ionicons>["name"];

const TAB_CONFIG: { name: string; title: string; icon: TabIcon; iconFocused: TabIcon }[] = [
  { name: "index", title: "Home", icon: "home-outline", iconFocused: "home" },
  { name: "timeline", title: "Timeline", icon: "time-outline", iconFocused: "time" },
  { name: "people", title: "People", icon: "people-outline", iconFocused: "people" },
  { name: "inbox", title: "Inbox", icon: "add-circle-outline", iconFocused: "add-circle" },
  { name: "settings", title: "Settings", icon: "settings-outline", iconFocused: "settings" },
];

export default function RootLayout() {
  useEffect(() => {
    registerBackgroundSync().catch(console.warn);
  }, []);

  return (
    <>
      <StatusBar style="light" />
      <Tabs
        screenOptions={{
          headerStyle: { backgroundColor: "#0a0a0f" },
          headerTintColor: "#e4e4e7",
          tabBarStyle: {
            backgroundColor: "#0a0a0f",
            borderTopColor: "#27272a",
          },
          tabBarActiveTintColor: "#3b82f6",
          tabBarInactiveTintColor: "#71717a",
        }}
      >
        {TAB_CONFIG.map((tab) => (
          <Tabs.Screen
            key={tab.name}
            name={tab.name}
            options={{
              title: tab.title,
              tabBarIcon: ({ focused, color, size }) => (
                <Ionicons
                  name={focused ? tab.iconFocused : tab.icon}
                  size={size}
                  color={color}
                />
              ),
            }}
          />
        ))}
        {/* Non-tab screens — accessible via router.push but hidden from the tab bar */}
        <Tabs.Screen
          name="integrations"
          options={{
            title: "Integrations",
            href: null, // hide from tab bar
          }}
        />
      </Tabs>
    </>
  );
}
