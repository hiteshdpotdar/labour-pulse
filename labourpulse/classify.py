"""Sorting stories into streams and tagging them, with keyword rules in English, Hindi and Marathi.

No AI model is used: every decision is a pattern below, so you can read, test and change it.

Streams (the `category` stored with each story):
    news      Struggles & news: strikes, organising, unions, workplaces, labour markets
    platform  Platform & domestic work: gig and app-based work, domestic and care work
    policy    Policy & courts: governments, ministries, courts, tribunals, the ILO
    law       Labour law tracker: bills and laws, with their stages where an official record exists
    theory    Theory & debate: Marxist and radical political economy writing
    research  Research: new journal articles and working papers

How a story is sorted:
  * Research and theory sources keep their stream (they only carry that kind of writing).
  * Anything else goes to "platform" if it is about platform, gig, domestic or care work;
    otherwise to "law" if it reports a bill or law; otherwise to "policy" if a government or court acts;
    otherwise it stays in its source's stream (usually "news").

Devanagari patterns are matched as plain substrings: Python's word boundaries (\\b) don't work inside
Hindi or Marathi words, and a stem like "कामगार" should match "कामगारांचा" and "कामगारों" alike.
"""

from __future__ import annotations

import re

STREAMS = {
    "news": "Struggles & news",
    "platform": "Platform & domestic work",
    "policy": "Policy & courts",
    "law": "Labour law tracker",
    "theory": "Theory & debate",
    "research": "Research",
}

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


# Marathi "संप" (strike) without "संपला" (it ended), "संपूर्ण" (whole), "संपर्क" (contact), "संपादक" (editor)...
STRIKE_MR = "संप(?=$|[\\s,.;:!?)'\"‘’“”-]|ावर|ात|ाचा|ाची|ाचे|ाला|ाच्या|करी)"


def _rules(english: list[str], devanagari: list[str] = ()) -> tuple[re.Pattern, re.Pattern | None]:
    """English patterns (case-insensitive, with word boundaries) and Devanagari ones (plain text or a
    regular expression, matched anywhere in a word)."""
    return re.compile("|".join(english), re.I), re.compile("|".join(devanagari)) if devanagari else None


def _hit(rules: tuple[re.Pattern, re.Pattern | None], text: str) -> bool:
    english, devanagari = rules
    if english.search(text):
        return True
    return devanagari is not None and bool(_DEVANAGARI.search(text)) and bool(devanagari.search(text))


# --- Is this story about work and workers at all? (for general feeds marked "filter": True) ---
LABOUR = _rules(
    [r"\bwork(er|ers|ers')\b", r"\blabou?r\b", r"\blabou?rers?\b", r"\bunions?\b", r"\bunioni[sz]", r"\bstrik(e|es|ers|ing)\b",
     r"\bwalk-?outs?\b", r"\bwages?\b", r"\bpay (rise|cut|gap|deal|dispute|parity)", r"\bminimum wage", r"\bemploy(ee|ees|er|ers|ment)\b",
     r"\bworkplace", r"\bpicket", r"\block-?outs?\b", r"collective bargaining", r"\borgani[sz](e|ed|ing|er|ers)\b",
     r"\binformal (sector|economy|work)", r"\bprecari", r"\blay-?offs?\b", r"\bredundanc", r"\bsweatshop",
     r"\bgarment", r"\bmigrant", r"\bcare work", r"social reproduction", r"\bexploitation\b", r"surplus value",
     r"class struggle", r"\bMarx", r"\bcapitalis[mt]", r"\bgig\b", r"\bplatform (work|economy|labou?r|capitalism)",
     r"\bdomestic work", r"\bhousemaids?\b", r"\bnannies\b", r"\bcaregivers?\b", r"\bcleaners\b", r"\bjanitors\b",
     r"\bnurses\b", r"\bdockers\b", r"\bminers\b", r"\bfarmworkers?\b", r"\bagricultural labou?r", r"\bbonded labou?r",
     r"\bforced labou?r", r"\bchild labou?r", r"\bcontract labou?r", r"\bsanitation workers?", r"\bAnganwadi",
     r"(?-i:\bASHA\b) workers?", r"\bpension", r"\bretrench", r"\bproletar", r"\bworking class"],
    ["मज़दूर", "मजदूर", "मज़दूरी", "मजदूरी", "श्रमिक", "श्रम ", "कामगार", "कर्मचारी", "हड़ताल", "हडताल", STRIKE_MR,
     "यूनियन", "युनियन", "वेतन", "पगार", "न्यूनतम वेतन", "किमान वेतन", "छंटनी", "कामगार कपात", "ठेका", "कंत्राटी",
     "घरेलू कामगार", "घरकामगार", "मोलकरीण", "गिग", "डिलीवरी", "डिलिव्हरी", "आंगनवाड़ी", "अंगणवाडी", "आशा कार्यकर्ता",
     "आशा सेविका", "असंगठित", "असंघटित", "हमाल", "माथाडी", "बंधुआ", "खेतिहर", "शेतमजूर", "भांडवल", "पूंजीवाद", "मार्क्स"],
)

