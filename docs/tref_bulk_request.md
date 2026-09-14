# Bulk data request — Tennessee Registry of Election Finance

**Status:** not yet sent.
**To:** registry.info@tn.gov
**Phone:** (615) 741-7959
**Address:** WRS Tennessee Tower, 16th Floor, 312 Rosa L. Parks Avenue, Nashville, TN 37243

This is the **primary source** — the agency that publishes the data the Accountability
Project copied. Ask informally first; agencies often provide extracts without a formal
process. If declined, the Tennessee Public Records Act is the formal route (check the
current rules on eligibility and fees at that point).

## Draft email

> **Subject:** Request for bulk campaign finance data — contributions and expenditures
>
> Hello,
>
> I'm building a free, public website that helps Tennesseans see their state
> legislators' campaign finance records alongside the bills those legislators sponsor
> and vote on. It is non-commercial and entirely open source — the code and methodology
> are public at https://github.com/We-the-Politicians-TN/tn-accountability
>
> I'm writing to ask whether the Registry can provide bulk copies of the contribution
> and expenditure records that are searchable at apps.tn.gov/tncamp — ideally as CSV or
> another delimited export covering all years available, for state House and Senate
> candidates and their committees.
>
> I can collect these records through the public search interface, and I've begun doing
> so, but that requires many thousands of paginated requests against your server. A
> single bulk extract would be far less load on your systems than my collecting the same
> records page by page, which is the main reason I'm asking.
>
> If a bulk extract is possible, I'd be glad to know:
>   - what formats and date ranges are available
>   - whether there are any fees, and what they would be
>   - whether there's a preferred process or form I should use
>   - whether any fields differ from those in the web export
>
> If it's easier to discuss by phone, I'm happy to call.
>
> Thank you for your time.
>
> [Your name]
> [Your phone]

## Notes

- Leading with the server-load argument is deliberate: it is true, and it reframes the
  request as helping them rather than asking a favor.
- Do not stop the scraper while waiting. Phase 7 needs ongoing TREF ingest regardless,
  and this request may take weeks or go nowhere.
- If they provide files, save them to `data/raw/tref/<date-received>/` **unrenamed**, and
  record the request and response in this file for the evidence trail.
