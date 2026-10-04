# Microsoft Store submission

**On the Rise Digital** — Alison Risner

What the Store needs, and — more usefully — what it does **not**, because
that is the whole argument for this route.

---

## What Microsoft does for you

Going through the Store means Microsoft takes over most of the apparatus of
selling software. These are the documents and systems you do **not** need:

| You would need, selling direct | On the Store |
|---|---|
| Terms of Sale | Microsoft is the seller; its terms govern the sale |
| Refund Policy | Microsoft's policy applies and overrides yours |
| Code-signing certificate ($120–500/yr) | Microsoft signs the MSIX, free |
| Installer hosting and bandwidth | Microsoft hosts it |
| Licence key system | Store entitlements handle it |
| Update mechanism | the OS checks every 24 hours |
| Sales tax / VAT registration and remittance | Microsoft is merchant of record worldwide |
| Chargeback handling | Microsoft's problem |
| Website, website terms, cookie notice | not required |
| SmartScreen install instructions | a Store install never warns |

That last one is easy to undervalue. A Store install is clean on day one. No
amount of money buys that anywhere else.

## What you still need

### Required by the Store

1. **Privacy policy at a public URL.** Non-negotiable, even though the app
   collects nothing. Use `shared/PRIVACY-POLICY.md`, publish it, give the
   URL in Partner Center. A GitHub Pages site or a gist is acceptable — it
   must simply be publicly reachable and stay reachable.
2. **Support contact.** An email address that works and is monitored.
3. **Age rating.** Completed through the IARC questionnaire in Partner
   Center. Answer honestly; for a utility this takes two minutes and comes
   back rated for everyone.
4. **Store listing** — see below.
5. **Dependency disclosure.** Policy 10.2.4 requires that software your
   product depends on be disclosed **at the start of the description**. Name
   the bundled open-source tools in the first lines.

### Optional but worth having

6. **Your own EULA.** If you supply none, Microsoft's Standard Application
   Licence Terms apply by default. Those are reasonable, but they do not
   contain your no-AI-training clause, your no-redistribution clause, or your
   commercial-use restriction. Supply `shared/EULA.md` with the
   Store-specific sections adjusted — see below.
7. **Terms of Use.** `shared/TERMS-OF-USE.md`, as the acceptable-use terms.
8. **Third-party licence notices.** `shared/THIRD-PARTY-LICENCES.md`, shipped
   inside the package and shown in the About box. Still a licence condition;
   the Store does not change that.

### EULA changes for the Store

If you supply your own EULA, edit these before submitting:

- **Section 9 (Refunds)** — replace with a line stating that purchases made
  through the Microsoft Store are governed by Microsoft's refund policy.
  Yours does not apply and claiming otherwise will read badly in
  certification.
- **Section 2.2 (devices)** — Store licences already follow the account
  across devices. Keep the clause; just do not contradict how the Store
  actually behaves.
- **Delivery, keys, chargebacks** — remove any mention. None of them exist
  on this route.

## The listing

| Field | Notes |
|---|---|
| Product name | reserved in Partner Center; reserve it early, it is free |
| Short description | one line, what it does, no marketing noise |
| Full description | **open with the dependency disclosure** (policy 10.2.4) |
| Screenshots | at least one; 1366×768 or larger. Show the real interface |
| Store logo | 300×300; the existing logo works |
| Category | Utilities & tools |
| Search terms | maximum seven, and they must be relevant (policy 10.1.3) |
| Privacy policy URL | required |
| Support contact | required |
| Age rating | IARC questionnaire |

**Write the description to describe the product accurately.** Policy 10.1.1
requires that all aspects accurately describe functions, features and
important limitations. Stating the limitations plainly — that it depends on
third-party services and that those can change — is both required and the
honest thing.

## Certification

Takes a few days. Rejections cite the policy number, which is the useful
part: it tells you whether the problem is mechanical (fixable, resubmit) or
about what the product is (reconsider).

Before submitting, run the
[Windows App Certification Kit](https://learn.microsoft.com/windows/uwp/debug-test-perf/windows-app-certification-kit)
against the `.msix` locally. It catches most mechanical failures in minutes
instead of days.

## The risk, stated plainly

For a product that saves video from third-party services, the policies that
matter are **10.1.6 / 10.2** — if your product accesses or monetizes access
to content from a third-party service, you must be specifically permitted to
under that service's terms — and **11.2** on intellectual property.

Certification is discretionary. The only way to find out is to submit, and
submitting is now free. See `../../RELEASING.md` for why that reverses the
usual order: try the free route first, and fall back to direct selling if it
is refused, rather than paying for the expensive route up front.

## Account type

Choose **Company**, not Individual. Microsoft's split is whether distribution
relates to your business, trade or profession — selling does.

**Partner Center cannot convert an Individual account to a Company one.**
Getting this wrong means starting over. Company verification wants a
registered business, which is why the entity question in
`../README.md` has to be settled before you register.

Start at <https://storedeveloper.microsoft.com> — registration is free there.
Any other entry point lands you in the legacy flow that still charges.
