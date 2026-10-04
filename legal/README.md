# Legal and release documents

Drafts for **On the Rise Digital** (Alison Risner) as a software publisher.
Written as templates — `the software` where a product name goes — so the same
set serves the next thing you release, not only Easy-dlp.

**They are not legal advice and I am not a lawyer.** They cover what these
documents usually cover and should cut a lawyer's review to about an hour,
which is the one line on either checklist worth paying for.

---

## Which set do I need?

```
legal/
├── shared/     every route needs these
├── direct/     your own site, or a marketplace like Fourthwall or Gumroad
└── store/      Microsoft Store
```

| | Direct | Store |
|---|---|---|
| EULA | ✅ | ✅ (optional — Microsoft's applies if you supply none) |
| Terms of Use | ✅ | ✅ |
| Privacy Policy | ✅ | ✅ **required at a public URL** |
| Third-party licences | ✅ | ✅ |
| **Terms of Sale** | ✅ | ❌ Microsoft is the seller |
| **Refund Policy** | ✅ | ❌ Microsoft's applies |
| **Website Terms** | ✅ | ❌ |
| **Cookie Notice** | ✅ | ❌ |
| **Support Policy** | ✅ | recommended |
| **Install instructions** | ✅ | ❌ no SmartScreen warning on a Store install |
| Code-signing certificate | $0–500/yr | ❌ free |
| Sales tax handling | your provider's, or yours | Microsoft's |

**Selling direct makes you the merchant.** That is where the extra documents
come from — not bureaucracy, but the fact that you are now the one taking
money, delivering goods, handling refunds and answering for tax.

## Start here

- Selling direct → **`direct/CHECKLIST.md`**
- Microsoft Store → **`store/CHECKLIST.md`**
- Deciding between them → `../RELEASING.md`

## The files

### `shared/` — both routes

| File | Goes where |
|---|---|
| `EULA.md` | installer, install folder, linked from About |
| `TERMS-OF-USE.md` | install folder, published |
| `PRIVACY-POLICY.md` | **public URL** |
| `THIRD-PARTY-LICENCES.md` | install folder, About box — a licence condition |

### `direct/` — your own site or a marketplace

| File | Goes where |
|---|---|
| `TERMS-OF-SALE.md` | published, linked from checkout |
| `REFUND-POLICY.md` | published, linked from checkout **and** product page |
| `WEBSITE-TERMS.md` | published |
| `COOKIE-NOTICE.md` | published — pick version A or B |
| `SUPPORT-POLICY.md` | published |
| `INSTALL.md` | download page, confirmation email, `READ-ME-FIRST.txt` |
| `CHECKLIST.md` | you |

### `store/` — Microsoft Store

| File | What it is |
|---|---|
| `SUBMISSION.md` | what the Store needs, and what it saves you |
| `CHECKLIST.md` | you |

## Already filled in

| | |
|---|---|
| Contracting party | Alison Risner, trading as On the Rise Digital |
| Email | ontherisedigital@gmail.com |
| State | Ohio |
| Currency | USD |
| Payment provider | Lemon Squeezy |
| Store / web address | https://ontherisedigital.lemonsqueezy.com |

**`[VERSION]` is the only placeholder left**, in
`shared/THIRD-PARTY-LICENCES.md`. It is per-release by design — fill it from
`yt-dlp --version` and `ffmpeg -version` at build time, not once.

If you change provider or claim a different store subdomain:

```bash
grep -rln "lemonsqueezy" legal/ | xargs sed -i 's|ontherisedigital.lemonsqueezy.com|YOUR-URL|g'
```

Two things in `direct/COOKIE-NOTICE.md` stay open on purpose:
`[ANALYTICS PROVIDER]` and `[PERIOD]`, in Version B only. Use Version A and
delete Version B, and they go with it.

---

## Decisions that affect every document

### 1. "No refunds" is not enforceable everywhere

A flat no-refunds policy is void against EU and UK consumers, who have a
statutory 14-day right to cancel. It does not bind the Microsoft Store, and
it does not stop a chargeback — one of those costs you the sale plus a fee,
and a pattern of them endangers your payment account.

**What is written instead:** "all sales are final" as the default, with
carve-outs where law overrides. Then the clause that actually works — **at
checkout, the buyer ticks a box requesting immediate delivery and
acknowledging they lose the right to cancel.** That tick closes the EU/UK gap
properly. Lemon Squeezy, Paddle and Gumroad all support it, usually as
"digital goods" or "waive withdrawal right".

Offer goodwill refunds quietly for the first few months regardless. A refund
costs one sale; a chargeback costs the sale, a fee, and a mark against your
merchant account.

### 2. "On the Rise Digital" is not a legal entity

Three consequences: no liability shield, so a claim reaches you personally
and the limitation-of-liability clause is a contract term rather than armour;
most US states require a DBA registration to trade under a name that is not
your own; and the Store **Company** account needs a verifiable registered
business, which you would not pass.

**Options, cheapest first:**

- **DBA** with your county or state — $10–100 and a form. Legitimises the
  trading name, usually enough to bank under it. **No** liability protection.
- **Single-member LLC** — $50–500 plus an annual fee. This is what actually
  separates personal assets from the business. For a product that ships to
  strangers and touches copyright questions, it is the right answer sooner
  rather than later.
- **Meanwhile:** sell under your own legal name with "On the Rise Digital" as
  the brand. The documents already contract as *Alison Risner, trading as On
  the Rise Digital*, which is lawful and accurate today.

**Settle this before registering a Store account** — Partner Center cannot
convert Individual to Company later.

### 3. "No commercial use" had to be narrowed

As a bare phrase it is ambiguous enough to backfire. A freelance illustrator
buys the software, downloads a course they paid for, uses what they learned
in paid work — breach? Literally, arguably yes, which is not what you meant
and is not a term you would enforce.

**What is written instead:** EULA §3.1 restricts commercial use **of the
software** — no running it on another person's behalf, no building a paid
service on it — and says explicitly that using downloaded material for your
own work is not restricted.

### 4. The first-run warning is a support problem, not a clause

Buried in an EULA, nobody reads it, and a customer meeting *"Windows
protected your PC"* cold concludes they bought malware.

**What is written instead:** `direct/INSTALL.md`, for the confirmation email,
the download page and a `READ-ME-FIRST.txt`. Explains that SmartScreen is a
popularity check rather than a virus scan, gives the two clicks, and offers a
SHA-256 and VirusTotal for anyone who would rather verify than trust.

**Store route only:** delete this concern. A Store install never warns.

---

## Also worth having

- **A short warranty statement.** "If it does not work on a supported system
  within 30 days, we fix it or refund you" converts well and costs little
  when the software works.
- **Supported systems, stated plainly**, so "it does not work" on Windows 8
  is not your problem.
- **What happens when a third-party service breaks it** — say it on the sales
  page, in friendly words, before the purchase rather than after.
- **An export-control line** for international sales. One sentence, standard;
  your payment provider may require it.
- **An accessibility note** where it applies. Honest, a real differentiator,
  and the best answer to anyone asking what a tool is for.
