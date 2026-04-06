/**
 * Collector barrel export — run all collectors in one call.
 */
export { collectCalendarEvents } from "./CalendarCollector";
export { collectContacts } from "./ContactsCollector";
export { collectCallLog } from "./CallLogCollector";
export {
  startNotificationCapture,
  stopNotificationCapture,
  isPermissionGranted,
  openPermissionSettings,
} from "./NotificationCollector";

import { collectCalendarEvents } from "./CalendarCollector";
import { collectContacts } from "./ContactsCollector";
import { collectCallLog } from "./CallLogCollector";

/**
 * Run all data collectors. Returns counts per source.
 */
export async function collectAll(): Promise<{
  contacts: number;
  calendar: number;
  calls: number;
}> {
  const [contacts, calendar, calls] = await Promise.allSettled([
    collectContacts(),
    collectCalendarEvents(),
    collectCallLog(),
  ]);

  return {
    contacts: contacts.status === "fulfilled" ? contacts.value : 0,
    calendar: calendar.status === "fulfilled" ? calendar.value : 0,
    calls: calls.status === "fulfilled" ? calls.value : 0,
  };
}
