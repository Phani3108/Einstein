mod vault;

use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::Mutex;
use tauri::State;
use vault::{ActionItem, CalendarEvent, GraphData, Note, NoteVersion, TagInfo, TemplateInfo, Vault};

struct VaultState(Mutex<Option<Vault>>);

macro_rules! lock_vault {
    ($state:expr) => {
        $state.0.lock().map_err(|_| "Vault state corrupted".to_string())?
    };
}

#[tauri::command]
fn open_vault(path: String, state: State<VaultState>) -> Result<Vec<Note>, String> {
    let vault = Vault::open(&path)?;
    let notes = vault.scan_vault()?;
    *lock_vault!(state) = Some(vault);
    Ok(notes)
}

#[tauri::command]
fn list_notes(state: State<VaultState>) -> Result<Vec<Note>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.list_notes()
}

#[tauri::command]
fn get_note(id: String, state: State<VaultState>) -> Result<Option<Note>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_note(&id)
}

#[tauri::command]
fn save_note(
    file_path: String,
    title: String,
    content: String,
    frontmatter: HashMap<String, String>,
    state: State<VaultState>,
) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.save_note(&file_path, &title, &content, &frontmatter)
}

#[tauri::command]
fn delete_note(id: String, state: State<VaultState>) -> Result<(), String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.delete_note(&id)
}

#[tauri::command]
fn search_notes(query: String, state: State<VaultState>) -> Result<Vec<Note>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.search_notes(&query)
}

#[tauri::command]
fn get_backlinks(note_id: String, state: State<VaultState>) -> Result<Vec<Note>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_backlinks(&note_id)
}

#[tauri::command]
fn get_graph_data(state: State<VaultState>) -> Result<GraphData, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_graph_data()
}

#[tauri::command]
fn create_daily_note(state: State<VaultState>) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    let now = chrono::Local::now();
    let today = now.format("%Y-%m-%d").to_string();
    let day_name = now.format("%A").to_string();
    let file_path = format!("daily/{}.md", today);
    let title = today.clone();

    // Return existing if already created today
    if let Some(existing) = vault.get_note_by_path(&file_path)? {
        return Ok(existing);
    }

    // Check for custom template
    let template_path = Path::new(&vault.config.vault_path)
        .join("templates")
        .join("daily.md");
    let content = if let Ok(template) = fs::read_to_string(&template_path) {
        template
            .replace("{{date}}", &today)
            .replace("{{day}}", &day_name)
            .replace("{{time}}", &now.format("%H:%M").to_string())
    } else {
        format!(
            "# {today}\n\n## Journal\n\n\n\n## Tasks\n\n- [ ] \n\n## Notes\n\n\n",
        )
    };

    // Link to yesterday's note
    let yesterday = (now - chrono::Duration::days(1)).format("%Y-%m-%d").to_string();
    let mut frontmatter = HashMap::new();
    frontmatter.insert("date".to_string(), today.clone());
    frontmatter.insert("type".to_string(), "daily".to_string());
    frontmatter.insert("day".to_string(), day_name);
    frontmatter.insert("previous".to_string(), format!("[[daily/{}]]", yesterday));

    vault.save_note(&file_path, &title, &content, &frontmatter)
}

#[tauri::command]
fn rename_note(id: String, new_title: String, new_file_path: String, state: State<VaultState>) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.rename_note(&id, &new_title, &new_file_path)
}

#[tauri::command]
fn get_note_versions(note_id: String, state: State<VaultState>) -> Result<Vec<NoteVersion>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_note_versions(&note_id)
}

#[tauri::command]
fn restore_version(version_id: String, state: State<VaultState>) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.restore_version(&version_id)
}

#[tauri::command]
fn toggle_bookmark(note_id: String, state: State<VaultState>) -> Result<bool, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.toggle_bookmark(&note_id)
}

#[tauri::command]
fn list_bookmarks(state: State<VaultState>) -> Result<Vec<Note>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.list_bookmarks()
}

#[tauri::command]
fn get_all_tags(state: State<VaultState>) -> Result<Vec<TagInfo>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_all_tags()
}

#[tauri::command]
fn get_config(key: String, state: State<VaultState>) -> Result<Option<String>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_config(&key)
}

#[tauri::command]
fn set_config(key: String, value: String, state: State<VaultState>) -> Result<(), String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.set_config(&key, &value)
}

#[tauri::command]
fn list_templates(state: State<VaultState>) -> Result<Vec<TemplateInfo>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.list_templates()
}

#[tauri::command]
fn create_from_template(template_name: String, note_title: String, state: State<VaultState>) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.create_from_template(&template_name, &note_title)
}

#[tauri::command]
fn merge_notes(ids: Vec<String>, new_title: String, state: State<VaultState>) -> Result<Note, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.merge_notes(&ids, &new_title)
}

// --- Action Items ---

#[tauri::command]
fn save_action_items(note_id: String, items: Vec<ActionItem>, state: State<VaultState>) -> Result<(), String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.save_action_items(&note_id, &items)
}

#[tauri::command]
fn get_action_items(note_id: Option<String>, status: Option<String>, state: State<VaultState>) -> Result<Vec<ActionItem>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_action_items(note_id.as_deref(), status.as_deref())
}

#[tauri::command]
fn update_action_status(id: String, status: String, state: State<VaultState>) -> Result<(), String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.update_action_status(&id, &status)
}

// --- Calendar Events ---

#[tauri::command]
fn save_calendar_events(note_id: String, events: Vec<CalendarEvent>, state: State<VaultState>) -> Result<(), String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.save_calendar_events(&note_id, &events)
}

#[tauri::command]
fn get_calendar_events(start_date: String, end_date: String, state: State<VaultState>) -> Result<Vec<CalendarEvent>, String> {
    let guard = lock_vault!(state);
    let vault = guard.as_ref().ok_or("No vault open")?;
    vault.get_calendar_events(&start_date, &end_date)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(VaultState(Mutex::new(None)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            open_vault,
            list_notes,
            get_note,
            save_note,
            delete_note,
            search_notes,
            get_backlinks,
            get_graph_data,
            create_daily_note,
            rename_note,
            get_note_versions,
            restore_version,
            toggle_bookmark,
            list_bookmarks,
            get_all_tags,
            get_config,
            set_config,
            list_templates,
            create_from_template,
            merge_notes,
            save_action_items,
            get_action_items,
            update_action_status,
            save_calendar_events,
            get_calendar_events,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
