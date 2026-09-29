"""Where Labour Pulse reads from. Add, remove or edit entries freely.

Feeds (SOURCES) — each entry:
    name      shown on every card
    url       an RSS/Atom feed (or an official API, see "format")
    category  the stream its stories start in: "news", "theory", "policy" or "law" (see classify.py)
    lang      "en", "hi" or "mr"
    filter    True for general outlets: only stories about work and workers are kept (classify.is_labour).
              Labour-only outlets leave it out and every story is kept.
    format    "feed" (default), "govuk" (GOV.UK search API) or "federal_register" (US Federal Register API)
    skip      optional regular expression: headlines to leave out (routine notices)

Journals (JOURNALS) are read through Crossref's open API by ISSN; "filter": True keeps only articles
about work and workers (for broader journals).

Before a source goes live, check two things (see SOURCES.md):
  1. robots.txt — checked automatically before every request (feeds.allowed); a disallowed feed is never read.
  2. Terms of use — by hand: they must not forbid showing a headline, a short description and a link,
     or automated access. Mark the entry "terms": "checked" once you have looked.
Removed because they don't allow automated reading: ITUC and Global Labour Column (robots.txt), Countercurrents and
Janchowk (refuse our requests, 403). Global Labour Journal isn't registered with Crossref under its ISSN.
A feed that fails three runs in a row shows as failing in `python -m labourpulse sources`.
"""

_ROUTINE = r"^(Agency Information Collection|Proposed Extension of Information Collection|Sunshine Act|.*Meetings?;|.*Privacy Act of 1974)"

