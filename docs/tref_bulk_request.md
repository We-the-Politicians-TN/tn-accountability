# Bulk data request — Tennessee Registry of Election Finance

**Status:** not yet sent.

**To:** registry.info@tn.gov
**Phone:** (615) 741-7959
**Address:** WRS Tennessee Tower, 16th Floor, 312 Rosa L. Parks Avenue, Nashville, TN 37243

**CC (planned):** Rep. William Lamberth — rep.william.lamberth@capitol.tn.gov
District 44 (part of Sumner County), R-Portland
425 Rep. John Lewis Way N., Suite 602, Cordell Hull Bldg., Nashville, TN 37243 · (615) 741-1980

---

## Before you send: what copying a legislator commits you to

Rep. Lamberth is a sitting member. His filings will be in this database, and he may
appear in the patterns-for-review queue like anyone else. That is not a reason to avoid
copying him, but it sets three rules for how this email is written:

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
> Representative Lamberth — I've copied you as [my representative / for your awareness]
> in case your office can point me to the right person or process. I'm not asking you to
> intervene with the Registry, only to help me navigate it if that's appropriate.
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

- **Fix the bracketed phrase.** If Lamberth represents you, say "as my representative" —
  that is the strongest and most legitimate framing. If he does not, say "for your
  awareness" and consider whether copying him is worth it at all; copying a legislator who
  is not yours, about an agency that regulates him, reads differently.
- **"I'm not asking you to intervene" is load-bearing.** Leave it in. It is the sentence
  that makes this email safe to publish.
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
