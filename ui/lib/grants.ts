/**
 * What each identity may reach — READ, never decided here (ph. 06 §4, C2).
 *
 * `agent/contracts/grants.py` is the single source of truth. It emits
 * `grants.json` via `contracts/emit_grants_json.py`, and this module is the
 * only place the UI touches it. Nothing in `ui/` hardcodes a role name, a
 * corpus name, or a grant: if this file and the agent ever disagree, the
 * screen is lying about a deployment the audience can see the traces for.
 *
 * `order` and `withheld` are both EMITTED rather than computed here. Deriving
 * `withheld` in TypeScript would put a second implementation of "what this
 * role cannot reach" in the client — exactly the duplication C2 exists to
 * prevent, and exactly the one that would go unnoticed, because a wrong ✗ row
 * still renders perfectly.
 */
import data from "../../agent/contracts/grants.json";

export type Role = keyof typeof data.roles;
export type CorpusId = keyof typeof data.corpora;

export interface RoleGrants {
  /** How the identity is shown. Display only — never an authorization input. */
  label: string;
  /** Every corpus this role may call. */
  granted: string[];
  /** The same corpora, most authoritative first. PREFERENCE, not enforcement. */
  order: string[];
  /** Corpora this role cannot reach at all. ENFORCED. The ✗ row. */
  withheld: string[];
}

export const GRANTS = data.roles as Record<Role, RoleGrants>;
export const CORPORA = data.corpora as Record<string, string>;
export const DEMO_VERSION: string = data.demo_version;

/** The roles a person may pick, in display order. */
export const ROLES = Object.keys(GRANTS) as Role[];

/**
 * Is this a role at all?
 *
 * Used by BOTH the identity route and the compare-mode header (§6), so a
 * client-supplied string is checked against the emitted set in one place
 * rather than two. A role that is not in `grants.json` never reaches the
 * deployment — and if one somehow did, the agent rejects it (C1).
 */
export function isRole(value: unknown): value is Role {
  return typeof value === "string" && Object.hasOwn(GRANTS, value);
}

/** Human text for a corpus id, for the grants panel. */
export function describe(corpus: string): string {
  return CORPORA[corpus] ?? corpus;
}
