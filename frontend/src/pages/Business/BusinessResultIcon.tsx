const paths = {
  back: "M19 12H5m6-6-6 6 6 6",
  download: "M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5",
  summary: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  discussion: "M4 4h16v12H9l-5 4V4m4 4h8m-8 4h5",
  chat: "M4 4h16v12H9l-5 4V4m4 6h.01M12 10h.01M16 10h.01",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  zoomIn: "M5 12h14M12 5v14",
  zoomOut: "M5 12h14",
  fit: "M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5",
  reset: "M4 10a8 8 0 1 1 1 8M4 4v6h6",
} as const;

export function BusinessResultIcon({ name }: { name: keyof typeof paths }) {
  return <svg className="business-result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>;
}