PLATFORM = _rules(
    [r"\bgig\b", r"\bgig[- ]work", r"\bplatform[- ](work|worker|workers|economy|labou?r|companies|firms|capitalism|cooperative)",
     r"\bapp[- ]based\b", r"\bon-demand work", r"\bcrowd ?work", r"\balgorithmic (management|control|wage|pay)",
     r"\bdelivery (riders?|workers?|partners?|drivers?|agents?)", r"\bride[- ]?hail", r"\bcab drivers\b",
     r"(?-i:\bUber\b)", r"(?-i:\bOla\b)", r"\bRapido\b", r"\bSwiggy\b", r"\bZomato\b", r"\bZepto\b", r"\bBlinkit\b", r"\bInstamart\b",
     r"\bUrban Company\b", r"\bUrbanClap\b", r"\bSnabbit\b", r"(?-i:\bPronto\b)", r"\bDunzo\b", r"(?-i:\bPorter\b)(?= (drivers|app|partners))",
     r"\bDeliveroo\b", r"\bDoorDash\b", r"\bInstacart\b", r"\bGrubHub\b", r"\bJust Eat\b", r"\bGlovo\b", r"\bRappi\b",
     r"(?-i:\biFood\b)", r"(?-i:\bGrab\b)(?= (drivers|riders|workers|food))", r"\bGojek\b", r"(?-i:\bBolt\b)(?= (drivers|riders|workers))",
     r"\bLyft\b", r"\bTaskRabbit\b", r"\bHelpling\b", r"\bCare\.com\b", r"\bAmazon Flex\b", r"\bUpwork\b", r"\bFiverr\b",
     r"\bMechanical Turk\b", r"\bdata (labell?ers|annotators|workers)\b", r"\bcontent moderators?\b",
     r"\bdomestic work", r"\bdomestic helpers?\b", r"\bdomestic labou?r", r"\bhousehold (work|workers|help)", r"\bhousemaids?\b",
     r"\bmaids\b", r"\bnann(y|ies)\b", r"\bau pairs?\b", r"\bhome-?based work", r"\bcare work", r"\bcare workers?\b",
     r"\bcarers?\b", r"\bpaid domestic", r"\bC189\b", r"\bConvention 189\b", r"\bkafala\b",
     r"\bPlatform[- ]based Gig Workers"],
    ["गिग", "प्लेटफ़ॉर्म", "प्लेटफॉर्म", "प्लॅटफॉर्म", "डिलीवरी", "डिलिव्हरी", "ऐप आधारित", "ॲप आधारित", "अॅप आधारित", "स्विगी", "झोमॅटो", "ज़ोमैटो",
     "जोमैटो", "ओला कैब", "उबेर", "अर्बन कंपनी", "घरेलू कामगार", "घरेलू काम", "घरेलू मज़दूर", "घरेलू मजदूर", "घरेलू कर्मचारी",
     "घरकामगार", "घरकाम", "मोलकरीण", "मोलकरणी", "केअर वर्क"],
)

