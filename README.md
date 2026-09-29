# Labour Pulse

A free, non-commercial, worldwide briefing on work and workers: strikes and organising, platform and domestic
work, policy and courts, labour law, Marxist and radical theory, and new research. It reads open sources in
English, Hindi and Marathi every 6 hours, sorts every story with keyword rules (no AI model, no paid service)
and links every card to the original.

Built on the design of [AI Pulse](https://github.com/shru14/ai-pulse) by shru14, whose fetcher, country
detector and parliament readers are reused here with credit.

## Streams

| Stream | What's in it |
| --- | --- |
| **Struggles & news** | Strikes, organising, unions and workplaces, from the labour and left press |
| **Platform & domestic work** | Gig, app-based, domestic and care work. A lens across every stream: a platform law also shows in the law tracker, a paper on gig work also in Research |
| **Policy & courts** | Governments, ministries, courts, tribunals and the ILO acting on work |
| **Labour law tracker** | Bills and laws. UK and Indian parliamentary bills come from official records with every stage dated; laws reported in the news anywhere are added by the rules; Indian state laws can be added by hand in `data/laws.json` |
| **Theory & debate** | Marxist and radical political economy writing |
| **Research** | New articles from ~18 journals (Antipode, Capital & Class, Historical Materialism, Global Labour Journal, RRPE, …) via Crossref |

Every story is tagged with the countries it names (193 places, plus Indian and US states), its language
and topics (Strike, Wages, Domestic work, Care work, Migrant labour, Informal sector, Marxist theory, …).
The same event reported by several outlets is one card.

## Putting it online (about 15 minutes, free)

1. **Make a GitHub account** at <https://github.com/signup> if you don't have one.
2. **Create a repository**: the **+** menu (top right) → *New repository*. Name it `labour-pulse`, choose
   **Public** (Actions and Pages are free for public repositories), and create it.
3. **Upload the files**: on the new repository's page, click *uploading an existing file*, then drag in
   everything from the unzipped `labour-pulse` folder, *including* the hidden `.github` folder. (On a Mac, press
   Cmd+Shift+. in Finder to show hidden folders; on Windows, View → Show → Hidden items.) Click *Commit changes*.
   If the `.github` folder won't drag in, create the file by hand instead: *Add file* → *Create new file*, type
   `.github/workflows/pages.yml` as the name, and paste in that file's contents.
4. **Turn on Pages**: *Settings* → *Pages* → under *Build and deployment*, set *Source* to **GitHub Actions**.
5. **Run it once**: *Actions* tab → *Collect and publish* → *Run workflow*. The first run reads a month of
   history and takes 10–20 minutes. When it turns green, your site is at
   `https://YOUR-GITHUB-NAME.github.io/labour-pulse/`.
6. **Optional**: *Settings* → *Secrets and variables* → *Actions* → *New repository secret*, named
   `CROSSREF_MAILTO`, with your email address. Crossref then gives our requests its faster "polite" service.

After that it updates itself every 6 hours. Each run's page (Actions tab) lists any source that failed.

## Changing things

Everything can be edited in the browser on GitHub (open a file, click the pencil icon, commit). Each commit
re-runs the site.

- **Add or remove a source**: `labourpulse/sources.py`. Any RSS or Atom feed works. Check its terms first
  (see `SOURCES.md`); robots.txt is checked automatically on every run.
- **Add a journal**: add its name and online ISSN to `JOURNALS` in the same file.
- **Add a law by hand** (e.g. a state gig workers' act): `data/laws.json` explains the format.
- **Change how stories are sorted or tagged**: `labourpulse/classify.py`. Every rule is a list of words in
  English, Hindi and Marathi. The next run re-sorts stored stories with your changes.
- **Rename the site**: `labourpulse/config.py`.

## Run it on your own computer (optional)

Needs Python 3.10 or newer; nothing else to install.

```
python -m labourpulse collect     # read every source into labourpulse.db
python -m labourpulse serve       # build the site and open it at http://127.0.0.1:8000
python -m labourpulse sources     # which sources are answering
python -m pytest -q               # tests (pip install pytest first)
```

## How it stays legal and polite

1. **robots.txt must allow us.** Every request first reads the site's robots.txt; a disallowed URL is never
   fetched, and a robots.txt that refuses us counts as "keep out". The one exception is Crossref's API, which
   is built for programmatic use.
2. **Terms must allow it.** A source's terms must not forbid showing a headline, a short description and a
   link, or automated access. Checked by hand before a source is added (`SOURCES.md`).
3. **No workarounds.** Nothing behind a login, paywall, bot challenge or rate limit is read.
4. **Only what's needed.** Headline, the publisher's own short description, date, link. Research: title,
   authors, date, DOI and the deposited abstract.
5. **Credit and non-commercial use.** Every card names and links its source; the site stays non-commercial.

Requests go one at a time with pauses and identify themselves as `LabourPulse/1.0` with a link to this
repository.

## Credits and licences

UK Parliament data: Open Parliament Licence v3.0. GOV.UK: Open Government Licence v3.0. Federal Register: US
public domain. Indian bills: Parliament of India (<https://sansad.in>). Research metadata: Crossref
(<https://www.crossref.org>). Fonts: Anek Devanagari and Mukta (SIL Open Font License), via Google Fonts.
Code design and reused modules: AI Pulse by shru14.
