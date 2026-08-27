# diakoptis

**διακόπτης** — Greek for "switch."

An interactive CLI for troubleshooting network switches over SSH, using friendly commands
instead of vendor-specific syntax. Built on [Netmiko](https://github.com/ktbyers/netmiko),
with structured output parsing via local [TextFSM](https://github.com/google/textfsm)
templates and the community [ntc-templates](https://github.com/networktocode/ntc-templates)
project as a fallback.

## Why the rename

This started as `asterfusion-cli` — a tool for Asterfusion (AsterNOS) switches specifically.
Once the driver abstraction, per-vendor command maps, and multi-switch fan-out were designed
in, the project stopped being about one vendor. **diakoptis** reflects what it actually is
now: a tool for switches, plural — Asterfusion today, Huawei VRP with real structured-parsing
coverage already, and any future vendor that implements the same driver interface.

## What it does

- Connects to one or many switches over SSH via Netmiko.
- Lets you type friendly, vendor-agnostic commands (`check bgp`, `show interfaces`) instead
  of memorizing native CLI syntax per platform — the same command means the same thing
  regardless of which switch answers it.
- Targets a single switch, an explicit list, or a tag/group query:
  `connect switch1,switch2` · `connect @role:leaf` · `connect @role:leaf&@site:nairobi`
- Fans a command out to every connected switch concurrently and aggregates the results into
  a comparison view, so an outlier (one switch's interface down when the rest are up) is
  visible at a glance.
- Parses raw CLI output through a fallback chain: a local TextFSM template first, then
  `ntc-templates`' community index, then raw text — a command is never blocked on being
  unparsed.
- Is built to grow: adding a vendor means adding a driver and a command map, not touching
  existing code (Open/Closed Principle — see `docs/plan.md` for the full design rationale).

## Supported vendors so far

| Vendor | Netmiko `device_type` | Structured parsing today |
|---|---|---|
| Asterfusion (AsterNOS / `sonic-cli`) | `asterfusion_asternos` | None yet — `ntc-templates` has no matching platform, so commands fall through to raw text until local templates are written or upstream coverage appears. |
| Huawei (VRP) | `huawei_vrp` | Broad, confirmed `ntc-templates` coverage — most commands return structured data with no local templates needed. |

Adding a new vendor: implement `SwitchDriver` under `drivers/`, register it in
`drivers/factory.py`, and add `config/command_map/<vendor>.yaml`. See "Extending to a new
vendor" below.

## Quick start

```bash
git clone <repo-url> diakoptis
cd diakoptis
pip install -e .
pip install ntc-templates textfsm   # parsing fallback chain

cp config/inventory.yaml.example config/inventory.yaml
# edit config/inventory.yaml with your real switches, then export the env vars
# your credential_profiles reference, e.g.:
export ASTER_DEFAULT_USER=admin
export ASTER_DEFAULT_PASS=********

python -m diakoptis
```

## Configuration

### Inventory — `config/inventory.yaml`

Defines switches, their vendor/device_type, and how they're grouped and authenticated.

- **`credential_profiles`** — named credential bundles resolved via environment variable
  *names* (never plaintext secrets in the file). Each switch references one by name, so
  switches can share a login or use entirely different ones.
- **`site` / `role` / `environment`** tags on each switch — orthogonal dimensions used for
  targeting (`@site:nairobi`, `@role:leaf`), not for cascading config defaults (deliberately
  out of scope for now — see Known Limitations).
- **`groups`** — optional, hand-curated sets that don't correspond to a single tag (a
  maintenance window, a set spanning multiple roles).

See `config/inventory.yaml.example` for a complete, runnable example.

### Command maps — `config/command_map/<vendor>.yaml`

One file per vendor. Each entry maps a friendly command to the vendor's native CLI
command(s) and a parsing strategy:

```yaml
check_bgp:
  description: "Check BGP peer state and prefix counts"
  native: ["display bgp peer"]   # or ["show ip bgp summary"] for another vendor
  parse: ntc
```

`parse` is one of:

| Value | Meaning |
|---|---|
| `raw` | Never structured — return the output as-is (used for logs, DOM/optics output, anything free-form that a table would misrepresent) |
| `ntc` | Parse via `ntc-templates`, matched against the switch's own `device_type` |
| `<vendor>/<file>.textfsm` | A local template, relative to the templates root — falls back to `ntc`, then raw, if the file is missing |

An optional `ntc_override: {platform, command}` block lets a command match ntc-templates
against a *different* platform/command pair than what was actually sent — useful when a
native command's wording doesn't match an existing template's trigger pattern, but treat any
override as unverified until checked against real captured output: a matching command regex
doesn't guarantee a matching column layout.

## Using the CLI

```
diakoptis> connect switch1,switch2,switch3
diakoptis [3 hosts]> check bgp
diakoptis [3 hosts]> show interfaces
diakoptis [3 hosts]> connect @role:leaf&@site:nairobi
diakoptis> disconnect
diakoptis> exit
```

Run `help` inside the shell for the full list of available friendly commands, generated
directly from whichever command maps are loaded.

## Architecture

Full design rationale, diagrams, and the decisions behind each piece (targeting syntax,
multi-vendor driver abstraction, credential resolution, parser fallback chain) live in
[`docs/diakoptis_cli_plan.md`](docs/diakoptis.md)

```
Interactive Shell -> Target Parser -> Session Pool (fan-out) -> Vendor Driver Factory
                                                                       |
                                                    Asterfusion / Huawei / (future vendors)
                                                                       |
                                            Output Parser (local -> ntc-templates -> raw)
                                                                       |
                                      Diagnostics Engine -> Aggregator -> Renderer
```


## Extending to a new vendor

1. Add `drivers/<vendor>.py` implementing the `SwitchDriver` interface (Netmiko
   `device_type`, `connect()`/`send_native()`).
2. Register it in `drivers/factory.py`.
3. Add `config/command_map/<vendor>.yaml` — reuse existing friendly command names for
   equivalent functionality so `check bgp` keeps meaning the same thing everywhere.
4. Check whether `ntc-templates` already covers that platform before writing any local
   templates — it may get you structured parsing for free (as with Huawei VRP).

No changes to the shell, resolver, session pool, or aggregator are required.

## Known limitations / open items

- **Asterfusion has no local templates yet.** Every command currently returns raw text;
  see `config/command_map/asterfusion.yaml` for the graduation path once templates exist.
- **`{target}` argument substitution isn't implemented.** Parameterized commands like
  `check bgp_neighbor 10.0.0.1` are declared in the command map but not yet wired up in
  the resolver.
- **Credential/config don't cascade by site/role/environment.** Every switch is explicit
  about its own `credential_profile` — deliberately deferred rather than picking an
  arbitrary precedence across three independent dimensions.
- **Hand-rolled session pool vs. Nornir.** The concurrent fan-out is currently custom
  (`ThreadPoolExecutor` + Netmiko); [Nornir](https://nornir.readthedocs.io/) already solves
  this plus multi-vendor inventory, and adopting it instead is still an open decision.
- **Boolean targeting is intentionally minimal.** Only two-term intersection
  (`@role:leaf&@site:nairobi`) is supported; exclusion and deeper set algebra are deferred
  until a real need shows up.

