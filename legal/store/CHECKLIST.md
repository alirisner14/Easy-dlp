# Submitting to the Microsoft Store

Shorter than the direct-sale list, because Microsoft handles most of it.
See `SUBMISSION.md` for the detail behind each line.

## Before you register

- [ ] **Settle the entity question** — Company verification wants a
      registered business, and Partner Center **cannot** convert an
      Individual account into a Company one later. See `../README.md` §2.

## Account

- [ ] Register at <https://storedeveloper.microsoft.com> — and only there.
      Free. Any other entry point charges $19/$99.
- [ ] Choose **Company** (selling relates to a business or profession)
- [ ] Complete identity verification — ID and selfie; allow a few days
- [ ] Reserve the product name in Partner Center (free, immediate)

## Documents

- [ ] `shared/PRIVACY-POLICY.md` **published at a public URL** — required,
      and the submission cannot proceed without it
- [ ] `shared/EULA.md`, edited for the Store:
  - [ ] refund section replaced with "Microsoft's policy applies"
  - [ ] delivery, licence keys and chargebacks removed
- [ ] `shared/TERMS-OF-USE.md` included
- [ ] `shared/THIRD-PARTY-LICENCES.md` inside the package and in the About box
- [ ] Support email that is monitored

**Not needed on this route:** Terms of Sale, Refund Policy, Website Terms,
Cookie Notice, install instructions.

## Package

- [ ] Build the MSIX (MSIX Packaging Tool, recorded on a clean VM)
- [ ] **Do not buy a code-signing certificate** — Microsoft signs MSIX free
- [ ] Run the Windows App Certification Kit locally and fix what it finds
- [ ] Test the installed package: settings and data land in the redirected
      `%APPDATA%`, and nothing tries to write beside the executable

## Listing

- [ ] Short description — one accurate line
- [ ] Full description — **opens with the dependency disclosure** (policy
      10.2.4): name the bundled open-source tools in the first lines
- [ ] Screenshots of the real interface, 1366×768 or larger
- [ ] Store logo, 300×300
- [ ] Category: Utilities & tools
- [ ] Search terms — seven maximum, relevant (policy 10.1.3)
- [ ] Age rating questionnaire completed
- [ ] Limitations stated plainly in the description (policy 10.1.1)

## Submit

- [ ] Submit and wait — certification takes a few days
- [ ] If rejected, read the policy number cited. Mechanical failures are
      fixable and you resubmit. A 10.1.6 rejection is about what the product
      is, and means falling back to `../direct/CHECKLIST.md`
- [ ] Keep the Store version number ahead of any direct-download version, or
      customers with both get confusing results

## Worth knowing

- `%APPDATA%` is redirected under MSIX, so a Store install and a direct
  install do not share settings or queue.
- Store installs never show a SmartScreen warning. This is the main thing you
  are buying with the extra effort.
- Updates are automatic — the OS checks every 24 hours.
