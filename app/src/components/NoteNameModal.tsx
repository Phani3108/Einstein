import { useState, useCallback, useEffect, useRef } from "react";
import { useTranslation } from "../lib/i18n";
import { X } from "lucide-react";

interface NoteNameModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string) => void;
  title?: string;
}

export function NoteNameModal({ open, onClose, onSubmit, title }: NoteNameModalProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleSubmit = useCallback(() => {
    const trimmed = name.trim();
    if (trimmed) {
      onSubmit(trimmed);
      setName("");
      onClose();
    }
  }, [name, onSubmit, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content note-name-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title || t("general.noteNamePrompt")}</h3>
          <button className="icon-btn" onClick={onClose}>
            <X size={14} />
          </button>
        </div>
        <input
          ref={inputRef}
          type="text"
          className="onboard-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit();
            if (e.key === "Escape") onClose();
          }}
          placeholder={t("general.noteNamePrompt")}
        />
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose}>{t("general.cancel")}</button>
          <button className="btn-primary" onClick={handleSubmit} disabled={!name.trim()}>
            {t("general.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
