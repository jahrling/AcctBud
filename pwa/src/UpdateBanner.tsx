import { useServiceWorker } from "./useServiceWorker";

export function UpdateBanner() {
  const { updateAvailable, update } = useServiceWorker();

  if (!updateAvailable) return null;

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
        padding: "0.6rem 1rem",
        background: "var(--accent)",
        color: "var(--text)",
        fontSize: "0.85rem",
      }}
    >
      <span>New version available</span>
      <button
        onClick={update}
        style={{
          padding: "4px 12px",
          borderRadius: "6px",
          background: "var(--accent-bright)",
          color: "white",
          fontSize: "0.8rem",
          fontWeight: 600,
        }}
      >
        Refresh
      </button>
    </div>
  );
}
