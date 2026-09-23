/**
 * One identity, or both side by side (ph. 06 §6).
 *
 * Lives in the top bar rather than the left rail, because in compare mode
 * there IS no left rail: both identities are running, so a single identity's
 * grants panel would be describing one of two panes and the picker would be
 * choosing something nothing reads. The toggle has to sit somewhere that
 * survives the layout it changes.
 *
 * Only rendered when `DEMO_COMPARE_MODE` is on — compare mode relaxes the
 * trust boundary (see the proxy route), so it is opt-in.
 *
 * Plain links, not buttons: the mode is a URL, so a presenter can open the
 * side-by-side view directly and a mis-click is recoverable with Back.
 */
import Link from "next/link";

export function ModeSwitch({ compare }: { compare: boolean }) {
  return (
    <nav className="modeswitch" aria-label="View">
      <Link href="/" aria-current={!compare ? "page" : undefined}>
        One identity
      </Link>
      <Link href="/?mode=compare" aria-current={compare ? "page" : undefined}>
        Side by side
      </Link>
    </nav>
  );
}
