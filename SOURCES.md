# Source vetting checklist

robots.txt is checked automatically before every request, so a site that disallows us is simply never read
(it will show as failing with a "robots.txt ... doesn't allow" error: remove it or look for another feed).

**Terms of use have to be checked by a person.** For each source, open its terms / copyright page and confirm it
doesn't forbid showing a headline, a short description and a link, or automated access. Tick it here when done.
Where a site publishes no terms, it is treated as open, like the rest of the web. After the first run, also
check `python -m labourpulse sources` (or the Actions run page): a feed address that has moved shows as failing.

| ✓ | Source | Language | Feed | Note |
|---|---|---|---|---|
| ☐ | Labor Notes | en | https://labornotes.org/rss.xml |  |
| ☐ | Equal Times | en | https://www.equaltimes.org/spip.php?page=backend&lang=en |  |
| ☐ | Payday Report | en | https://paydayreport.com/feed/ |  |
| ☐ | ITUC | en | https://www.ituc-csi.org/spip.php?page=backend&lang=en |  |
| ☐ | IndustriALL | en | https://www.industriall-union.org/feed | Feed address unconfirmed |
| ☐ | UNI Global Union | en | https://uniglobalunion.org/feed/ |  |
| ☐ | Peoples Dispatch | en | https://peoplesdispatch.org/feed/ |  |
| ☐ | Jacobin | en | https://jacobin.com/feed/ |  |
| ☐ | Tribune | en | https://tribunemag.co.uk/feed/ |  |
| ☐ | NACLA | en | https://nacla.org/rss.xml |  |
| ☐ | Africa Is a Country | en | https://africasacountry.com/feed |  |
| ☐ | Rest of World | en | https://restofworld.org/feed/latest | General tech outlet: labour stories only |
| ☐ | GroundXero | en | https://www.groundxero.in/feed/ |  |
| ☐ | Countercurrents | en | https://countercurrents.org/feed/ |  |
| ☐ | The India Forum | en | https://www.theindiaforum.in/rss.xml | Feed address unconfirmed |
| ☐ | Fairwork | en | https://fair.work/en/feed/ |  |
| ☐ | WIEGO | en | https://www.wiego.org/rss.xml | Feed address unconfirmed |
| ☐ | मज़दूर बिगुल (Mazdoor Bigul) | hi | https://www.mazdoorbigul.net/feed |  |
| ☐ | वर्कर्स यूनिटी (Workers Unity) | hi | https://www.workersunity.com/feed/ |  |
| ☐ | मेहनतकश (Mehnatkash) | hi | https://mehnatkash.in/feed/ |  |
| ☐ | जनचौक (Janchowk) | hi | https://janchowk.com/feed/ |  |
| ☐ | द वायर हिंदी (The Wire Hindi) | hi | https://thewirehindi.com/feed/ |  |
| ☐ | लोकसत्ता (Loksatta) | mr | https://www.loksatta.com/feed/ | Commercial daily (Indian Express group): check its terms carefully |
| ☐ | मॅक्स महाराष्ट्र (Max Maharashtra) | mr | https://www.maxmaharashtra.com/feed | Feed address unconfirmed |
| ☐ | Monthly Review | en | https://monthlyreview.org/feed/ |  |
| ☐ | MR Online | en | https://mronline.org/feed/ |  |
| ☐ | Spectre | en | https://spectrejournal.com/feed/ |  |
| ☐ | Salvage | en | https://salvage.zone/feed/ |  |
| ☐ | Notes from Below | en | https://notesfrombelow.org/feed.xml | Feed address unconfirmed |
| ☐ | Cosmonaut | en | https://cosmonautmag.com/feed/ |  |
| ☐ | Tricontinental | en | https://thetricontinental.org/feed/ |  |
| ☐ | Developing Economics | en | https://developingeconomics.org/feed/ |  |
| ☐ | ROAPE | en | https://roape.net/feed/ |  |
| ☐ | Global Labour Column | en | https://globallabourcolumn.org/feed/ |  |
| ☐ | ILO | en | https://www.ilo.org/rss.xml | Feed address unconfirmed since the ILO's 2024 site redesign |
| ☐ | GOV.UK (employment rights) | en | https://www.gov.uk/api/search.json?q=%22employment+rights%22&order=-public_timestamp&count=40 |  |
| ☐ | GOV.UK (minimum wage) | en | https://www.gov.uk/api/search.json?q=%22minimum+wage%22&order=-public_timestamp&count=40 |  |
| ☐ | GOV.UK (trade unions) | en | https://www.gov.uk/api/search.json?q=%22trade+union%22&order=-public_timestamp&count=40 |  |
| ☐ | Federal Register (US Dept of Labor) | en | https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=labor-department&order=newest&per_page=40 |  |
| ☐ | Federal Register (NLRB) | en | https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=national-labor-relations-board&order=newest&per_page=40 |  |

## Journals (Crossref API)

Crossref's metadata is openly reusable; nothing to check per journal except that the ISSN is the right one
(a wrong ISSN shows as failing or returns nothing).

| Journal | Online ISSN |
|---|---|
| Antipode | 1467-8330 |
| Capital & Class | 2041-0980 |
| Historical Materialism | 1569-206X |
| Review of Radical Political Economics | 1552-8502 |
| Science & Society | 1943-2801 |
| Global Labour Journal | 1918-7351 |
| Work, Employment and Society | 1469-8722 |
| Economic and Industrial Democracy | 1461-7099 |
| Industrial Relations Journal | 1468-2338 |
| International Labor and Working-Class History | 1471-6445 |
| Gender, Work & Organization | 1468-0432 |
| Feminist Economics | 1466-4372 |
| Journal of Agrarian Change | 1471-0366 |
| Development and Change | 1467-7660 |
| Review of International Political Economy | 1466-4526 |
| New Political Economy | 1469-9923 |
| Environment and Planning A | 1472-3409 |
| The Indian Journal of Labour Economics | 0019-5308 |

## Official records (law tracker)

| Source | Licence |
|---|---|
| UK Parliament Bills API | Open Parliament Licence v3.0 |
| Parliament of India (sansad.in) | Public API behind its own bill pages; nothing prohibits automated use |
| GOV.UK search API | Open Government Licence v3.0 |
| Federal Register API | US public domain |
