# -*- coding: utf-8 -*-
"""Debug EPMC/Crossref availability for failing DOIs."""
import requests, json
H = {"User-Agent": "x/1.0"}
DOIS = {
    "J2": "10.1016/j.cognition.2020.104344",
    "J4": "10.1016/j.socscimed.2021.114222",
    "J6": "10.3390/bdcc5040077",
    "J9": "10.3389/fpsyg.2022.917630",
    "J10": "10.1073/pnas.2220898120",
    "J12": "10.1002/pchj.70051",
    "J13": "10.1073/pnas.2504632123",
    "J15": "10.3390/bdcc9070171",
}
for rid, doi in DOIS.items():
    print(f"== {rid} {doi}")
    try:
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": f"DOI:{doi}", "format": "json"}, headers=H, timeout=30)
        d = r.json()
        res = d.get("resultList", {}).get("result", [])
        if not res:
            print("   EPMC: no result (hitCount=%s)" % d.get("hitCount"))
        else:
            e = res[0]
            print("   EPMC: pmcid=%s hasPDF=%s inEPMC=%s" % (e.get("pmcid"), e.get("hasPDF"), e.get("inEPMC")))
            for ft in e.get("fullTextUrlList", {}).get("fullTextUrl", []):
                print("      FT:", ft.get("availability"), ft.get("documentStyle"), ft.get("url")[:100])
    except Exception as ex:
        print("   EPMC ERR", ex.__class__.__name__)
    try:
        r2 = requests.get(f"https://api.crossref.org/works/{doi}", headers=H, timeout=30)
        m = r2.json()["message"]
        links = [(l.get("content-type"), l.get("URL")) for l in m.get("link", [])]
        print("   CR links:", links)
    except Exception as ex:
        print("   CR ERR", ex.__class__.__name__)
