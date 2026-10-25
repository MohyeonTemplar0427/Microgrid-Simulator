# Remaining 2025 ECC source retrieval

Research date: October 24, 2026. This is an access/evidence record, **not a
new rate source or permission to claim verified coverage**. The verified
January–June 2025 / January–September 2026 windows remain unchanged. After this
research, the user separately authorized an opt-in provisional model carrying
June's ECC through July–December 2025. Its replaceable study assumptions are
recorded in `2025-provisional-assumptions.json`; they do not close the evidence
gap described here.

## Exact evidence needed

For Rg1/Rg2 residential and Cg1/Cg6 small commercial non-demand service, obtain
the original Wisconsin Electric Volume 19 **sheet 20.2** applicable after June
2025 and the superseding sheet applicable to December 2025. Verify the actual
issue/effective dates, class rates, revision numbers and any intervening
adjustments from the documents themselves. Expected June/December adjustment
dates and expected revision numbers alone do not establish actual history.

The June 2025 issuer certificate verifies residential $0.00055/kWh and small
C&I $0.00050/kWh for that month. The January 2026 utility brochure verifies
$0.00052/kWh and $0.00047/kWh for its published period. Neither establishes all
of July–December 2025. A dated filed sequence can cover that gap; alternatively,
the actual applicable issuer monthly certificates plus explicit effective-date
evidence can establish each remaining month. A collections/remittances total in
a Form 10-D is not a class-specific rate and cannot supply the missing factor.

The official issuer's public asset index identifies these existing records:

- [July 2025 certificate](https://s22.q4cdn.com/994559668/files/doc_downloads/2025/08/July-2025-Monthly-Servicers-Certificate.pdf)
- [August 2025 certificate](https://s22.q4cdn.com/994559668/files/doc_downloads/2025/09/August-2025-Monthly-Servicers-Certificate.pdf)
- [September 2025 certificate](https://s22.q4cdn.com/994559668/files/doc_downloads/2025/10/September-2025-Monthly-Servicers-Certificate.pdf)
- [October 2025 certificate](https://s22.q4cdn.com/994559668/files/doc_downloads/2025/11/October-2025-Monthly-Servicers-Certificate.pdf)
- [November 2025 certificate](https://s22.q4cdn.com/994559668/files/doc_downloads/2026/November-2025-Monthly-Servicers-Certificate.pdf)

A December 2025 monthly certificate was not identified in that index; do not
invent its URL. The December distribution certificate concerns earlier billing
and collections periods and does not list the required rates. The issuer index
is available at [WEC Environmental Trust Financing](https://investor.wecenergygroup.com/investors/financial-info/WEPCO-Environmental-Trust-Financing/default.aspx).

## Public archival lead

The Internet Archive CDX index returns two HTTP-200 captures of the utility's
original official URL,
`https://www.we-energies.com/pdfs/etariffs/wisconsin/elecrateswi.pdf`:

| Capture UTC | Archive content digest | Compressed archival record length |
| --- | --- | ---: |
| August 5, 2025 04:16:08 | `XYDRFVTEO7UQB4HPIHO4FCBAOAF2CKBT` | 1,852,124 bytes |
| November 26, 2025 07:36:02 | `2WUJF37YOTVCTKA6ZQVE4SRE7GFR3NXZ` | 1,806,130 bytes |

The November capture could contain a prefiled December sheet, but its contents
have **not** been read. The digest/index entry alone does not verify a price.

- [August captured official ratebook](https://web.archive.org/web/20250805041608id_/https://www.we-energies.com/pdfs/etariffs/wisconsin/elecrateswi.pdf)
- [November captured official ratebook](https://web.archive.org/web/20251126073602id_/https://www.we-energies.com/pdfs/etariffs/wisconsin/elecrateswi.pdf)

PDF replay returned HTTP429. A subsequent HEAD response also returned429 with
no Retry-After header; no repeated PDF retry was made. Public CDX metadata
returned null archive filenames/offsets, so it did not expose an alternative
archival storage object. Do not claim either PDF's original-byte hash has been
verified or derive a tariff from the compressed record size.

## Other access findings

- The PSC's own customer-generation guidance points to
  `https://apps.psc.wi.gov/pages/tariffs.htm` and
  `https://apps.psc.wi.gov/pages/ERFhome.htm`. Both returned403 in direct public
  requests and the web reader. Earlier failed ERF query routes were not retried.
- Issuer-indexed certificate first-page PNG thumbnails also returned451. This
  did not provide an alternate format for the previously blocked PDF records.
- Common Crawl's exact-URL July/November 2025 index attempts returned504;
  another November index attempt failed upstream. Arquivo.pt exact-URL history
  returned no captures. Those access failures do not establish missing tariffs.
- Government URDB record
  [6859a625ee417fe3fa0cb0df](https://apps.openei.org/USURDB/rate/view/6859a625ee417fe3fa0cb0df)
  retains effective date June1,2025 but displays 2026 base energy $0.19342 and
  combined adjustment $0.00251 following its January8,2026 approval update.
  This inconsistent historical record was excluded rather than treating its
  "Expert Has Verified" label as sufficient evidence for 2025.

The known September 2025 fuel refund remains separately supported by the
[utility's August 28, 2025 notice](https://news.we-energies.com/refunds-expected-for-we-energies-electric-customers-from-fuel-cost-adjustment/):
$0.04054/kWh residential and $0.03620/kWh small C&I, applied to September use.
It does not close the ECC gap. These unsuccessful retrieval attempts added no
new verified rates. The subsequent explicit provisional-mode authorization
allows simulations without claiming that the missing filed factors have been
found or that a normal adjustment calendar proves their historical validity.
