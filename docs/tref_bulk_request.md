# Bulk data request — Tennessee Registry of Election Finance

**Status:** not yet sent.

**To:** registry.info@tn.gov
**Phone:** (615) 741-7959
**Address:** WRS Tennessee Tower, 16th Floor, 312 Rosa L. Parks Avenue, Nashville, TN 37243

**CC:** Rep. William Lamberth — rep.william.lamberth@capitol.tn.gov — **my representative**,
and the only member who has responded to me in the past.
District 44 (part of Sumner County), R-Portland
425 Rep. John Lewis Way N., Suite 602, Cordell Hull Bldg., Nashville, TN 37243 · (615) 741-1980

---

## Before you send: what copying a legislator commits you to

Lamberth represents District 44, which covers the sender — so this is constituent
service, the most legitimate footing there is, and he has a track record of responding.

He is also a sitting member whose filings will be in this database, and who may appear in
the patterns-for-review queue like anyone else. Both things are true at once. That does
not argue against copying him; it sets three rules for how this email is written:

1. **It must survive being forwarded.** Assume TREF's director, Lamberth's staff, and a
   reporter all read it. Nothing in it should read differently to those three audiences.
2. **It must not ask him to lean on the agency.** Asking a legislator to pressure a
   regulator on your behalf is the thing you would flag if someone else did it. The ask
   is for help navigating a process, nothing more.
3. **It must state what the project is, plainly.** Understating it and being discovered
   later is far worse than being straightforward now.

The draft below follows all three. **Do not soften the description of the project to make
the ask easier** — the accuracy of that paragraph is what protects you later.

---

## Draft email

> **To:** registry.info@tn.gov
> **CC:** rep.william.lamberth@capitol.tn.gov
> **Subject:** Request for bulk campaign finance data — contributions and expenditures
>
> Hello,
>
> I'm writing to ask whether the Registry can provide bulk copies of the contribution and
> expenditure records that are publicly searchable at apps.tn.gov/tncamp.
>
> I'm building a free, non-commercial website that presents Tennessee state legislators'
> publicly filed campaign finance records alongside the bills they sponsor and vote on, so
> that any citizen can look up their own representative and see both in one place. The
> project is entirely open source — the code, the database design, and the methodology are
> public at https://github.com/We-the-Politicians-TN/tn-accountability, and I intend to
> keep them public precisely so the work can be checked by anyone, including the officials
> it covers.
>
> Specifically, I'm asking for contributions and expenditures for state House and Senate
> candidates and their committees, for 2019 through the present, as CSV or any delimited
> format you already produce.
>
> I can collect these records through the public search interface, and I have begun doing
> so. But that requires many thousands of paginated requests against your servers to
> retrieve data you could export once. A single bulk extract would put substantially less
> load on your systems than my continuing to page through the search results, which is the
> main reason I'm writing rather than simply carrying on.
>
> If an extract is possible, I would appreciate knowing:
>
> - what formats and date ranges are available
> - whether any fees apply, and what they would be
> - whether there is a preferred form or process I should use
> - whether the extract includes any fields not present in the web export
>
> Representative Lamberth — I've copied you as my representative. You've been responsive
> when I've written before, which is why I'm asking you rather than anyone else. If your
> office can point me toward the right person or process at the Registry, I'd be grateful.
> I'm not asking you to intervene on my behalf, only to help me navigate it.
>
> I'll add that I expect your own filings to be in this data, along with every other
> member's, and they'll be presented the same way — the records as filed, next to the
> bills, with the methodology published so anyone can check it.
>
> I'm happy to discuss any of this by phone.
>
> Thank you for your time,
>
> [Your name]
> [Your phone]
> [Your address, if writing as a constituent]

---

## Notes on the draft

- **"I'm not asking you to intervene" is load-bearing.** Leave it in. It is the sentence
  that makes this email safe to publish.
- **The paragraph about his own filings is deliberate.** It would be easy to leave out,
  and leaving it out would be the beginning of a problem: asking a legislator for help
  with data that covers him, without saying so, is something you would have to explain
  later. Saying it up front costs one sentence and removes the issue permanently. It also
  tells him the terms honestly, which is what you would want in his position.
- **Alternative to a CC:** a CC on an agency email is easy to read as FYI. If nothing
  happens in two weeks, send him a short separate note — "I wrote to the Registry on
  [date] asking about bulk data; is there someone in your office who could help me reach
  the right person?" — which is far more actionable than a copied thread.
- The server-load argument is true and does real work: it reframes the request as reducing
  their burden rather than adding to it.
- The project description is deliberately neutral — "presents records alongside bills,"
  not "exposes" or "investigates." That matches the language rules in PLAN.md Phase 8 and
  is how the site itself will read.
- **Do not stop the scraper while waiting.** Phase 7 needs ongoing TREF ingest regardless,
  and this request may take weeks or go nowhere.

## If they provide files

Save to `data/raw/tref/<date-received>/` **unrenamed**, and record the request, the
response, and who sent it in this file. Provenance for agency-supplied data matters as
much as for scraped data.
