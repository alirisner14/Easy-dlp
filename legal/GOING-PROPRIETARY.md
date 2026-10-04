# Closing the source

What changing the licence does, what it cannot do, and the order to do it in.

## What has been done

`LICENSE` now reads proprietary, with the MIT text kept below it and a dated
line saying what that old grant still covers. **Keeping the old licence
visible is deliberate** — deleting it would misrepresent the terms that
versions already published went out under, and anyone who looks at the git
history will find it anyway. A clear, dated boundary is both honest and
easier to defend than a quiet deletion.

## What a licence change cannot do

**MIT is irrevocable for copies already released.** Anyone who obtained the
code under it keeps the right to use, modify and redistribute *that copy*,
permanently, and you cannot take it back. The same is true of any fork or
clone made while the repository was public.

What you can do is close everything from here forward. Your position rests on
your paid releases being newer and better than the last free one — which, in
practice, is the model a lot of commercial software runs on.

Your situation is about as good as it gets: the repository has never been
advertised, has no release tags, and nobody has had a reason to look for it.
The realistic exposure is close to zero. It is still worth doing the steps
below rather than assuming.

## Do these in order

### 1. Make the repository private

GitHub → the repo → Settings → scroll to **Danger Zone** → *Change
repository visibility* → **Make private**.

Before you do, know what it changes:

- Existing forks of a public repo **do not become private**. Check for forks
  first — the fork count is on the repo's main page. If it is zero, there is
  nothing to worry about.
- GitHub Pages stops working on a private repo unless you have Pro. Nothing
  here depends on that.
- Anyone you have given access keeps it. Check Settings → Collaborators.

### 2. Check what is already out there

```bash
git log --oneline | wc -l
git tag
```

No tags means no releases were published, so there is no built binary sitting
on a releases page for anyone to find.

Search GitHub for the project name while it is still public — if nothing
comes back but your own repo, nothing was copied.

### 3. Decide about the history

The git history still contains every MIT-licensed commit. That is fine and
you do not need to rewrite it. It is a record of what was true at the time,
and the dated note in `LICENSE` explains the transition.

**Do not rewrite history to hide it.** It would not help — the old grant
stands regardless of whether the commits are visible — and it would destroy
the record you may one day want, showing you wrote this and when.

### 4. Update what the repository says about itself

- [x] `LICENSE` — done
- [ ] `README.md` — remove or amend anything describing it as open source,
      and anything inviting contributions
- [ ] Repository description and topics on GitHub
- [ ] Add a short "this is proprietary software" line near the top of the
      README, so it is unambiguous to anyone with access

### 5. Decide about contributions

A private proprietary repo takes no outside contributions, which removes the
question. If you ever open parts of it again, you will need a contributor
licence agreement before accepting a patch — otherwise you do not own all of
what you are selling. Not a problem today; worth knowing before you invite
anybody in.

## What stays open regardless

The third-party components keep their own licences no matter what you do with
yours:

- **yt-dlp** — Unlicense, public domain. No obligations.
- **FFmpeg** — LGPL. You must ship the licence text, state that it is
  unmodified and separately invoked, and offer the source. Closing your own
  source does not touch this.
- **Python, Pillow, Tcl/Tk** — permissive, notices required.

See `shared/THIRD-PARTY-LICENCES.md`. **Going proprietary does not release you
from any of it.** If anything it matters more, because a paid product that
quietly drops required notices is a clearer problem than a hobby project that
does.

## The honest trade

Closing the source protects the thing you are selling. It also means nobody
can read the code to satisfy themselves it does what you say — which, for a
tool that handles browser cookies and runs downloads, is a reasonable thing
for a buyer to want.

You can answer that without opening the source: publish the installer's
SHA-256, be specific in the privacy policy about what is and is not sent
anywhere (already done — it is the strongest section in there), and say
plainly which open-source tools are inside and what they do. That is most of
the reassurance, without giving away the product.
