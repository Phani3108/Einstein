import { useState, useEffect, useRef } from "react";

const CLOUD_API = "http://localhost:8000";
const POLL_INTERVAL = 30_000;

const styles = {
  banner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: "6px 16px",
    background: "#422006",
    borderBottom: "1px solid #854d0e",
    color: "#f59e0b",
    fontSize: 13,
    fontWeight: 500 as const,
    lineHeight: 1,
    zIndex: 9999,
  },
  refreshIcon: {
    display: "inline-flex",
    cursor: "pointer",
    opacity: 0.8,
  },
};

function OfflineBanner() {
  const [offline, setOffline] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${CLOUD_API}/api/v1/info`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      setOffline(!res.ok);
    } catch {
      setOffline(true);
    }
  };

  useEffect(() => {
    checkStatus();
    timerRef.current = setInterval(checkStatus, POLL_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  if (!offline) return null;

  return (
    <div style={styles.banner}>
      <span
        style={styles.refreshIcon}
        onClick={() => checkStatus()}
        title="Retry connection"
      >
        &#x21bb;
      </span>
      Offline &mdash; using cached data
    </div>
  );
}

export default OfflineBanner;
