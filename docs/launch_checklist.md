# Pre-launch checklist

The site is built and runs. These are the things to settle **before** pointing
wethepoliticianstn.com at it. Ordered by how much damage getting them wrong would do.

## Must do before launch

- [ ] **Two people who are not you review five legislator pages each** (PLAN.md Phase 10).
      Ask them one question: *is every claim here backed by a number you could defend
      to the person it is about?* Do not tell them what to look for.
- [ ] **Read the Garrett page as if you were his staff.** It is the page you have
      looked at most, which makes it the one you are least likely to see clearly.
- [ ] **Review the donor categories** (`data/processed/donor_categories_to_review.csv`).
      This is the weakest link: it is where the $184,500 hospitality-as-health-care
      error came from, and **$11.6M of organisation money is still uncategorised**.
- [ ] **Confirm the 95 pending filer-name matches.** Until confirmed, that money is
      attributed to nobody — figures currently understate.
- [ ] **Collect the missing 2023 contributions.** TREF returns HTTP 500 for that year.
      Any 2023 analysis is incomplete until it is resolved, and the site does not
      currently say which year is missing on every page.
- [ ] **Decide the legal footing** (see the earlier discussion): an entity protects
      less than people assume, and the real protection is editorial. A media lawyer
      should see the actual site, not a description of it. The Reporters Committee for
      Freedom of the Press runs a free hotline.

## Should do before launch

- [ ] Add repository secrets so the scheduled jobs run: `DATABASE_URL`,
      `LEGISCAN_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
- [ ] Trigger each workflow manually once and confirm it completes.
- [ ] Verify the filing deadline dates in `filing_calendar.md` with the Registry —
      they are currently **unverified**.
- [ ] Run `python -m tn_accountability.healthcheck` and clear anything marked FAIL.
- [ ] Send the two bulk-data requests, still outstanding.

## After launch

- [ ] Monthly: the health check runs on the 1st and opens an issue if needed.
- [ ] Watch the issue tracker for corrections, including from legislators' offices.
      Respond to those quickly and publicly — how corrections are handled is itself
      evidence of good faith.
- [ ] Extend backwards. Contribution data exists to 2002; the backfill is resumable
      and the schema already handles earlier General Assemblies.

## What to say if asked "why are there more Republicans on your patterns page?"

Because Republicans hold supermajorities in both chambers and therefore most
leadership and committee positions, which attract contributions. The method takes no
account of party at any point: the same thresholds apply to everyone, nothing is added
or removed by hand, and both parties appear at both extremes of every distribution.
The methodology page states this, and the ratio table by party is published rather
than omitted.

Being able to answer this calmly, with the numbers already on the site, is worth more
than any disclaimer.
