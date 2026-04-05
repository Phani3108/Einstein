use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Note {
    pub id: String,
    pub file_path: String,
    pub title: String,
    pub content: String,
    pub frontmatter: HashMap<String, String>,
    pub outgoing_links: Vec<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultConfig {
    pub vault_path: String,
    pub db_path: String,
}

pub struct Vault {
    pub config: VaultConfig,
    db: Connection,
}

impl Vault {
    pub fn open(vault_path: &str) -> Result<Self, String> {
        let vault_dir = Path::new(vault_path);
        let einstein_dir = vault_dir.join(".einstein");
        fs::create_dir_all(&einstein_dir).map_err(|e| e.to_string())?;

        let db_path = einstein_dir.join("index.sqlite");
        let db = Connection::open(&db_path).map_err(|e| e.to_string())?;

        let config = VaultConfig {
            vault_path: vault_path.to_string(),
            db_path: db_path.to_string_lossy().to_string(),
        };

        let vault = Vault { config, db };
        vault.init_db()?;
        Ok(vault)
    }

    fn init_db(&self) -> Result<(), String> {
        self.db
            .execute_batch(
                "
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                frontmatter TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS links (
                id TEXT PRIMARY KEY,
                source_note_id TEXT NOT NULL,
                target_note_id TEXT,
                link_text TEXT NOT NULL,
                context TEXT DEFAULT '',
                link_type TEXT DEFAULT 'wikilink',
                is_resolved INTEGER DEFAULT 0,
                FOREIGN KEY (source_note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_note_id) REFERENCES notes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                context TEXT DEFAULT '',
                extracted_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title, content, file_path,
                content='notes',
                content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, title, content, file_path) VALUES (new.rowid, new.title, new.content, new.file_path);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, file_path) VALUES ('delete', old.rowid, old.title, old.content, old.file_path);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, file_path) VALUES ('delete', old.rowid, old.title, old.content, old.file_path);
                INSERT INTO notes_fts(rowid, title, content, file_path) VALUES (new.rowid, new.title, new.content, new.file_path);
            END;

            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                source TEXT DEFAULT 'inline',
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_id);
            CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);

            CREATE TABLE IF NOT EXISTS versions (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                content TEXT NOT NULL,
                frontmatter TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_versions_note ON versions(note_id);

            CREATE TABLE IF NOT EXISTS bookmarks (
                note_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                task TEXT NOT NULL,
                assignee TEXT,
                deadline TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_action_items_note ON action_items(note_id);
            CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(status);
            CREATE INDEX IF NOT EXISTS idx_action_items_deadline ON action_items(deadline);

            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_type TEXT DEFAULT 'deadline',
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_calendar_events_note ON calendar_events(note_id);
            CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON calendar_events(event_date);

            CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_note_id);
            CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_note_id);
            CREATE INDEX IF NOT EXISTS idx_entities_note ON entities(note_id);
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            ",
            )
            .map_err(|e| e.to_string())
    }

    pub fn list_notes(&self) -> Result<Vec<Note>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes ORDER BY updated_at DESC")
            .map_err(|e| e.to_string())?;

        let notes = stmt
            .query_map([], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        Ok(notes)
    }

    pub fn get_note(&self, id: &str) -> Result<Option<Note>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE id = ?1")
            .map_err(|e| e.to_string())?;

        let mut notes = stmt
            .query_map(params![id], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect::<Vec<_>>();

        Ok(notes.pop())
    }

    pub fn get_note_by_path(&self, file_path: &str) -> Result<Option<Note>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE file_path = ?1")
            .map_err(|e| e.to_string())?;

        let mut notes = stmt
            .query_map(params![file_path], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect::<Vec<_>>();

        Ok(notes.pop())
    }

    pub fn save_note(&self, file_path: &str, title: &str, content: &str, frontmatter: &HashMap<String, String>) -> Result<Note, String> {
        let now = chrono::Utc::now().to_rfc3339();
        let fm_json = serde_json::to_string(frontmatter).unwrap_or_default();

        // Check if note exists by file_path
        let existing = self.get_note_by_path(file_path)?;

        let note = if let Some(existing) = existing {
            // Save version history
            if existing.content != content {
                let version_id = uuid::Uuid::new_v4().to_string();
                let old_fm = serde_json::to_string(&existing.frontmatter).unwrap_or_default();
                let _ = self.db.execute(
                    "INSERT INTO versions (id, note_id, content, frontmatter, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                    params![version_id, existing.id, existing.content, old_fm, now],
                );
                let _ = self.db.execute(
                    "DELETE FROM versions WHERE note_id = ?1 AND id NOT IN (SELECT id FROM versions WHERE note_id = ?1 ORDER BY created_at DESC LIMIT 50)",
                    params![existing.id],
                );
            }

            self.db
                .execute(
                    "UPDATE notes SET title = ?1, content = ?2, frontmatter = ?3, updated_at = ?4 WHERE id = ?5",
                    params![title, content, fm_json, now, existing.id],
                )
                .map_err(|e| e.to_string())?;
            Note {
                id: existing.id,
                file_path: file_path.to_string(),
                title: title.to_string(),
                content: content.to_string(),
                frontmatter: frontmatter.clone(),
                outgoing_links: vec![],
                created_at: existing.created_at,
                updated_at: now,
            }
        } else {
            let id = uuid::Uuid::new_v4().to_string();
            self.db
                .execute(
                    "INSERT INTO notes (id, file_path, title, content, frontmatter, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                    params![id, file_path, title, content, fm_json, now, now],
                )
                .map_err(|e| e.to_string())?;
            Note {
                id,
                file_path: file_path.to_string(),
                title: title.to_string(),
                content: content.to_string(),
                frontmatter: frontmatter.clone(),
                outgoing_links: vec![],
                created_at: now.clone(),
                updated_at: now,
            }
        };

        // Write to disk
        let full_path = Path::new(&self.config.vault_path).join(file_path);
        if let Some(parent) = full_path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }

        let mut file_content = String::new();
        if !frontmatter.is_empty() {
            file_content.push_str("---\n");
            for (key, value) in frontmatter {
                file_content.push_str(&format!("{}: {}\n", key, value));
            }
            file_content.push_str("---\n\n");
        }
        file_content.push_str(content);

        fs::write(&full_path, &file_content).map_err(|e| e.to_string())?;

        // Parse and store links
        self.extract_and_store_links(&note.id, content)?;

        Ok(note)
    }

    pub fn delete_note(&self, id: &str) -> Result<(), String> {
        // Get file path before deleting from DB
        if let Some(note) = self.get_note(id)? {
            let full_path = Path::new(&self.config.vault_path).join(&note.file_path);
            if full_path.exists() {
                fs::remove_file(full_path).map_err(|e| e.to_string())?;
            }
        }
        self.db
            .execute("DELETE FROM notes WHERE id = ?1", params![id])
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn search_notes(&self, query: &str) -> Result<Vec<Note>, String> {
        let mut stmt = self
            .db
            .prepare(
                "SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
                 FROM notes_fts fts
                 JOIN notes n ON n.rowid = fts.rowid
                 WHERE notes_fts MATCH ?1
                 ORDER BY rank
                 LIMIT 50",
            )
            .map_err(|e| e.to_string())?;

        let notes = stmt
            .query_map(params![query], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        Ok(notes)
    }

    pub fn get_backlinks(&self, note_id: &str) -> Result<Vec<Note>, String> {
        let mut stmt = self
            .db
            .prepare(
                "SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
                 FROM links l
                 JOIN notes n ON n.id = l.source_note_id
                 WHERE l.target_note_id = ?1",
            )
            .map_err(|e| e.to_string())?;

        let notes = stmt
            .query_map(params![note_id], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        Ok(notes)
    }

    fn extract_and_store_links(&self, note_id: &str, content: &str) -> Result<(), String> {
        // Delete existing links for this note
        self.db
            .execute(
                "DELETE FROM links WHERE source_note_id = ?1",
                params![note_id],
            )
            .map_err(|e| e.to_string())?;

        // Parse [[wikilinks]] from content
        let re = regex_lite::Regex::new(r"\[\[([^\]]+)\]\]").unwrap();
        for cap in re.captures_iter(content) {
            let link_text = &cap[1];
            let link_id = uuid::Uuid::new_v4().to_string();

            // Try to resolve the link to an existing note
            let target_id = self.resolve_link(link_text)?;

            self.db
                .execute(
                    "INSERT INTO links (id, source_note_id, target_note_id, link_text, link_type, is_resolved) VALUES (?1, ?2, ?3, ?4, 'wikilink', ?5)",
                    params![link_id, note_id, target_id, link_text, target_id.is_some() as i32],
                )
                .map_err(|e| e.to_string())?;
        }

        // Delete existing tags for this note
        self.db
            .execute("DELETE FROM tags WHERE note_id = ?1", params![note_id])
            .map_err(|e| e.to_string())?;

        // Extract inline #tags from content
        let tag_re = regex_lite::Regex::new(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_-]*)").unwrap();
        for cap in tag_re.captures_iter(content) {
            let tag = &cap[1];
            let tag_id = uuid::Uuid::new_v4().to_string();
            self.db
                .execute(
                    "INSERT OR IGNORE INTO tags (id, note_id, tag, source) VALUES (?1, ?2, ?3, 'inline')",
                    params![tag_id, note_id, tag],
                )
                .map_err(|e| e.to_string())?;
        }

        Ok(())
    }

    fn resolve_link(&self, link_text: &str) -> Result<Option<String>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT id FROM notes WHERE title = ?1 OR file_path LIKE ?2 ESCAPE '\\' LIMIT 1")
            .map_err(|e| e.to_string())?;

        let escaped = link_text.replace('%', "\\%").replace('_', "\\_");
        let pattern = format!("%{}.md", escaped);
        let mut rows = stmt
            .query_map(params![link_text, pattern], |row| row.get::<_, String>(0))
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect::<Vec<_>>();

        Ok(rows.pop())
    }

    pub fn scan_vault(&self) -> Result<Vec<Note>, String> {
        let vault_path = Path::new(&self.config.vault_path);
        let mut notes = Vec::new();

        for entry in WalkDir::new(vault_path)
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path().extension().map_or(false, |ext| ext == "md")
                    && !e.path().starts_with(vault_path.join(".einstein"))
            })
        {
            let full_path = entry.path();
            let rel_path = full_path
                .strip_prefix(vault_path)
                .map_err(|e| e.to_string())?
                .to_string_lossy()
                .to_string();

            let raw = fs::read_to_string(full_path).map_err(|e| e.to_string())?;
            let (frontmatter, content) = parse_frontmatter(&raw);
            let title = derive_title(&content, &rel_path);

            let note = self.save_note(&rel_path, &title, &content, &frontmatter)?;
            notes.push(note);
        }

        Ok(notes)
    }

    pub fn get_graph_data(&self) -> Result<GraphData, String> {
        let notes = self.list_notes()?;
        let mut nodes: Vec<GraphNode> = notes
            .iter()
            .map(|n| GraphNode {
                id: n.id.clone(),
                label: n.title.clone(),
                node_type: "note".to_string(),
                file_path: Some(n.file_path.clone()),
            })
            .collect();

        // Add entity nodes
        let mut stmt = self
            .db
            .prepare("SELECT DISTINCT entity_type, entity_value FROM entities")
            .map_err(|e| e.to_string())?;
        let entities: Vec<(String, String)> = stmt
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        for (etype, evalue) in &entities {
            nodes.push(GraphNode {
                id: format!("entity_{}_{}", etype, evalue),
                label: evalue.clone(),
                node_type: etype.clone(),
                file_path: None,
            });
        }

        // Build edges from links
        let mut edges = Vec::new();
        let mut link_stmt = self
            .db
            .prepare("SELECT source_note_id, target_note_id, link_text FROM links WHERE is_resolved = 1")
            .map_err(|e| e.to_string())?;
        let links: Vec<(String, String, String)> = link_stmt
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        for (source, target, label) in links {
            edges.push(GraphEdge {
                source,
                target,
                label,
                edge_type: "wikilink".to_string(),
            });
        }

        // Edges from entities
        let mut entity_stmt = self
            .db
            .prepare("SELECT note_id, entity_type, entity_value FROM entities")
            .map_err(|e| e.to_string())?;
        let note_entities: Vec<(String, String, String)> = entity_stmt
            .query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        for (note_id, etype, evalue) in note_entities {
            edges.push(GraphEdge {
                source: note_id,
                target: format!("entity_{}_{}", etype, evalue),
                label: etype.clone(),
                edge_type: "entity".to_string(),
            });
        }

        Ok(GraphData { nodes, edges })
    }

    pub fn rename_note(&self, id: &str, new_title: &str, new_file_path: &str) -> Result<Note, String> {
        let old_note = self.get_note(id)?.ok_or("Note not found")?;
        let old_title = old_note.title.clone();
        let old_path_stem = Path::new(&old_note.file_path)
            .file_stem()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default();

        // Rename file on disk
        let old_full = Path::new(&self.config.vault_path).join(&old_note.file_path);
        let new_full = Path::new(&self.config.vault_path).join(new_file_path);
        if let Some(parent) = new_full.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        if old_full.exists() {
            fs::rename(&old_full, &new_full).map_err(|e| e.to_string())?;
        }

        // Update DB
        let now = chrono::Utc::now().to_rfc3339();
        self.db
            .execute(
                "UPDATE notes SET title = ?1, file_path = ?2, updated_at = ?3 WHERE id = ?4",
                params![new_title, new_file_path, now, id],
            )
            .map_err(|e| e.to_string())?;

        // Update all wikilinks across all notes
        let all_notes = self.list_notes()?;
        for note in &all_notes {
            if note.id == id { continue; }
            let mut updated = false;
            let mut new_content = note.content.clone();

            // Replace [[old_title]] with [[new_title]]
            let old_link = format!("[[{}]]", old_title);
            let new_link = format!("[[{}]]", new_title);
            if new_content.contains(&old_link) {
                new_content = new_content.replace(&old_link, &new_link);
                updated = true;
            }

            // Replace [[old_path_stem]] with [[new_title]]
            let old_path_link = format!("[[{}]]", old_path_stem);
            if new_content.contains(&old_path_link) {
                new_content = new_content.replace(&old_path_link, &new_link);
                updated = true;
            }

            if updated {
                self.save_note(&note.file_path, &note.title, &new_content, &note.frontmatter)?;
            }
        }

        self.get_note(id)?.ok_or("Note not found after rename".to_string())
    }

    pub fn get_note_versions(&self, note_id: &str) -> Result<Vec<NoteVersion>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT id, note_id, content, frontmatter, created_at FROM versions WHERE note_id = ?1 ORDER BY created_at DESC LIMIT 50")
            .map_err(|e| e.to_string())?;
        let versions = stmt
            .query_map(params![note_id], |row| {
                Ok(NoteVersion {
                    id: row.get(0)?,
                    note_id: row.get(1)?,
                    content: row.get(2)?,
                    frontmatter: row.get(3)?,
                    created_at: row.get(4)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();
        Ok(versions)
    }

    pub fn restore_version(&self, version_id: &str) -> Result<Note, String> {
        let mut stmt = self
            .db
            .prepare("SELECT note_id, content, frontmatter FROM versions WHERE id = ?1")
            .map_err(|e| e.to_string())?;
        let mut rows: Vec<(String, String, String)> = stmt
            .query_map(params![version_id], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();
        let (note_id, content, fm_json) = rows.pop().ok_or("Version not found")?;
        let note = self.get_note(&note_id)?.ok_or("Note not found")?;
        let frontmatter: HashMap<String, String> = serde_json::from_str(&fm_json).unwrap_or_default();
        self.save_note(&note.file_path, &note.title, &content, &frontmatter)
    }

    pub fn toggle_bookmark(&self, note_id: &str) -> Result<bool, String> {
        let exists: bool = self
            .db
            .query_row(
                "SELECT COUNT(*) FROM bookmarks WHERE note_id = ?1",
                params![note_id],
                |row| row.get::<_, i32>(0),
            )
            .map_err(|e| e.to_string())?
            > 0;

        if exists {
            self.db
                .execute("DELETE FROM bookmarks WHERE note_id = ?1", params![note_id])
                .map_err(|e| e.to_string())?;
            Ok(false)
        } else {
            let now = chrono::Utc::now().to_rfc3339();
            self.db
                .execute(
                    "INSERT INTO bookmarks (note_id, created_at) VALUES (?1, ?2)",
                    params![note_id, now],
                )
                .map_err(|e| e.to_string())?;
            Ok(true)
        }
    }

    pub fn list_bookmarks(&self) -> Result<Vec<Note>, String> {
        let mut stmt = self
            .db
            .prepare(
                "SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
                 FROM bookmarks b
                 JOIN notes n ON n.id = b.note_id
                 ORDER BY b.created_at DESC",
            )
            .map_err(|e| e.to_string())?;
        let notes = stmt
            .query_map([], |row| {
                let fm_str: String = row.get(4)?;
                let frontmatter: HashMap<String, String> =
                    serde_json::from_str(&fm_str).unwrap_or_default();
                Ok(Note {
                    id: row.get(0)?,
                    file_path: row.get(1)?,
                    title: row.get(2)?,
                    content: row.get(3)?,
                    frontmatter,
                    outgoing_links: vec![],
                    created_at: row.get(5)?,
                    updated_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();
        Ok(notes)
    }

    pub fn get_all_tags(&self) -> Result<Vec<TagInfo>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT tag, COUNT(*) as count FROM tags GROUP BY tag ORDER BY count DESC")
            .map_err(|e| e.to_string())?;
        let tags = stmt
            .query_map([], |row| {
                Ok(TagInfo {
                    tag: row.get(0)?,
                    count: row.get(1)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();
        Ok(tags)
    }

    pub fn get_config(&self, key: &str) -> Result<Option<String>, String> {
        let mut stmt = self
            .db
            .prepare("SELECT value FROM config WHERE key = ?1")
            .map_err(|e| e.to_string())?;
        let mut values: Vec<String> = stmt
            .query_map(params![key], |row| row.get(0))
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();
        Ok(values.pop())
    }

    pub fn set_config(&self, key: &str, value: &str) -> Result<(), String> {
        self.db
            .execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?1, ?2)",
                params![key, value],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn list_templates(&self) -> Result<Vec<TemplateInfo>, String> {
        let template_dir = Path::new(&self.config.vault_path).join("templates");
        let mut templates = Vec::new();
        if template_dir.exists() {
            for entry in WalkDir::new(&template_dir)
                .max_depth(1)
                .into_iter()
                .filter_map(|e| e.ok())
                .filter(|e| e.path().extension().map_or(false, |ext| ext == "md"))
            {
                let name = entry.path().file_stem()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default();
                let content = fs::read_to_string(entry.path()).unwrap_or_default();
                templates.push(TemplateInfo { name, content });
            }
        }
        Ok(templates)
    }

    pub fn create_from_template(&self, template_name: &str, note_title: &str) -> Result<Note, String> {
        let template_path = Path::new(&self.config.vault_path)
            .join("templates")
            .join(format!("{}.md", template_name));
        let template = fs::read_to_string(&template_path)
            .map_err(|_| format!("Template '{}' not found", template_name))?;

        let now = chrono::Local::now();
        let content = template
            .replace("{{title}}", note_title)
            .replace("{{date}}", &now.format("%Y-%m-%d").to_string())
            .replace("{{time}}", &now.format("%H:%M").to_string())
            .replace("{{day}}", &now.format("%A").to_string())
            .replace("{{datetime}}", &now.format("%Y-%m-%d %H:%M").to_string());

        let file_path = format!("{}.md", note_title.replace(' ', "-").to_lowercase());
        self.save_note(&file_path, note_title, &content, &HashMap::new())
    }

    pub fn merge_notes(&self, ids: &[String], new_title: &str) -> Result<Note, String> {
        let mut combined_content = format!("# {}\n\n", new_title);
        let mut combined_fm = HashMap::new();

        for id in ids {
            if let Some(note) = self.get_note(id)? {
                combined_content.push_str(&format!("## {}\n\n{}\n\n---\n\n", note.title, note.content));
                for (k, v) in &note.frontmatter {
                    if k != "entities" {
                        combined_fm.insert(k.clone(), v.clone());
                    }
                }
            }
        }
        combined_fm.insert("merged_from".to_string(), ids.join(","));

        let file_path = format!("{}.md", new_title.replace(' ', "-").to_lowercase());
        self.save_note(&file_path, new_title, &combined_content, &combined_fm)
    }

    // --- Action Items ---

    pub fn save_action_items(&self, note_id: &str, items: &[ActionItem]) -> Result<(), String> {
        // Delete existing action items for this note, then insert new ones
        self.db
            .execute("DELETE FROM action_items WHERE note_id = ?1", params![note_id])
            .map_err(|e| e.to_string())?;

        for item in items {
            self.db
                .execute(
                    "INSERT INTO action_items (id, note_id, task, assignee, deadline, priority, status, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                    params![item.id, note_id, item.task, item.assignee, item.deadline, item.priority, item.status, item.created_at],
                )
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }

    pub fn get_action_items(&self, note_id: Option<&str>, status: Option<&str>) -> Result<Vec<ActionItem>, String> {
        let mut query = "SELECT id, note_id, task, assignee, deadline, priority, status, created_at FROM action_items".to_string();
        let mut conditions = Vec::new();
        if note_id.is_some() { conditions.push("note_id = ?1"); }
        if status.is_some() { conditions.push(if note_id.is_some() { "status = ?2" } else { "status = ?1" }); }
        if !conditions.is_empty() {
            query.push_str(" WHERE ");
            query.push_str(&conditions.join(" AND "));
        }
        query.push_str(" ORDER BY deadline ASC NULLS LAST");

        let mut stmt = self.db.prepare(&query).map_err(|e| e.to_string())?;

        let items: Vec<ActionItem> = match (note_id, status) {
            (Some(nid), Some(st)) => {
                stmt.query_map(params![nid, st], |row| {
                    Ok(ActionItem {
                        id: row.get(0)?, note_id: row.get(1)?, task: row.get(2)?,
                        assignee: row.get(3)?, deadline: row.get(4)?, priority: row.get(5)?,
                        status: row.get(6)?, created_at: row.get(7)?,
                    })
                }).map_err(|e| e.to_string())?
                .filter_map(|r| r.ok()).collect()
            },
            (Some(nid), None) => {
                stmt.query_map(params![nid], |row| {
                    Ok(ActionItem {
                        id: row.get(0)?, note_id: row.get(1)?, task: row.get(2)?,
                        assignee: row.get(3)?, deadline: row.get(4)?, priority: row.get(5)?,
                        status: row.get(6)?, created_at: row.get(7)?,
                    })
                }).map_err(|e| e.to_string())?
                .filter_map(|r| r.ok()).collect()
            },
            (None, Some(st)) => {
                stmt.query_map(params![st], |row| {
                    Ok(ActionItem {
                        id: row.get(0)?, note_id: row.get(1)?, task: row.get(2)?,
                        assignee: row.get(3)?, deadline: row.get(4)?, priority: row.get(5)?,
                        status: row.get(6)?, created_at: row.get(7)?,
                    })
                }).map_err(|e| e.to_string())?
                .filter_map(|r| r.ok()).collect()
            },
            (None, None) => {
                stmt.query_map([], |row| {
                    Ok(ActionItem {
                        id: row.get(0)?, note_id: row.get(1)?, task: row.get(2)?,
                        assignee: row.get(3)?, deadline: row.get(4)?, priority: row.get(5)?,
                        status: row.get(6)?, created_at: row.get(7)?,
                    })
                }).map_err(|e| e.to_string())?
                .filter_map(|r| r.ok()).collect()
            },
        };
        Ok(items)
    }

    pub fn update_action_status(&self, id: &str, status: &str) -> Result<(), String> {
        self.db
            .execute(
                "UPDATE action_items SET status = ?1 WHERE id = ?2",
                params![status, id],
            )
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Calendar Events ---

    pub fn save_calendar_events(&self, note_id: &str, events: &[CalendarEvent]) -> Result<(), String> {
        self.db
            .execute("DELETE FROM calendar_events WHERE note_id = ?1", params![note_id])
            .map_err(|e| e.to_string())?;

        for event in events {
            self.db
                .execute(
                    "INSERT INTO calendar_events (id, note_id, title, event_date, event_type, description, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                    params![event.id, note_id, event.title, event.event_date, event.event_type, event.description, event.created_at],
                )
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }

    pub fn get_calendar_events(&self, start_date: &str, end_date: &str) -> Result<Vec<CalendarEvent>, String> {
        let mut stmt = self.db
            .prepare("SELECT id, note_id, title, event_date, event_type, description, created_at FROM calendar_events WHERE event_date >= ?1 AND event_date <= ?2 ORDER BY event_date ASC")
            .map_err(|e| e.to_string())?;

        let events = stmt
            .query_map(params![start_date, end_date], |row| {
                Ok(CalendarEvent {
                    id: row.get(0)?,
                    note_id: row.get(1)?,
                    title: row.get(2)?,
                    event_date: row.get(3)?,
                    event_type: row.get(4)?,
                    description: row.get(5)?,
                    created_at: row.get(6)?,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        Ok(events)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub node_type: String,
    pub file_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source: String,
    pub target: String,
    pub label: String,
    pub edge_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionItem {
    pub id: String,
    pub note_id: String,
    pub task: String,
    pub assignee: Option<String>,
    pub deadline: Option<String>,
    pub priority: String,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalendarEvent {
    pub id: String,
    pub note_id: String,
    pub title: String,
    pub event_date: String,
    pub event_type: String,
    pub description: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphData {
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteVersion {
    pub id: String,
    pub note_id: String,
    pub content: String,
    pub frontmatter: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TagInfo {
    pub tag: String,
    pub count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateInfo {
    pub name: String,
    pub content: String,
}

fn parse_frontmatter(raw: &str) -> (HashMap<String, String>, String) {
    let mut frontmatter = HashMap::new();
    let content;

    if raw.starts_with("---") {
        if let Some(end) = raw[3..].find("---") {
            let fm_end = 3 + end + 3;
            if fm_end <= raw.len() {
                let fm_block = raw[3..3 + end].trim();
                content = raw[fm_end..].trim().to_string();

                for line in fm_block.lines() {
                    if let Some((key, value)) = line.split_once(':') {
                        frontmatter.insert(key.trim().to_string(), value.trim().to_string());
                    }
                }
            } else {
                content = raw.to_string();
            }
        } else {
            content = raw.to_string();
        }
    } else {
        content = raw.to_string();
    }

    (frontmatter, content)
}

fn derive_title(content: &str, file_path: &str) -> String {
    // Try H1 heading
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("# ") {
            return trimmed[2..].trim().to_string();
        }
    }
    // Fall back to filename
    Path::new(file_path)
        .file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "Untitled".to_string())
}