LAW = _rules(
    [r"\bbills?\b", r"(?-i:\bAct\b)", r"\blegislat", r"\bordinance\b", r"\blabou?r codes?\b", r"\bCode on (Wages|Social Security)",
     r"\bIndustrial Relations Code", r"\bOccupational Safety, Health", r"\bstatute\b", r"\bdecree\b", r"\bdirective\b",
     r"\bsigned into law", r"\bpasse[sd] (a |the )?(law|bill)", r"\bnew law\b", r"\blaw (on|to|for|that)\b",
     r"\bamend(ment|s|ed|ing)? (to )?(the )?(labou?r|employment|wage|factories|minimum)", r"\bconvention\b(?=.*\b(ILO|ratif))",
     r"\bratif(y|ies|ied|ication)", r"\brules notified\b", r"\bdraft rules\b"],
    ["विधेयक", "कानून", "क़ानून", "कायदा", "कायद्या", "अध्यादेश", "श्रम संहिता", "कामगार संहिता", "लेबर कोड", "अधिनियम",
     "नियमावली", "संशोधन विधेयक", "सुधारणा विधेयक"],
)

POLICY = _rules(
    [r"\bgovernment\b", r"\bgovt\b", r"\bministr(y|ies|er|ers)\b", r"\bcabinet\b", r"\bparliament", r"\bcongress\b",
     r"\bsenate\b", r"\bassembly\b", r"\bcourt\b", r"\btribunal\b", r"\bjudge", r"\bruling\b", r"\bjudg(e)?ment\b",
     r"\bverdict\b", r"\blawsuit\b", r"\bregulat(or|ors|ion|ions)\b", r"\bpolicy\b", r"\bpolicies\b", r"\bconsultation\b",
     r"\binquiry\b", r"\bcommission\b", r"\bwelfare board\b", r"\blabou?r department\b", r"\bDepartment of Labou?r",
     r"\bDOL\b", r"\bNLRB\b", r"\bEEOC\b", r"\bACAS\b", r"\bILO\b", r"\bInternational Labou?r", r"\bbudget\b",
     r"\bscheme\b", r"\bsocial security\b", r"\be-?Shram\b", r"\bnotification\b"],
    ["सरकार", "मंत्रालय", "मंत्री", "अदालत", "न्यायालय", "कोर्ट", "हाईकोर्ट", "हायकोर्ट", "उच्च न्यायालय", "सुप्रीम कोर्ट",
     "सर्वोच्च न्यायालय", "आयोग", "कल्याण बोर्ड", "कल्याणकारी मंडळ", "श्रम विभाग", "कामगार विभाग", "योजना", "बजट",
     "अर्थसंकल्प", "ई-श्रम"],
)


# Political parties' cadres are "workers" too, but not in the sense this site follows.
_PARTY_WORKERS = re.compile(r"\b(BJP|Congress|AAP|TMC|NCP|DMK|AIADMK|BRS|YSRCP|JD\(U\)|JD\(S\)|RJD|SP|BSP|RSS|Sena|MNS|"
                            r"Labou?r Party|Tory|Conservative|Republican|Democratic|party)\s+(workers?|cadres?|activists?)\b", re.I)


def is_labour(title: str, summary: str = "") -> bool:
    """Is the story about work and workers? (Only asked of general feeds; labour feeds pass everything.)"""
    title, summary = _PARTY_WORKERS.sub(" ", title), _PARTY_WORKERS.sub(" ", summary[:600])
    return _hit(LABOUR, title) or _hit(LABOUR, summary)


def categorize(title: str, summary: str = "", default: str = "news") -> list[str]:
    """The streams a story belongs in, its main one first (see the module docstring for the rules).

    A story can sit in more than one stream: platform and domestic work is a lens across all of them (a
    platform law also shows in the law tracker, a paper on gig work also in Research), and a new law
    reported by a policy source is both policy and law. A strike or protest against a law is a struggle
    first; it doesn't enter the law tracker."""
    text = f"{title} {summary[:400]}"
    platform = _hit(PLATFORM, text)
    struggle = _hit(TAGS["Strike"], title) or _hit(TAGS["Protest"], title)
    law = not struggle and _hit(LAW, title) and (_hit(LABOUR, text) or platform or default in ("policy", "law"))
    if default in ("research", "theory"):
        main = default
    elif platform:
        main = "platform"
    elif law or default == "law":
        main = "law"
    elif not struggle and (_hit(POLICY, title) or default == "policy"):
        main = "policy"
    else:
        main = "news" if default in ("policy", "law") else default
    streams = [main]
    if platform and main != "platform":
        streams.append("platform")
    if law and main != "law":
        streams.append("law")
    return streams


