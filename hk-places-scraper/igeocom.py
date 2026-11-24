"""Government points of interest in Hong Kong from the Lands Department's iGeoCom.

    python igeocom.py          # -> out/igeocom_places.csv

One download returns the GeoCommunity Database (iGeoCom) as GeoJSON: every point of interest
the Lands Department maps, in 18 classes and 142 types. Every place is kept. `category` holds
the project's category where an iGeoCom type corresponds to one, and is empty otherwise:

  Lifestyle, snack and convenience    CVS convenience stores
  Supermarket                         SMK supermarkets
  Restaurant                          CFS cooked food stalls and centres, FLR floating restaurants

iGeoCom has no type for single restaurants, cafes, bars, gyms, pharmacies or beauty salons.
What it adds is the surroundings: railway stations and their entrances (RSN, MTA, LRA, HSN,
HSA), bus and minibus termini (BUS, MIN), ferry piers (FER, FET), malls (MAL), markets (MKT),
schools (class SCH), hospitals and clinics (HOS, CLI), government offices (GOF, GOD), hotels
and guest houses (HTL, GHS), cinemas (TNC), and sports and leisure venues (class RSF).

The download host serves its certificate without the intermediate that signed it, so the
script first fetches that intermediate from the address the certificate names.

Each run is kept in data/igeocom/<date>.zip as downloaded. `lat` and `lon` are the WGS84 point
of the place; `easting` and `northing` are its Hong Kong 1980 Grid coordinates as given.
`revised` is the day the Lands Department last changed the place, `data_date` the day it wrote
the file. Class, type, subcategory and source names come from its data dictionary, version 5.0.

The data is (c) the Government of the Hong Kong SAR, released on DATA.GOV.HK for free
commercial and non-commercial re-use with the source acknowledged.

Standard library only; Python 3.9 or newer, built with OpenSSL 1.1.1 or newer for TLS 1.3.
"""
import csv
import io
import json
import random
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "igeocom"
OUT = ROOT / "out"
DOWNLOAD = ("https://open.hkmapservice.gov.hk/OpenData/directDownload"
            "?productName=iGeoCom&sheetName=iGeoCom&productFormat=GEOJSON")

