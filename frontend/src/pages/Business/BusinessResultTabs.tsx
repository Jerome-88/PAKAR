
export function BusinessResultTabs({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const selected = ["swarm", "timeline", "chat"].includes(value) ? "summary" : value;
  return <div className="business-results-navigation"><nav className="business-tabs" aria-label="Hasil analisis">{[["summary", "Tim Discussion"], ["findings", "Blind Spots"], ["evidence", "Evidence & Calculations"], ["scenario", "Scenario Lab"], ["report", "Final Report"], ["audit", "Analysis Trail"]].map(([id, label]) => <button type="button" key={id} className={selected === id ? "active" : ""} aria-current={selected === id ? "page" : undefined} onClick={() => onChange(id)}>{label}</button>)}</nav></div>;
}
import "./BusinessProjectResult.css";
