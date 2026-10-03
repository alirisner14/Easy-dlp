# What is in here, and what still needs doing

Drafts of the documents Easy-dlp needs before it can be sold. They are
written to be read by a normal person, cover what these documents usually
cover, and say what you asked them to say.

**They are not legal advice and I am not a lawyer.** They are a solid starting
point that will save you most of a lawyer's billable time, not a substitute
for one. Four items below have real legal constraints; each has a fix.

| File | Goes where |
|---|---|
| `EULA.md` | shown by the installer, installed beside the app, linked from About |
| `TERMS.md` | installed beside the app, published on your site |
| `PRIVACY.md` | **must be at a public URL** — required by the Microsoft Store |
| `THIRD-PARTY-LICENCES.md` | installed beside the app, linked from About |
| `licences/` | full licence texts — create this folder before release |

## Fill these in everywhere

`[LEGAL NAME]` · `[SUPPORT EMAIL]` · `[WEBSITE]` · `[STATE]` · `[DATE]` ·
`[VERSION]`

```bash
grep -rn "\[LEGAL NAME\]\|\[SUPPORT EMAIL\]\|\[WEBSITE\]\|\[STATE\]\|\[DATE\]\|\[VERSION\]" legal/
```

Run that again before every release. A published document with `[DATE]` in it
undermines the rest of it.

---

## The four things that need a decision

### 1. "No refunds" is not enforceable everywhere

**The problem.** A flat no-refunds policy is void against consumers in the EU
and UK, who have a statutory 14-day right to cancel. It also does not bind
the Microsoft Store, which applies its own policy regardless of yours, and it
does not stop a card chargeback — losing one of those costs you the sale
*plus* a fee, and a pattern of them puts your payment account at risk.

**The fix, already written into section 9 of the EULA:** keep "all sales are
final" as the default, and carve out the cases where the law overrides you.
Then add the one clause that actually protects you — at checkout, get the
buyer to tick a box saying they request immediate delivery and understand
they lose the right to cancel once the download starts. That tick is what
makes the EU/UK carve-out close again. Paddle, Lemon Squeezy and Gumroad all
support this; it is usually a setting called "digital goods" or "waive
withdrawal right".

**Also worth doing:** offer a goodwill refund quietly for the first few
months. A refunded customer costs you one sale. A chargeback costs you the
sale, a fee, and a mark against your merchant account.

### 2. "On the Rise Digital" is not a legal entity

**The problem.** Trading under a name that is not registered creates three
issues. You have no liability shield — a claim lands on you personally, your
savings included, and the limitation-of-liability clause is a contract term,
not armour. Most US states require a DBA ("fictitious business name")
registration before you can lawfully trade under a name that is not your own,
and some require it before a bank will open an account in that name. And the
Microsoft Store **Company** account needs a verifiable registered business —
which you would not pass.

**The fix, cheapest first:**

- **Register a DBA** with your county or state. Typically $10–100 and a form.
  This legitimises the trading name and is usually enough to take payments
  under it. It gives you **no** liability protection.
- **Form a single-member LLC** when revenue justifies it — $50–500 depending
  on state, plus an annual fee. This is what actually separates your personal
  assets from the business. For a product that ships to strangers and touches
  copyright questions, it is the right answer sooner rather than later.
- **In the meantime**, sell under your own legal name with "On the Rise
  Digital" as a brand, and put your real name in the EULA as the contracting
  party. That is lawful and honest; the drafts are already written this way,
  which is why `[LEGAL NAME]` appears and not just the brand.

On the Store account question specifically: if you are not a registered
entity, you cannot pass Company verification — but Microsoft describes
Individual accounts as for distribution *not* in relation to a business or
profession, which selling does not fit. **Resolve the entity question before
you register the Store account**, because Partner Center cannot convert an
Individual account into a Company one later.

### 3. "No commercial use" needs to say which thing is restricted

**The problem.** As a bare phrase it is ambiguous in a way that will cost you
sales and create disputes. A freelance illustrator buys Easy-dlp to download
a course they paid for, and uses what they learn in paid work. Have they
breached it? Under a literal reading, arguably yes — which is almost
certainly not what you meant, and is a term you would never actually enforce.

**The fix, already written into clause 3.1:** restrict commercial use *of the
Software*, not of what the user does afterwards. The clause now says you may
not run it on someone else's behalf or as part of a service you charge for,
and states explicitly that using downloaded material for your own work is not
restricted. That keeps what you want — nobody building a download service on
your tool — and drops what you do not.

### 4. The first-run warning is not a legal document

**The problem.** You listed it with the legal items, but a SmartScreen
warning is a support issue, and burying the instructions in an EULA means
nobody reads them. A customer who hits "Windows protected your PC" with no
warning assumes they have been sold malware and asks for a refund.

**The fix:** tell them *before* they see it, in three places — the purchase
confirmation email, the download page, and a `READ-ME-FIRST.txt` in the
download. `INSTALL.md` in this folder is written to be used for all three.
Saying it first turns an alarming moment into an expected one.

---

## Also worth adding, which you did not list

- **A warranty-period statement.** Not required, but "if it does not work on
  a supported system within 30 days, we will fix it or refund you" converts
  far better than silence, and costs little when the software works.
- **Supported systems, stated plainly.** Windows 10 1809 or later, 64-bit.
  Without this, "it does not work" on Windows 8 becomes your problem.
- **What happens when a site breaks it.** Section 7 of the Terms says you do
  not guarantee it keeps working. Say the same on the sales page, in friendly
  words, before the purchase rather than after.
- **An export-control line**, if you sell internationally: that the buyer is
  not in a sanctioned country and is not on a denied-parties list. One
  sentence, standard, and your payment provider may require it.
- **Accessibility statement.** You built this partly for your own vision.
  Saying so on the sales page is honest, is a genuine differentiator, and is
  the best answer to anyone asking what the tool is for.

## Before you publish

```
[ ] every [PLACEHOLDER] replaced, grep clean
[ ] entity question decided (own name, DBA, or LLC) and EULA names it
[ ] refund carve-out matched to what your payment provider actually does
[ ] checkout has the "immediate delivery, waive cancellation" tick
[ ] PRIVACY.md live at a public URL, and that URL in Partner Center
[ ] licences/ holds the full texts, versions confirmed against the build
[ ] FFmpeg build verified LGPL, not GPL — ffmpeg -version, no --enable-gpl
[ ] a lawyer has read the EULA and Terms at least once
```

That last line is the one worth spending money on. An hour of a software
lawyer's time against these drafts costs a few hundred dollars and is cheaper
than any one thing that goes wrong without it.
