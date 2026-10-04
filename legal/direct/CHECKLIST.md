# Launching on your own site or a marketplace

The cheap route, and the one that does not depend on anyone approving you.
Roughly in order.

## Decide the entity first

Everything else names it, so changing it later means editing every document.

- [ ] Decide: own name / DBA / LLC — see `../README.md` §2
- [ ] If DBA: register with the county or state ($10–100)
- [ ] Open a separate bank account for the business, whatever you chose
- [ ] Put the decision into every document (`[LEGAL NAME]` is already
      filled in as Alison Risner; change if you form an entity)

## Pick a payment provider

The single most consequential choice here, because it decides whether you
handle sales tax yourself.

| | Merchant of record | Fee | Notes |
|---|---|---|---|
| **Lemon Squeezy** | yes | ~5% + 50¢ | handles VAT/tax worldwide, licence keys built in |
| **Paddle** | yes | ~5% + 50¢ | same; more established, slightly heavier setup |
| **Gumroad** | yes | ~10% | simplest to start, highest fee |
| **Fourthwall** | check | varies | creator storefront; confirm whether it is MoR for digital goods before relying on it |
| **Stripe alone** | **no** | ~2.9% + 30¢ | cheapest, but *you* register for and remit sales tax in every jurisdiction |

**Merchant of record is worth the fee.** It means the provider is legally the
seller and deals with VAT, GST and US state sales tax. Doing that yourself as
a sole trader is a genuine ongoing burden, not a one-off.

- [ ] Choose a provider and confirm it is merchant of record
- [ ] Confirm it supports **licence keys**, or decide you do not need them
- [ ] Enable the **"digital goods / waive right of withdrawal"** checkout tick
      — this is what makes the refund policy hold up in the EU and UK
- [ ] Test a real purchase end to end, with a real card, and refund yourself

## Publish the documents

- [ ] `shared/EULA.md` — fill placeholders, ship in installer and install folder
- [ ] `shared/TERMS-OF-USE.md` — ship and publish
- [ ] `shared/PRIVACY-POLICY.md` — publish at `https://ontherisedigital.lemonsqueezy.com/privacy`
- [ ] `shared/THIRD-PARTY-LICENCES.md` — ship, and link from About
- [ ] `direct/TERMS-OF-SALE.md` — publish, link from checkout
- [ ] `direct/REFUND-POLICY.md` — publish, link from checkout **and** the
      product page, where buyers look for it
- [ ] `direct/WEBSITE-TERMS.md` — publish
- [ ] `direct/COOKIE-NOTICE.md` — pick version A or B, publish
- [ ] `direct/SUPPORT-POLICY.md` — publish
- [ ] `direct/INSTALL.md` — download page, confirmation email, and
      `READ-ME-FIRST.txt` beside the installer

```bash
grep -rn "\[SUPPORT EMAIL\]\|\[WEBSITE\]\|\[STATE\]\|\[DATE\]\|\[PRODUCT\]\|\[PROVIDER\]\|\[VERSION\]" legal/
```

Nothing ships until that comes back clean.

## Signing

- [ ] Decide: sign or do not sign (see `../../RELEASING.md`)
- [ ] If signing: **Azure Artifact Signing**, ~$120/yr, individuals in US and
      Canada — the cheapest real option
- [ ] Do **not** buy EV — it no longer bypasses SmartScreen
- [ ] If not signing: `INSTALL.md` is doing the work instead; make sure it is
      in front of every buyer before they download
- [ ] Publish the installer's SHA-256 on the download page either way

## The product page

- [ ] What it does, in one sentence, above the fold
- [ ] Screenshots of the real interface
- [ ] System requirements, stated plainly
- [ ] **What it does not do**, and that third-party services can change —
      honesty here prevents refunds later
- [ ] Price, with tax handling made clear
- [ ] Links to refund policy, EULA, privacy
- [ ] Accessibility note, if it applies to the product
- [ ] An email address that works

## Before you take the first payment

- [ ] Buy your own product with a real card, from a different browser
- [ ] Confirm the delivery email arrives, and check it is not in spam
- [ ] Install from the delivered link on a clean machine with neither yt-dlp
      nor ffmpeg present
- [ ] Walk through `INSTALL.md` exactly as a customer would, SmartScreen
      included
- [ ] Refund yourself and confirm the process works
- [ ] Reply to your own support email and time how long you took

## After launch

- [ ] Keep a record of every sale for tax purposes, even with an MoR
- [ ] Note which questions arrive twice — that is your FAQ writing itself
- [ ] Set a reminder to review the documents at every major version
