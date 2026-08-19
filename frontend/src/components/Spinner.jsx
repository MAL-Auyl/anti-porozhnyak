/**
 * Design review finding: LLM parsing takes ~5s — needs an explicit
 * loading indicator, not a blank screen a judge might mistake for broken.
 */
export default function Spinner({ label }) {
  return (
    <div className="spinner-row">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
