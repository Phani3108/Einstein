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

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                category TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                deadline TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT DEFAULT '',
                organization TEXT DEFAULT '',
                email TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                last_contact TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                reasoning TEXT DEFAULT '',
                alternatives TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                decided_at TEXT DEFAULT (datetime('now')),
                revisit_date TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);

            CREATE TABLE IF NOT EXISTS note_associations (
                id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                relationship TEXT DEFAULT 'mentions',
                confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(note_id, object_type, object_id)
            );
            CREATE INDEX IF NOT EXISTS idx_assoc_note ON note_associations(note_id);
            CREATE INDEX IF NOT EXISTS idx_assoc_object ON note_associations(object_type, object_id);

            CREATE TABLE IF NOT EXISTS note_metadata (
                note_id TEXT PRIMARY KEY,
                lifecycle TEXT DEFAULT 'active',
                last_meaningful_edit TEXT,
                view_count INTEGER DEFAULT 0,
                importance_score REAL DEFAULT 0.5,
                distilled_at TEXT,
                source_type TEXT DEFAULT 'manual'
            );
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

    // --- Projects ---

    pub fn create_project(&self, title: &str, description: &str, category: &str, goal: &str, deadline: Option<&str>) -> Result<Project, String> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = chrono::Utc::now().to_rfc3339();
        self.db.execute(
            "INSERT INTO projects (id, title, description, status, category, goal, deadline, created_at, updated_at) VALUES (?1, ?2, ?3, 'active', ?4, ?5, ?6, ?7, ?8)",
            params![id, title, description, category, goal, deadline, now, now],
        ).map_err(|e| e.to_string())?;
        Ok(Project { id, title: title.to_string(), description: description.to_string(), status: "active".to_string(), category: category.to_string(), goal: goal.to_string(), deadline: deadline.map(|s| s.to_string()), created_at: now.clone(), updated_at: now })
    }

    pub fn update_project(&self, id: &str, title: Option<&str>, description: Option<&str>, status: Option<&str>, category: Option<&str>, goal: Option<&str>, deadline: Option<&str>) -> Result<Project, String> {
        let now = chrono::Utc::now().to_rfc3339();
        let existing = self.get_project(id)?;
        let t = title.unwrap_or(&existing.title);
        let d = description.unwrap_or(&existing.description);
        let s = status.unwrap_or(&existing.status);
        let c = category.unwrap_or(&existing.category);
        let g = goal.unwrap_or(&existing.goal);
        let dl = deadline.or(existing.deadline.as_deref());
        self.db.execute(
            "UPDATE projects SET title=?1, description=?2, status=?3, category=?4, goal=?5, deadline=?6, updated_at=?7 WHERE id=?8",
            params![t, d, s, c, g, dl, now, id],
        ).map_err(|e| e.to_string())?;
        Ok(Project { id: id.to_string(), title: t.to_string(), description: d.to_string(), status: s.to_string(), category: c.to_string(), goal: g.to_string(), deadline: dl.map(|s| s.to_string()), created_at: existing.created_at, updated_at: now })
    }

    pub fn get_project(&self, id: &str) -> Result<Project, String> {
        let mut stmt = self.db.prepare("SELECT id, title, description, status, category, goal, deadline, created_at, updated_at FROM projects WHERE id = ?1").map_err(|e| e.to_string())?;
        let mut rows: Vec<Project> = stmt.query_map(params![id], |row| {
            Ok(Project {
                id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                status: row.get(3)?, category: row.get(4)?, goal: row.get(5)?,
                deadline: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        rows.pop().ok_or_else(|| "Project not found".to_string())
    }

    pub fn list_projects(&self, status_filter: Option<&str>) -> Result<Vec<Project>, String> {
        let query = if status_filter.is_some() {
            "SELECT id, title, description, status, category, goal, deadline, created_at, updated_at FROM projects WHERE status = ?1 ORDER BY updated_at DESC"
        } else {
            "SELECT id, title, description, status, category, goal, deadline, created_at, updated_at FROM projects ORDER BY updated_at DESC"
        };
        let mut stmt = self.db.prepare(query).map_err(|e| e.to_string())?;
        let projects = if let Some(sf) = status_filter {
            stmt.query_map(params![sf], |row| {
                Ok(Project {
                    id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                    status: row.get(3)?, category: row.get(4)?, goal: row.get(5)?,
                    deadline: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
                })
            }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect()
        } else {
            stmt.query_map([], |row| {
                Ok(Project {
                    id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                    status: row.get(3)?, category: row.get(4)?, goal: row.get(5)?,
                    deadline: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
                })
            }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect()
        };
        Ok(projects)
    }

    pub fn delete_project(&self, id: &str) -> Result<(), String> {
        self.db.execute("DELETE FROM note_associations WHERE object_type = 'project' AND object_id = ?1", params![id]).map_err(|e| e.to_string())?;
        self.db.execute("DELETE FROM projects WHERE id = ?1", params![id]).map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- People ---

    pub fn create_person(&self, name: &str, role: &str, organization: &str, email: &str, notes: &str) -> Result<Person, String> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = chrono::Utc::now().to_rfc3339();
        self.db.execute(
            "INSERT INTO people (id, name, role, organization, email, notes, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![id, name, role, organization, email, notes, now, now],
        ).map_err(|e| e.to_string())?;
        Ok(Person { id, name: name.to_string(), role: role.to_string(), organization: organization.to_string(), email: email.to_string(), notes: notes.to_string(), last_contact: None, created_at: now.clone(), updated_at: now })
    }

    pub fn update_person(&self, id: &str, name: Option<&str>, role: Option<&str>, organization: Option<&str>, email: Option<&str>, notes: Option<&str>, last_contact: Option<&str>) -> Result<Person, String> {
        let now = chrono::Utc::now().to_rfc3339();
        let existing = self.get_person(id)?;
        let n = name.unwrap_or(&existing.name);
        let r = role.unwrap_or(&existing.role);
        let o = organization.unwrap_or(&existing.organization);
        let e = email.unwrap_or(&existing.email);
        let nt = notes.unwrap_or(&existing.notes);
        let lc = last_contact.or(existing.last_contact.as_deref());
        self.db.execute(
            "UPDATE people SET name=?1, role=?2, organization=?3, email=?4, notes=?5, last_contact=?6, updated_at=?7 WHERE id=?8",
            params![n, r, o, e, nt, lc, now, id],
        ).map_err(|e| e.to_string())?;
        Ok(Person { id: id.to_string(), name: n.to_string(), role: r.to_string(), organization: o.to_string(), email: e.to_string(), notes: nt.to_string(), last_contact: lc.map(|s| s.to_string()), created_at: existing.created_at, updated_at: now })
    }

    pub fn get_person(&self, id: &str) -> Result<Person, String> {
        let mut stmt = self.db.prepare("SELECT id, name, role, organization, email, notes, last_contact, created_at, updated_at FROM people WHERE id = ?1").map_err(|e| e.to_string())?;
        let mut rows: Vec<Person> = stmt.query_map(params![id], |row| {
            Ok(Person {
                id: row.get(0)?, name: row.get(1)?, role: row.get(2)?,
                organization: row.get(3)?, email: row.get(4)?, notes: row.get(5)?,
                last_contact: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        rows.pop().ok_or_else(|| "Person not found".to_string())
    }

    pub fn list_people(&self) -> Result<Vec<Person>, String> {
        let mut stmt = self.db.prepare("SELECT id, name, role, organization, email, notes, last_contact, created_at, updated_at FROM people ORDER BY name ASC").map_err(|e| e.to_string())?;
        let people = stmt.query_map([], |row| {
            Ok(Person {
                id: row.get(0)?, name: row.get(1)?, role: row.get(2)?,
                organization: row.get(3)?, email: row.get(4)?, notes: row.get(5)?,
                last_contact: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        Ok(people)
    }

    pub fn delete_person(&self, id: &str) -> Result<(), String> {
        self.db.execute("DELETE FROM note_associations WHERE object_type = 'person' AND object_id = ?1", params![id]).map_err(|e| e.to_string())?;
        self.db.execute("DELETE FROM people WHERE id = ?1", params![id]).map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn search_people(&self, query: &str) -> Result<Vec<Person>, String> {
        let pattern = format!("%{}%", query);
        let mut stmt = self.db.prepare("SELECT id, name, role, organization, email, notes, last_contact, created_at, updated_at FROM people WHERE name LIKE ?1 OR role LIKE ?1 OR organization LIKE ?1 ORDER BY name ASC").map_err(|e| e.to_string())?;
        let people = stmt.query_map(params![pattern], |row| {
            Ok(Person {
                id: row.get(0)?, name: row.get(1)?, role: row.get(2)?,
                organization: row.get(3)?, email: row.get(4)?, notes: row.get(5)?,
                last_contact: row.get(6)?, created_at: row.get(7)?, updated_at: row.get(8)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        Ok(people)
    }

    // --- Decisions ---

    pub fn create_decision(&self, title: &str, description: &str, reasoning: &str, alternatives: &str, revisit_date: Option<&str>) -> Result<Decision, String> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = chrono::Utc::now().to_rfc3339();
        self.db.execute(
            "INSERT INTO decisions (id, title, description, reasoning, alternatives, status, decided_at, revisit_date, created_at) VALUES (?1, ?2, ?3, ?4, ?5, 'active', ?6, ?7, ?8)",
            params![id, title, description, reasoning, alternatives, now, revisit_date, now],
        ).map_err(|e| e.to_string())?;
        Ok(Decision { id, title: title.to_string(), description: description.to_string(), reasoning: reasoning.to_string(), alternatives: alternatives.to_string(), status: "active".to_string(), decided_at: now.clone(), revisit_date: revisit_date.map(|s| s.to_string()), created_at: now })
    }

    pub fn update_decision(&self, id: &str, title: Option<&str>, description: Option<&str>, reasoning: Option<&str>, alternatives: Option<&str>, status: Option<&str>, revisit_date: Option<&str>) -> Result<Decision, String> {
        let existing = self.get_decision(id)?;
        let t = title.unwrap_or(&existing.title);
        let d = description.unwrap_or(&existing.description);
        let r = reasoning.unwrap_or(&existing.reasoning);
        let a = alternatives.unwrap_or(&existing.alternatives);
        let s = status.unwrap_or(&existing.status);
        let rd = revisit_date.or(existing.revisit_date.as_deref());
        self.db.execute(
            "UPDATE decisions SET title=?1, description=?2, reasoning=?3, alternatives=?4, status=?5, revisit_date=?6 WHERE id=?7",
            params![t, d, r, a, s, rd, id],
        ).map_err(|e| e.to_string())?;
        Ok(Decision { id: id.to_string(), title: t.to_string(), description: d.to_string(), reasoning: r.to_string(), alternatives: a.to_string(), status: s.to_string(), decided_at: existing.decided_at, revisit_date: rd.map(|s| s.to_string()), created_at: existing.created_at })
    }

    pub fn get_decision(&self, id: &str) -> Result<Decision, String> {
        let mut stmt = self.db.prepare("SELECT id, title, description, reasoning, alternatives, status, decided_at, revisit_date, created_at FROM decisions WHERE id = ?1").map_err(|e| e.to_string())?;
        let mut rows: Vec<Decision> = stmt.query_map(params![id], |row| {
            Ok(Decision {
                id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                reasoning: row.get(3)?, alternatives: row.get(4)?, status: row.get(5)?,
                decided_at: row.get(6)?, revisit_date: row.get(7)?, created_at: row.get(8)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        rows.pop().ok_or_else(|| "Decision not found".to_string())
    }

    pub fn list_decisions(&self, status_filter: Option<&str>) -> Result<Vec<Decision>, String> {
        let query = if status_filter.is_some() {
            "SELECT id, title, description, reasoning, alternatives, status, decided_at, revisit_date, created_at FROM decisions WHERE status = ?1 ORDER BY decided_at DESC"
        } else {
            "SELECT id, title, description, reasoning, alternatives, status, decided_at, revisit_date, created_at FROM decisions ORDER BY decided_at DESC"
        };
        let mut stmt = self.db.prepare(query).map_err(|e| e.to_string())?;
        let decisions = if let Some(sf) = status_filter {
            stmt.query_map(params![sf], |row| {
                Ok(Decision {
                    id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                    reasoning: row.get(3)?, alternatives: row.get(4)?, status: row.get(5)?,
                    decided_at: row.get(6)?, revisit_date: row.get(7)?, created_at: row.get(8)?,
                })
            }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect()
        } else {
            stmt.query_map([], |row| {
                Ok(Decision {
                    id: row.get(0)?, title: row.get(1)?, description: row.get(2)?,
                    reasoning: row.get(3)?, alternatives: row.get(4)?, status: row.get(5)?,
                    decided_at: row.get(6)?, revisit_date: row.get(7)?, created_at: row.get(8)?,
                })
            }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect()
        };
        Ok(decisions)
    }

    // --- Note Associations ---

    pub fn create_association(&self, note_id: &str, object_type: &str, object_id: &str, relationship: &str, confidence: f64) -> Result<NoteAssociation, String> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = chrono::Utc::now().to_rfc3339();
        self.db.execute(
            "INSERT OR REPLACE INTO note_associations (id, note_id, object_type, object_id, relationship, confidence, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![id, note_id, object_type, object_id, relationship, confidence, now],
        ).map_err(|e| e.to_string())?;
        Ok(NoteAssociation { id, note_id: note_id.to_string(), object_type: object_type.to_string(), object_id: object_id.to_string(), relationship: relationship.to_string(), confidence, created_at: now })
    }

    pub fn get_associations_for_note(&self, note_id: &str) -> Result<Vec<NoteAssociation>, String> {
        let mut stmt = self.db.prepare("SELECT id, note_id, object_type, object_id, relationship, confidence, created_at FROM note_associations WHERE note_id = ?1").map_err(|e| e.to_string())?;
        let assocs = stmt.query_map(params![note_id], |row| {
            Ok(NoteAssociation {
                id: row.get(0)?, note_id: row.get(1)?, object_type: row.get(2)?,
                object_id: row.get(3)?, relationship: row.get(4)?, confidence: row.get(5)?,
                created_at: row.get(6)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        Ok(assocs)
    }

    pub fn get_associations_for_object(&self, object_type: &str, object_id: &str) -> Result<Vec<NoteAssociation>, String> {
        let mut stmt = self.db.prepare("SELECT id, note_id, object_type, object_id, relationship, confidence, created_at FROM note_associations WHERE object_type = ?1 AND object_id = ?2").map_err(|e| e.to_string())?;
        let assocs = stmt.query_map(params![object_type, object_id], |row| {
            Ok(NoteAssociation {
                id: row.get(0)?, note_id: row.get(1)?, object_type: row.get(2)?,
                object_id: row.get(3)?, relationship: row.get(4)?, confidence: row.get(5)?,
                created_at: row.get(6)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        Ok(assocs)
    }

    pub fn delete_association(&self, id: &str) -> Result<(), String> {
        self.db.execute("DELETE FROM note_associations WHERE id = ?1", params![id]).map_err(|e| e.to_string())?;
        Ok(())
    }

    // --- Note Metadata ---

    pub fn get_note_metadata(&self, note_id: &str) -> Result<NoteMetadata, String> {
        let mut stmt = self.db.prepare("SELECT note_id, lifecycle, last_meaningful_edit, view_count, importance_score, distilled_at, source_type FROM note_metadata WHERE note_id = ?1").map_err(|e| e.to_string())?;
        let mut rows: Vec<NoteMetadata> = stmt.query_map(params![note_id], |row| {
            Ok(NoteMetadata {
                note_id: row.get(0)?, lifecycle: row.get(1)?,
                last_meaningful_edit: row.get(2)?, view_count: row.get(3)?,
                importance_score: row.get(4)?, distilled_at: row.get(5)?,
                source_type: row.get(6)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        match rows.pop() {
            Some(meta) => Ok(meta),
            None => {
                // Auto-create default metadata
                let now = chrono::Utc::now().to_rfc3339();
                self.db.execute(
                    "INSERT INTO note_metadata (note_id, lifecycle, last_meaningful_edit, view_count, importance_score, source_type) VALUES (?1, 'active', ?2, 0, 0.5, 'manual')",
                    params![note_id, now],
                ).map_err(|e| e.to_string())?;
                Ok(NoteMetadata { note_id: note_id.to_string(), lifecycle: "active".to_string(), last_meaningful_edit: Some(now), view_count: 0, importance_score: 0.5, distilled_at: None, source_type: "manual".to_string() })
            }
        }
    }

    pub fn update_note_metadata(&self, note_id: &str, lifecycle: Option<&str>, last_meaningful_edit: Option<&str>, view_count: Option<i32>, importance_score: Option<f64>, distilled_at: Option<&str>, source_type: Option<&str>) -> Result<NoteMetadata, String> {
        // Ensure metadata exists first
        let existing = self.get_note_metadata(note_id)?;
        let lc = lifecycle.unwrap_or(&existing.lifecycle);
        let lme = last_meaningful_edit.or(existing.last_meaningful_edit.as_deref());
        let vc = view_count.unwrap_or(existing.view_count);
        let is = importance_score.unwrap_or(existing.importance_score);
        let da = distilled_at.or(existing.distilled_at.as_deref());
        let st = source_type.unwrap_or(&existing.source_type);
        self.db.execute(
            "UPDATE note_metadata SET lifecycle=?1, last_meaningful_edit=?2, view_count=?3, importance_score=?4, distilled_at=?5, source_type=?6 WHERE note_id=?7",
            params![lc, lme, vc, is, da, st, note_id],
        ).map_err(|e| e.to_string())?;
        Ok(NoteMetadata { note_id: note_id.to_string(), lifecycle: lc.to_string(), last_meaningful_edit: lme.map(|s| s.to_string()), view_count: vc, importance_score: is, distilled_at: da.map(|s| s.to_string()), source_type: st.to_string() })
    }

    pub fn get_stale_notes(&self, days_threshold: i32) -> Result<Vec<Note>, String> {
        let mut stmt = self.db.prepare(
            "SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
             FROM notes n
             JOIN note_metadata nm ON n.id = nm.note_id
             WHERE nm.lifecycle = 'active'
               AND nm.importance_score > 0.3
               AND julianday('now') - julianday(COALESCE(nm.last_meaningful_edit, n.updated_at)) > ?1
             ORDER BY nm.importance_score DESC
             LIMIT 20"
        ).map_err(|e| e.to_string())?;
        let notes = stmt.query_map(params![days_threshold], |row| {
            let fm_str: String = row.get(4)?;
            let frontmatter: HashMap<String, String> = serde_json::from_str(&fm_str).unwrap_or_default();
            Ok(Note {
                id: row.get(0)?, file_path: row.get(1)?, title: row.get(2)?,
                content: row.get(3)?, frontmatter, outgoing_links: vec![],
                created_at: row.get(5)?, updated_at: row.get(6)?,
            })
        }).map_err(|e| e.to_string())?.filter_map(|r| r.ok()).collect();
        Ok(notes)
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub title: String,
    pub description: String,
    pub status: String,
    pub category: String,
    pub goal: String,
    pub deadline: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Person {
    pub id: String,
    pub name: String,
    pub role: String,
    pub organization: String,
    pub email: String,
    pub notes: String,
    pub last_contact: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub id: String,
    pub title: String,
    pub description: String,
    pub reasoning: String,
    pub alternatives: String,
    pub status: String,
    pub decided_at: String,
    pub revisit_date: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteAssociation {
    pub id: String,
    pub note_id: String,
    pub object_type: String,
    pub object_id: String,
    pub relationship: String,
    pub confidence: f64,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteMetadata {
    pub note_id: String,
    pub lifecycle: String,
    pub last_meaningful_edit: Option<String>,
    pub view_count: i32,
    pub importance_score: f64,
    pub distilled_at: Option<String>,
    pub source_type: String,
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
