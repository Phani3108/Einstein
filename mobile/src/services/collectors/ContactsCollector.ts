/**
 * ContactsCollector — syncs device contacts to People records.
 *
 * - Runs on launch + hourly.
 * - Creates/updates PersonProfile entries via the cloud API.
 * - Does NOT create ContextEvents — contacts are reference data, not events.
 */
import * as Contacts from "expo-contacts";
import { useStore } from "../../store/useStore";
import type { Person } from "../../store/types";

const BATCH_SIZE = 100;

export async function collectContacts(): Promise<number> {
  const { status } = await Contacts.requestPermissionsAsync();
  if (status !== "granted") {
    console.warn("[ContactsCollector] Permission denied");
    return 0;
  }

  const { data } = await Contacts.getContactsAsync({
    fields: [
      Contacts.Fields.Name,
      Contacts.Fields.PhoneNumbers,
      Contacts.Fields.Emails,
      Contacts.Fields.Company,
      Contacts.Fields.JobTitle,
    ],
    sort: Contacts.SortTypes.LastName,
  });

  if (!data || data.length === 0) return 0;

  const store = useStore.getState();
  const existingNames = new Set(store.people.map((p) => p.name.toLowerCase()));

  let synced = 0;
  for (const contact of data) {
    if (!contact.name || contact.name.trim().length < 2) continue;

    const name = contact.name.trim();
    const phone =
      contact.phoneNumbers?.[0]?.number ?? null;
    const email =
      contact.emails?.[0]?.email ?? null;
    const organization = contact.company ?? null;
    const role = contact.jobTitle ?? null;

    // Skip if we already have this person (by name match)
    if (existingNames.has(name.toLowerCase())) continue;

    const person: Person = {
      id: `contact_${contact.id}`,
      name,
      aliases: [],
      phone,
      email,
      role,
      organization,
      last_seen: null,
      interaction_count: 0,
      freshness_score: 0.5,
    };

    store.upsertPerson(person);
    existingNames.add(name.toLowerCase());
    synced++;
  }

  console.log(`[ContactsCollector] Synced ${synced} new contacts`);
  return synced;
}
