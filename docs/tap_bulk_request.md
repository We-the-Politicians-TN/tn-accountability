# Bulk data request — The Accountability Project

**Status:** not yet sent.
**Where:** https://forms.gle/QenrjhaUfkWZGQf67 — their "contact us" form, linked from the
search guide's note about the download cap. They publish no email address.

## Why we are asking

Their search guide says: "Downloads are capped at 10,000 rows. If you are looking for
more data than this, please contact us." The Tennessee contributions dataset is
2,027,069 rows, so the cap returns 0.5% of it.

We are not blocked on this — we are pulling the same records directly from TREF, which is
where they got theirs. What their copy adds is the **normalized name and address
columns**, which would save real work in Phase 6 donor clustering. Worth asking for; not
worth waiting for.

## Draft message

> I'm building a public, open-source accountability site for Tennessee state legislators,
> linking campaign finance records to bill sponsorships and votes. The code and
> methodology are public at
> https://github.com/We-the-Politicians-TN/tn-accountability
>
> I'd like to use your Tennessee campaign contributions (dataset 395, 2,027,069 records)
> and campaign expenditures (dataset 428, 483,587 records) datasets. The search guide
> notes downloads are capped at 10,000 rows and to contact you for more, so I'm writing
> to ask whether bulk copies of those two Tennessee files are available.
>
> What's most valuable to me is your normalized columns — the cleaned donor names and
> addresses. I'm also collecting the underlying records directly from the Tennessee
> Registry of Election Finance, following the approach in your own `get_tn_contribs.R`,
> so I have a path forward either way; your normalization would save duplicated effort
> and keep my figures comparable to yours.
>
> Happy to credit The Accountability Project prominently on the site and in the repo, and
> to share back anything useful — including a note that the TREF app has moved from
> /tncamp-app/ to /tncamp/, which breaks that script as written.
>
> Thank you for making this data available.

## If they say yes

Save the files to `data/raw/accountability_project/` **without renaming them**, then load
them alongside the TREF data. Their records stop at 2023, so TREF remains the source for
everything after that regardless.