# iGeoCom type -> category
CATEGORY = {
    "CVS": "Lifestyle, snack and convenience",
    "SMK": "Supermarket",
    "CFS": "Restaurant", "FLR": "Restaurant",
}
CLASSES = {
    "AMD": "Accommodation", "AQU": "Aquatics", "BGD": "Burial Ground", "BUS": "Bus Stop",
    "CMF": "Commercial Facility", "COM": "Community Facility", "CUF": "Cultural Facility",
    "GOV": "Public Service", "HNC": "Health Care", "MUF": "Municipal Facility",
    "PAK": "Conservation", "REM": "Religious", "RSF": "Leisure Facility", "SCH": "Educational",
    "TRF": "Transportation Furniture", "TRH": "Tourism and Hiking", "TRS": "Transportation",
    "UTI": "Utility / Installation",
}
TYPES = {
    # AMD
    "GHS": "Guest House", "HCV": "Holiday Camp / Village", "HTL": "Hotel", "YHL": "Youth Hostel",
    # AQU
    "BBS": "Bathing Beach", "YAC": "Boating / Yachting / Water Sports Centre",
    # BGD
    "CEM": "Cemetery", "COL": "Columbarium", "CRE": "Crematorium",
    "FUN": "Funeral Parlour / Mortuary",
    # BUS
    "BUS": "Bus Terminus", "MIN": "Green Minibus Terminus",
    # CMF
    "ACS": "Association / Club / Society", "CTR": "China Travel Service",
    "CVS": "Convenience Store", "FLR": "Floating Restaurant",
    "MAL": "Mall / Shopping Centre / Commercial Complex",
    "ROI": "Department Store / Retail Outlet of Interest", "SMK": "Supermarket",
    # COM
    "CMC": "Community Centre / Community Hall / Youth Centre / Welfare Centre",
    "FSC": "Family Service Centre", "RCM": "Rural Committee", "VOF": "Village Office",
    # CUF
    "CHL": "City Hall / Town Hall / Civic Centre", "DMT": "Declared Monument / Antiquity",
    "EXB": "Exhibition Venue", "HST": "Historical Site/Heritage", "LIB": "Library",
    "PAG": "Pagoda", "PFM": "Performing Arts Venue", "SCU": "Sculpture / Memorial Inscription",
    "SSR": "Self-Study Room", "TNC": "Cinema", "TTH": "Ancestral Hall",
    # GOV
    "ABL": "Ambulance Depot", "CMS": "Diplomatic Organization / Foreign Commission",
    "CSD": "Correctional Institution & etc.", "CST": "Consulate", "DLO": "District Land Office",
    "DOF": "District Office", "FSN": "Fire Station", "GOD": "HQ of Government Department",
    "GOF": "Government Offices", "ICA": "ICAC Regional Office", "ICP": "Immigration Control Point",
    "IDB": "Immigration Department (Births and Deaths Registry)",
    "IDM": "Immigration Department (Marriage Registry)",
    "IDP": "Immigration Department (Personal Documentation)",
    "IDR": "Immigration Department (Registration of Persons)",
    "JUD": "Magistracy / District Court",
    "LJB": "Labour Department (Employment Services Division)",
    "LRE": "Labour Department (Labour Relations Division)", "LRY": "Land Registry",
    "MAP": "Map Sales Outlet", "ORG": "Public Service Organization", "POB": "Posting Box",
    "POF": "Post Office", "PPT": "Police Post", "PSI": "Prison", "PSN": "Police Station",
    "RPT": "Police Reporting Centre", "TAN": "Hong Kong Tourism Board",
    "TDT": "Transport Department (Licensing Division)",
    # HNC
    "BDC": "Blood Donor Centre", "CLI": "Clinic / Health Centre / Dispensary",
    "ELD": "Home for the Elderly", "HOS": "Hospital", "REH": "Rehabilitation Centre",
    # MUF
    "BAZ": "Bazaar", "CFS": "Cooked Food Stall", "CSC": "Municipal Complex", "MKT": "Market",
    "RCP": "Refuse Collection Point", "TOI": "Toilet", "WMT": "Wholesale Market",
    # PAK
    "CPB": "Country Parks (Designation) (Consolidation) Order (Cap. 208B)",
    "CRA": "Conservational restricted area",
    "CSA": "Designation of Special Areas within Country Parks (Consolidation) Order (Cap. 208C)",
    "MPB": "Marine Parks (Designation) Order (Cap. 476B)",
    "MRA": "Marine Reserve (Designation) Order (Cap. 476C)", "NRA": "Nature Reserve",
    "SPA": "Special Areas (Designation) (Consolidation) Order (Cap. 208D)",
    # REM
    "CHU": "Church", "MON": "Monastery / Nunnery", "MOS": "Mosque",
    "RPS": "Other Religious Meeting Place", "SMY": "Seminary", "SYN": "Synagogue", "TMP": "Temple",
    # RSF
    "AMK": "Theme Park", "BAS": "Basketball Court", "BWG": "Bowling Green",
    "BWR": "Indoor Bowling Rink", "CCS": "Recreational Club Site", "GCO": "Golf Course",
    "IGH": "Indoor Sports Venue", "ISR": "Ice Skating / Roller Rink / Skateboard",
    "OSA": "Other Sports and Sports Association", "PAR": "Park", "PAV": "Pavilion",
    "PLG": "Playground", "RCO": "Racecourse", "RGD": "Minor Open Space", "SCO": "Squash Court",
    "SGD": "Sports Ground / Football Field", "SPL": "Swimming Pool", "STD": "Stadium",
    "TCT": "Tennis Court", "VPT": "Viewing Point", "ZOO": "Zoo",
    # SCH
    "CCC": "Child Care Centre", "KDG": "Kindergarten", "MIS": "Riding School / Road Safety Centre",
    "PRS": "Primary School", "SCM": "Educational Branch / Sub-campus",
    "SEC": "Special Education School", "SES": "Secondary School", "TEI": "Post-Secondary",
    "VTI": "Vocational Training Institute / Career Skill Development",
    # TRF
    "AER": "Aeronautical Beacon", "NAU": "Nautical Navigation",
    "REA": "Vehicular Restricted Access", "REN": "Route Exit", "VEB": "Vehicular Barred Access",
    # TRH
    "CAM": "Country / Marine Park Management Centre", "FLO": "Fire Lookout", "SIG": "Scenic Spot",
    # TRS
    "AIR": "Airport", "CBC": "Cable Car", "CBV": "Cross Boundary Vehicle Stop", "CPO": "Car Park",
    "DTC": "Driving Test Centre", "FER": "Ferry Pier", "FET": "Ferry Terminal",
    "HLP": "Helicopter Landing Pad", "HSA": "High Speed Rail Station Entrance",
    "HSN": "High Speed Rail Station", "LRA": "Light Rail Station",
    "MTA": "Railway Station Entrance", "PIE": "Wharf", "PTA": "Peak Tram Access",
    "RSN": "Railway Station", "TOA": "Toll Gate",
    # UTI
    "EES": "Electricity Substation", "LPG": "Liquefied Petroleum Gas Filling Station",
    "PFS": "Petrol Station",
    "SGN": ("Radio Transmitting Station / Television Transmitting Station / Radar Station / "
            "Signal Station / Wireless Station / Microwave Station"),
    "SST": "Earth Satellite Station",
}
SUBCATS = {
    "BIRTHS": "Births Registry", "BTHDTH": "Births and Deaths Registry",
    "CPINDR": "Car Park - Indoor", "CPMULT": "Car Park - Multi-Storey", "CPOPEN": "Car Park - Open",
    "CTMPCM": "Chinese Temple Committee", "DEATHS": "Deaths Registry",
    "DELDCC": "District Elderly Community Centre",
    "DISTHQ": "Hong Kong Police Force District Headquarters",
    "DIVSTN": "Hong Kong Police Force Divisional Station", "DTLSCH": "School Dental Clinic",
    "ELDHTH": "Elderly Health Centre", "ESUPVS": "Supervised", "EVNSCH": "Evening School",
    "EXBCTR": "Exhibition Centre", "EXBSPC": "Exhibition Venue of Specific Thematic Interest",
    "GENOPC": "General Outpatient Clinical", "GOPCLI": "General Outpatient Clinical",
    "HGP24R": "24-Hour Cross Boundary Coach to Huanggang Port",
    "HSRLIF": "High Speed Rail Barrier-free Access with Lift",
    "HSRRAM": "High Speed Rail Barrier-free Access with Ramp",
    "HSRSLV": "High Speed Rail Barrier-free Access at Same Level",
    "HTLASN": "Member of Hong Kong Hotels Association",
    "IFSGOV": "Integrated Family Service Centre (Social Welfare Department)",
    "IFSSVN": "Integrated Family Service Centre (Subvented Non-Governmental Organization)",
    "INSIDE": "Subordinate Facility inside Pleasure Ground",
    "ISCSVN": "Integrated Services Centre (Subvented Non-Governmental Organization)",
    "KDGCCC": "Kindergarten-cum-Child Care Centre", "MOBILE": "Mobile",
    "MTHDNC": "Methadone Centre", "MTNCHD": "Maternal & Child Health Centre",
    "MTRLIF": "MTR Barrier-free Access with Lift", "MTRRAM": "MTR Barrier-free Access with Ramp",
    "MTRSLV": "MTR Barrier-free Access at Same Level",
    "MTRSTL": "MTR Barrier-free Access with Stair Lift",
    "MTRWCA": "MTR Barrier-free Access with Wheelchair Aid", "NON24R": "Non-24-Hour Open",
    "OPBASE": "Hong Kong Police Force Operational Base",
    "PENQSC": "Public Enquiry Services Counter",
    "PEXMPT": "Private - Exempted under Section 8 of Medical Clinics Ordinance (Chapter 343)",
    "PFMIDR": "Venue for Performing Art (Indoor)",
    "PFMODR": "Venue for Performing Activities (Outdoor)", "RDRSTN": "Radar Station",
    "RESHSE": "Resort House (Holiday Flat)",
    "RGDPSC": "Registered Under the Post-Secondary Colleges Ordinance",
    "RGNHQS": "Hong Kong Police Force Regional Headquarters",
    "RPTC_T": "Hong Kong Police Force Traffic Reporting Centre", "RRLCMT": "Rural Committee",
    "RSTOTL": "Restricted Area (Omni-temporal)", "RSTSSL": "Restricted Area (Seasonal)",
    "SKTBRD": "Skateboard", "SKTICE": "Ice Skating", "SKTRRK": "Roller Rink",
    "SPRSTR": "Superstore",
    "UGCFIT": ("University Grants Committee Funded Institutions or University with Self "
               "University Ordinance"),
    "WESTRN": "Western", "WMNHTH": "Woman Health Centre",
}
SOURCES = {
    1: "Facility records from map.gov.hk", 3: "Gazetted / Deposited Information",
    5: "iB1000 Topographic Map from Lands Department",
    9: "Cadastral Information from Lands Department",
    22: "Information from A-K Government Departments",
    24: "Information from L-Z Government Departments",
    26: "Information from government related organisations",
    27: "Information from private sector",
}
COLS = ["igeocom_id", "category", "class", "class_name", "type", "type_name", "subcat",
        "subcat_name", "name_en", "name_zh", "floor_en", "floor_zh", "site_en", "site_zh",
        "area_en", "area_zh", "district_en", "district_zh", "region_en", "region_zh",
        "address_en", "address_zh", "lat", "lon", "easting", "northing", "phone", "website",
        "source", "revised", "data_date", "collected"]


