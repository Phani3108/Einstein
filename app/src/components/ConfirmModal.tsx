import { AlertTriangle, Info, CheckCircle } from "lucide-react";

interface ConfirmModalProps {
  title: string;
  message: string;
  type?: "info" | "warning" | "danger";
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  title,
  message,
  type = "info",
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const Icon = type === "danger" ? AlertTriangle : type === "warning" ? AlertTriangle : type === "info" ? Info : CheckCircle;
  const iconColor = type === "danger" ? "#ef4444" : type === "warning" ? "#f59e0b" : "var(--accent)";

  return (
    <div className="search-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="confirm-modal">
        <div className="confirm-header">
          <Icon size={20} color={iconColor} />
          <h3>{title}</h3>
        </div>
        <p className="confirm-message">{message}</p>
        <div className="confirm-actions">
          <button className="btn-secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button
            className={`btn-primary ${type === "danger" ? "btn-danger" : ""}`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