SOURCES = [
    # --- Struggles & news: labour movement press (English) ---
    {"name": "Labor Notes", "url": "https://labornotes.org/rss.xml", "category": "news", "lang": "en"},
    {"name": "Equal Times", "url": "https://www.equaltimes.org/spip.php?page=backend&lang=en", "category": "news", "lang": "en"},
    {"name": "Payday Report", "url": "https://paydayreport.com/feed/", "category": "news", "lang": "en"},
    {"name": "IndustriALL", "url": "https://www.industriall-union.org/feed", "category": "news", "lang": "en"},
    {"name": "UNI Global Union", "url": "https://uniglobalunion.org/feed/", "category": "news", "lang": "en"},
    {"name": "Peoples Dispatch", "url": "https://peoplesdispatch.org/feed/", "category": "news", "lang": "en", "filter": True},
    {"name": "Jacobin", "url": "https://jacobin.com/feed/", "category": "news", "lang": "en", "filter": True},
    {"name": "Tribune", "url": "https://tribunemag.co.uk/feed/", "category": "news", "lang": "en", "filter": True},
    {"name": "NACLA", "url": "https://nacla.org/rss.xml", "category": "news", "lang": "en", "filter": True},
    {"name": "Africa Is a Country", "url": "https://africasacountry.com/feed", "category": "news", "lang": "en", "filter": True},
    {"name": "Rest of World", "url": "https://restofworld.org/feed/latest", "category": "news", "lang": "en", "filter": True},
    # India (English)
    {"name": "GroundXero", "url": "https://www.groundxero.in/feed/", "category": "news", "lang": "en", "filter": True},
    {"name": "The India Forum", "url": "https://www.theindiaforum.in/rss.xml", "category": "news", "lang": "en", "filter": True},

    # --- Platform & domestic work ---
    {"name": "Fairwork", "url": "https://fair.work/en/feed/", "category": "news", "lang": "en"},
    {"name": "WIEGO", "url": "https://www.wiego.org/rss.xml", "category": "news", "lang": "en"},

    # --- Hindi ---
    {"name": "मज़दूर बिगुल (Mazdoor Bigul)", "url": "https://www.mazdoorbigul.net/feed", "category": "news", "lang": "hi"},
    {"name": "वर्कर्स यूनिटी (Workers Unity)", "url": "https://www.workersunity.com/feed/", "category": "news", "lang": "hi"},
    {"name": "मेहनतकश (Mehnatkash)", "url": "https://mehnatkash.in/feed/", "category": "news", "lang": "hi"},
    {"name": "द वायर हिंदी (The Wire Hindi)", "url": "https://thewirehindi.com/feed/", "category": "news", "lang": "hi", "filter": True},

    # --- Marathi (few labour outlets publish feeds: add the ones you read) ---
    {"name": "लोकसत्ता (Loksatta)", "url": "https://www.loksatta.com/feed/", "category": "news", "lang": "mr", "filter": True},
    {"name": "मॅक्स महाराष्ट्र (Max Maharashtra)", "url": "https://www.maxmaharashtra.com/feed", "category": "news", "lang": "mr",
     "filter": True},

    # --- Theory & debate ---
    {"name": "Monthly Review", "url": "https://monthlyreview.org/feed/", "category": "theory", "lang": "en"},
    {"name": "MR Online", "url": "https://mronline.org/feed/", "category": "theory", "lang": "en"},
    {"name": "Spectre", "url": "https://spectrejournal.com/feed/", "category": "theory", "lang": "en"},
    {"name": "Salvage", "url": "https://salvage.zone/feed/", "category": "theory", "lang": "en"},
    {"name": "Notes from Below", "url": "https://notesfrombelow.org/feed.xml", "category": "theory", "lang": "en"},
    {"name": "Cosmonaut", "url": "https://cosmonautmag.com/feed/", "category": "theory", "lang": "en"},
    {"name": "Tricontinental", "url": "https://thetricontinental.org/feed/", "category": "theory", "lang": "en"},
    {"name": "Developing Economics", "url": "https://developingeconomics.org/feed/", "category": "theory", "lang": "en"},
    {"name": "ROAPE", "url": "https://roape.net/feed/", "category": "theory", "lang": "en"},
    {"name": "Anvil", "url": "https://anvilmag.in/feed/", "category": "theory", "lang": "en"},

    # --- Policy & courts: official and institutional ---
    {"name": "ILO", "url": "https://www.ilo.org/rss.xml", "category": "policy", "lang": "en"},
    {"name": "GOV.UK (employment rights)", "format": "govuk", "category": "policy", "lang": "en",
     "url": "https://www.gov.uk/api/search.json?q=%22employment+rights%22&order=-public_timestamp&count=40"},
    {"name": "GOV.UK (minimum wage)", "format": "govuk", "category": "policy", "lang": "en",
     "url": "https://www.gov.uk/api/search.json?q=%22minimum+wage%22&order=-public_timestamp&count=40"},
    {"name": "GOV.UK (trade unions)", "format": "govuk", "category": "policy", "lang": "en",
     "url": "https://www.gov.uk/api/search.json?q=%22trade+union%22&order=-public_timestamp&count=40"},
    {"name": "Federal Register (US Dept of Labor)", "format": "federal_register", "category": "policy", "lang": "en",
     "skip": _ROUTINE,
     "url": "https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=labor-department&order=newest&per_page=40"},
    {"name": "Federal Register (NLRB)", "format": "federal_register", "category": "policy", "lang": "en", "skip": _ROUTINE,
     "url": "https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=national-labor-relations-board&order=newest&per_page=40"},
]

# --- Research: journals via Crossref (https://api.crossref.org), by ISSN. Metadata only: title, authors,
# date, link (the DOI) and, where the publisher deposited one, the abstract.
JOURNALS = [
    {"name": "Antipode", "issn": "1467-8330"},
    {"name": "Capital & Class", "issn": "2041-0980"},
    {"name": "Historical Materialism", "issn": "1569-206X"},
    {"name": "Review of Radical Political Economics", "issn": "1552-8502"},
    {"name": "Science & Society", "issn": "1943-2801"},
    {"name": "Work, Employment and Society", "issn": "1469-8722"},
    {"name": "Economic and Industrial Democracy", "issn": "1461-7099"},
    {"name": "Industrial Relations Journal", "issn": "1468-2338"},
    {"name": "International Labor and Working-Class History", "issn": "1471-6445"},
    {"name": "Gender, Work & Organization", "issn": "1468-0432"},
    {"name": "Feminist Economics", "issn": "1466-4372"},
    {"name": "Journal of Agrarian Change", "issn": "1471-0366"},
    {"name": "Development and Change", "issn": "1467-7660", "filter": True},
    {"name": "Review of International Political Economy", "issn": "1466-4526", "filter": True},
    {"name": "New Political Economy", "issn": "1469-9923", "filter": True},
    {"name": "Environment and Planning A", "issn": "1472-3409", "filter": True},
    {"name": "The Indian Journal of Labour Economics", "issn": "0019-5308"},
]
