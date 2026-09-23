/**
 * Single identity vs. side by side (ph. 06 §6).
 *
 * Only rendered when `DEMO_COMPARE_MODE` is on, because compare mode relaxes
 * the trust boundary (see the proxy route). The identity selector is the
 * committed deliverable; this is the upgrade.
 *
 * Plain links, not buttons: the mode is a URL so a presenter can open the
 * side-by-side view directly and so a mis-click is recoverable with Back.
 */
import Link from "next/link";

export function ModeSwitch({ compare }: { compare: boolean }) {
  return (
    <div className="panel">
      <h2>View</h2>
      <div className="modeswitch">
        <Link href="/" aria-pressed={!compare} role="button">
          One identity
        </Link>
        <Link href="/?mode=compare" aria-pressed={compare} role="button">
          Side by side
        </Link>
      </div>
    </div>
  );
}
