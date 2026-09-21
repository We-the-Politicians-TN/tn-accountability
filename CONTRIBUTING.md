# Checking this work, and contributing to it

This project makes claims about named public officials. Its only real defence is that
the method is published and anyone can check it. So the most valuable contribution is
not code — it is **finding something we got wrong**.

## If you think a figure is wrong

[Open an issue](https://github.com/We-the-Politicians-TN/tn-accountability/issues).
Include the page, the figure, and what you believe it should be. If you can point to
the original filing or bill page, better still.

**This applies to legislators and their staff too.** If a figure about you is wrong we
want to correct it, and we will. You do not need an account here to say so — the
contact address on the site works.

We have already found and fixed errors of exactly this kind, including one where
$184,500 of restaurant and hotel contributions was counted as health care money
because a pattern matching `HOSPITAL` also matched `HOSPITALITY`. That was caught by
reading one generated report line by line against its sources. Assume there are more.

## How to check a figure yourself

Everything traces to a primary source.

1. **Campaign finance** — search the donor or recipient at
   [apps.tn.gov/tncamp](https://apps.tn.gov/tncamp). Every contribution we store keeps
   the date, amount and donor name exactly as filed, plus the report it came from.
2. **Bills and votes** — look up the bill at
   [capitol.tn.gov](https://wapp.capitol.tn.gov/apps/indexes/). Sponsor, introduction
   date and status should match what we show.
3. **Our own record** — every stored row names the file and line it was loaded from,
   and every ingest run is logged in `data_pulls`.

The [data dictionary](docs/data_dictionary.md) describes every table and column, and
is generated from the live database so it cannot drift.

## What to be sceptical about

We would rather point these out than have you find them.

- **Donor industry is assigned by us**, mostly from name patterns. It is the weakest
  link in the chain, and the error above came from exactly here.
- **Name matching** connects campaign finance filers to legislators. Tennessee has
  three sitting Brookses, three Johnsons, three Joneses, and `BARRETT` differs from
  `GARRETT` by one letter. Matches below a confidence threshold are held back until a
  human confirms them, and unconfirmed matches count for nobody.
- **Timing means very little.** Tennessee bars contributions during session, so nearly
  every member raises money in the same months and nearly every bill has money behind
  it. See [the methodology findings](docs/methodology_findings.md).
- **Coverage is incomplete** in ways we state on the site rather than hide.

## Running it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in a Supabase connection string
PYTHONPATH=src python -m tn_accountability.migrate
```

Then `python -m tn_accountability.healthcheck` to see the state of the data, or
`python -m tn_accountability.site_build --serve` to build and browse the site locally.

`STATUS.md` records every significant decision and why it was made — read it before
changing anything. It is append-only: if a decision is reversed, add a new entry
saying so rather than editing the old one.

## If you want to write code

- **Tests first for classification rules.** `tests/test_classify.py` exists because
  prefix matching is silently wrong when one industry's word starts another's. Every
  case in that file was a real production error.
- **Never aggregate money and bill counts in the same join.** It multiplies one by the
  other. That mistake once produced a $70.6M figure for a legislator who raised
  $342,925, and has recurred three times in different forms.
- **Never modify anything under `data/raw/`.** Those files are the evidence trail.
  Move failed attempts aside instead of deleting them.
- **The language rules are enforced at build time**, and the build fails rather than
  publishing a violation. The site describes patterns; it does not allege wrongdoing.

## Contributing local knowledge

You do not need to write code to help. The things we most need are judgement calls a
Tennessean can make and an algorithm cannot:

- **Which industry a PAC belongs to.** Opaque names like `WSWT POLITICAL ACTION
  COMMITTEE` or `FRIENDS OF THA` are currently uncategorised; $11.6M of organisation
  money is waiting on exactly this.
- **Whether a filer name is really a given legislator**, particularly for common
  surnames and nicknames.
- **Whether a bill's subject is right.** LegiScan's labels are broad, and our mapping
  to industries is ours, not theirs.
