/**
 * ConnectionBadge — compact relationship/freshness indicator.
 */
import { View, Text, StyleSheet } from "react-native";

interface Props {
  score: number; // 0 to 1
  label?: string;
}

export function ConnectionBadge({ score, label }: Props) {
  const color =
    score > 0.7 ? "#10b981" : score > 0.3 ? "#f59e0b" : "#ef4444";
  const bg = color + "18";

  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={[styles.label, { color }]}>
        {label ?? `${Math.round(score * 100)}%`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  label: {
    fontSize: 11,
    fontWeight: "600",
  },
});