# --- Topic tags (shown on each card and searchable) ---
TAGS = {
    "Strike": _rules([r"\bstrik(e|es|ers|ing)\b", r"\bwalk-?outs?\b", r"\bwalk(s|ed|ing)? out\b", r"\bindustrial action", r"\bbandh\b", r"\block-?outs?\b",
                      r"\bsit-?in\b", r"\bgo-?slow\b"], ["हड़ताल", "हडताल", STRIKE_MR, "बंद का आह्वान"]),
    "Protest": _rules([r"\bprotest", r"\brall(y|ies)\b", r"\bmarch(es|ed)?\b(?! \d)", r"\bdharna\b", r"\bgherao\b", r"\bpicket"],
                      ["प्रदर्शन", "धरना", "धरणे", "आंदोलन", "मोर्चा", "घेराव"]),
    "Unions": _rules([r"\bunions?\b", r"\bunioni[sz]", r"\borgani[sz](e|ed|ing|er|ers)\b", r"collective bargaining",
                      r"\bcollective agreements?", r"\brecognition\b"], ["यूनियन", "युनियन", "मज़दूर संगठन", "मजदूर संगठन", "श्रमिक संगठन", "कामगार संघटना", "सामूहिक सौदेबाजी"]),
    "Wages": _rules([r"\bwages?\b", r"\bpay\b", r"\bsalar(y|ies)\b", r"\bminimum wage", r"\bliving wage", r"\bincome"],
                    ["वेतन", "मज़दूरी", "मजदूरी", "पगार", "मानधन"]),
    "Platform work": _rules([r"\bgig\b", r"\bplatform[- ](work|worker|workers|economy|labou?r|capitalism)",
                                               r"\bapp[- ]based\b", r"\bdelivery (riders?|workers?|partners?)", r"\bride[- ]?hail",
                                               r"\balgorithmic (management|control)", r"\bcrowd ?work"],
                                              ["गिग", "प्लेटफ़ॉर्म", "प्लेटफॉर्म", "प्लॅटफॉर्म", "डिलीवरी", "डिलिव्हरी"]),
    "Domestic work": _rules([r"\bdomestic (work|workers?|help|helpers?|labou?r)", r"\bhousemaids?\b", r"\bmaids\b",
                             r"\bnann(y|ies)\b", r"\bhousehold (work|workers)", r"\bC189\b", r"\bpaid domestic"],
                            ["घरेलू कामगार", "घरेलू काम", "घरेलू मज़दूर", "घरेलू मजदूर", "घरकामगार", "घरकाम", "मोलकरीण"]),
    "Care work": _rules([r"\bcare work", r"\bcare workers?\b", r"\bcarers?\b", r"social reproduction", r"\bAnganwadi",
                         r"(?-i:\bASHA\b)", r"\bnurs(e|es|ing)\b", r"\bchildcare"],
                        ["आंगनवाड़ी", "अंगणवाडी", "आशा कार्यकर्ता", "आशा सेविका", "परिचारिका", "नर्स"]),
    "Migrant labour": _rules([r"\bmigrant", r"\bmigration\b", r"\bkafala\b", r"\bguest workers?"],
                             ["प्रवासी मज़दूर", "प्रवासी मजदूर", "स्थलांतरित", "प्रवासी कामगार"]),
    "Informal sector": _rules([r"\binformal (sector|economy|work|workers)", r"\bunorgani[sz]ed", r"\bstreet vendors?",
                               r"\bhome-?based workers?", r"\bwaste pickers?"],
                              ["असंगठित", "असंघटित", "फेरीवाले", "रेहड़ी", "कचरा वेचक"]),
    "Contract labour": _rules([r"\bcontract (labou?r|workers?)", r"\boutsourc", r"\bagency workers?", r"\bfixed-term",
                               r"\bzero[- ]hours"], ["ठेका", "ठेके पर", "कंत्राटी", "आउटसोर्स"]),
    "Garment & factory": _rules([r"\bgarment", r"\btextile", r"\bfactor(y|ies)\b", r"\bmanufactur", r"\bsweatshop",
                                 r"\bsupply chains?\b"], ["कारखाना", "कारखान्या", "फैक्ट्री", "गारमेंट", "वस्त्र"]),
    "Agrarian labour": _rules([r"\bfarm ?workers?", r"\bagricultural (labou?r|workers?)", r"\bagrarian", r"\bpeasants?",
                               r"\bplantation", r"\bMGNREGA\b", r"\bNREGA\b", r"\bsugarcane cutters?"],
                              ["खेतिहर", "शेतमजूर", "मनरेगा", "ऊसतोड", "किसान", "शेतकरी"]),
    "Gender": _rules([r"\bwomen\b", r"\bgender", r"\bfeminis", r"\bmaternity", r"\bsexual harassment", r"\bequal pay"],
                     ["महिला", "स्त्री", "मातृत्व", "लैंगिक"]),
    "Health & safety": _rules([r"\bhealth and safety", r"\boccupational (health|safety)", r"\bdeaths?\b", r"\bkilled\b",
                               r"\baccident", r"\bheat ?(stress|waves?)", r"\bmanual scaveng", r"\binjur(y|ies|ed)"],
                              ["मौत", "मृत्यू", "हादसा", "अपघात", "सुरक्षा", "हाथ से मैला"]),
    "Layoffs": _rules([r"\blay-?offs?\b", r"\blaid off\b", r"\bjob cuts?\b", r"\bredundanc", r"\bretrench", r"\bclosures?\b"],
                      ["छंटनी", "नौकरी से निकाल", "कामगार कपात", "नोकरी गमाव"]),
    "Social security": _rules([r"\bsocial security", r"\bpension", r"\bwelfare board", r"\binsurance", r"\be-?Shram\b",
                               r"\bESIC?\b", r"\bprovident fund"], ["सामाजिक सुरक्षा", "पेंशन", "निवृत्तीवेतन", "कल्याण बोर्ड", "कल्याणकारी मंडळ", "कल्याण योजना", "बीमा", "विमा"]),
    "Automation & AI": _rules([r"\bautomation\b", r"\bartificial intelligence\b", r"\bAI\b", r"\brobots?\b",
                               r"\bsurveillance\b"], ["स्वचालन", "कृत्रिम बुद्धिमत्ता", "एआय", "एआई"]),
    "Marxist theory": _rules([r"\bMarx", r"\bsubsumption", r"surplus value", r"\bvalue theory", r"\bclass struggle",
                              r"\bhistorical materialism", r"\bdialectic", r"\bprimitive accumulation", r"\bimperialism",
                              r"\bsocial reproduction"], ["मार्क्स", "वर्ग संघर्ष", "अतिरिक्त मूल्य", "साम्राज्यवाद"]),
    "Court": _rules([r"\bcourt\b", r"\btribunal\b", r"\bruling\b", r"\bjudg(e)?ment\b", r"\blawsuit\b", r"\bverdict\b"],
                    ["अदालत", "न्यायालय", "कोर्ट", "हाईकोर्ट", "हायकोर्ट", "फैसला", "निकाल"]),
    "ILO": _rules([r"\bILO\b", r"International Labou?r (Organi[sz]ation|Conference|Office)"],
                  ["अंतरराष्ट्रीय श्रम संगठन", "आंतरराष्ट्रीय कामगार संघटना"]),
}


def tags_for(title: str, summary: str = "", limit: int = 5) -> list[str]:
    """Topic tags in the order listed above, at most `limit`."""
    text = f"{title} {summary[:500]}"
    return [name for name, rules in TAGS.items() if _hit(rules, text)][:limit]


def language(text: str, default: str = "en") -> str:
    """The source's language, unless the text is plainly in another script. Hindi and Marathi share
    Devanagari, so a Devanagari story keeps its source's language ("hi" or "mr"); a Devanagari story in an
    English feed is guessed from a few words that are common in one language and rare in the other."""
    if not _DEVANAGARI.search(text):
        return "en" if default in ("hi", "mr") else default
    if default in ("hi", "mr"):
        return default
    marathi = sum(w in text for w in (" आहे", " आणि ", " च्या", " ला ", "ांचा", "ांनी", " नाही"))
    hindi = sum(w in text for w in (" है", " और ", " के ", " की ", " में ", " नहीं", " का "))
    return "mr" if marathi > hindi else "hi"