def fetch(url, context=None):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hk-places-scraper/0.1"})
            with urllib.request.urlopen(req, timeout=240, context=context) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504):
                raise SystemExit(f"HTTP {e.code} from {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(20 * 2 ** attempt + random.random())
    raise SystemExit(f"no answer after 5 tries: {url}")


def trust():
    """TLS context that also holds the intermediate certificate the download host leaves out."""
    host = urllib.parse.urlsplit(DOWNLOAD).hostname
    certificate = ssl.PEM_cert_to_DER_cert(ssl.get_server_certificate((host, 443)))
    issuer = re.search(rb"http://[!-~]+?\.crt", certificate).group().decode()
    context = ssl.create_default_context()
    # the fetched certificate counts only if it leads to a root this machine already trusts
    context.verify_flags &= ~getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
    time.sleep(1)
    context.load_verify_locations(cadata=fetch(issuer))
    return context


def text(v):
    return " ".join((v or "").split())


def row(feature, data_date, today):
    p = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]
    day, month, year = p["REV_DATE"].split("/")
    subcat = p["SUBCAT"] or ""
    return {
        "igeocom_id": p["GEONAMEID"], "category": CATEGORY.get(p["TYPE"], ""),
        "class": p["CLASS"], "class_name": CLASSES.get(p["CLASS"], ""),
        "type": p["TYPE"], "type_name": TYPES.get(p["TYPE"], ""),
        "subcat": subcat, "subcat_name": SUBCATS.get(subcat, ""),
        "name_en": text(p["ENGLISHNAME"]), "name_zh": text(p["CHINESENAME"]),
        "floor_en": text(p["E_FLOOR"]), "floor_zh": text(p["C_FLOOR"]),
        "site_en": text(p["E_SITENAME"]), "site_zh": text(p["C_SITENAME"]),
        "area_en": text(p["E_AREA"]), "area_zh": text(p["C_AREA"]),
        "district_en": text(p["E_DISTRICT"]), "district_zh": text(p["C_DISTRICT"]),
        "region_en": text(p["E_REGION"]), "region_zh": text(p["C_REGION"]),
        "address_en": text(p["E_ADDRESS"]), "address_zh": text(p["C_ADDRESS"]),
        "lat": lat, "lon": lon, "easting": p["EASTING"], "northing": p["NORTHING"],
        "phone": text(p["TEL_NO"]), "website": text(p["WEB_SITE"]),
        "source": SOURCES.get(p["SOURCE"], ""),
        "revised": f"{year}-{int(month):02}-{int(day):02}",
        "data_date": data_date, "collected": today,
    }


def main():
    today = date.today().isoformat()
    context = trust()
    time.sleep(1)
    body = fetch(DOWNLOAD, context)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{today.replace('-', '')}.zip").write_bytes(body)

    with zipfile.ZipFile(io.BytesIO(body)) as z:
        member = z.infolist()[0]
        features = json.loads(z.read(member))["features"]
    data_date = date(*member.date_time[:3]).isoformat()

    rows = [row(f, data_date, today) for f in features]
    rows.sort(key=lambda r: (r["class"], r["type"], r["name_en"], r["igeocom_id"]))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "igeocom_places.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    for category, n in Counter(r["category"] or "(no category)" for r in rows).most_common():
        print(f"{n:6}  {category}")
    print(f"{len(rows)} places, data of {data_date} -> {OUT / 'igeocom_places.csv'}")


if __name__ == "__main__":
    sys.exit(main())
