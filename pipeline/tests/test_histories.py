"""Checks for the link rules and the store-change count.

    cd pipeline && python -m unittest discover tests

The two cases under tests/cases/ are the licence records of shopfronts whose histories were
checked by hand against the English and Chinese files.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import histories as H  # noqa: E402

CASES = Path(__file__).parent / "cases"


def lic(licno, first, last, *signs):
    return {"licno": licno, "prefix": licno[:2], "first_snap": first, "last_snap": last, "sign_set": set(signs)}


def hist(*lics):
    return {"licences": list(lics), "sign_set": set().union(*(l["sign_set"] for l in lics))}


def run_case(name):
    case = json.loads((CASES / f"{name}.json").read_text())
    lics = [{**l, "sign_set": set(l["sign_set"])} for l in case["licences"]]
    hs, trans = H.histories_for(lics, case["first_file"], case["latest_file"])
    return case["expect"], lics, hs, H.succession_changes(hs, trans, case["latest_file"])


class Signs(unittest.TestCase):
    def test_placeholder(self):
        for s in ("No Record", "(NO RECORD FOUND)", "沒有記錄", "---", "", None):
            self.assertTrue(H.is_placeholder(s), s)
        self.assertFalse(H.is_placeholder("YEUNG SING ICE ROOM"))

    def test_generic_words_do_not_decide_a_match(self):
        self.assertTrue(H.same_sign({"GOOD TASTE RESTAURANT"}, {"Good Taste Cafe Ltd."}))
        self.assertFalse(H.same_sign({"GOOD TASTE RESTAURANT"}, {"LUCKY RESTAURANT"}))

    def test_either_language_can_match(self):
        self.assertTrue(H.same_sign({"ABC NOODLE", "漁民麵館"}, {"FISHERMAN", "漁民麵館"}))

    def test_placeholder_never_matches(self):
        self.assertFalse(H.same_sign({"No Record"}, {"No Record"}))


class LinkRules(unittest.TestCase):
    def test_provisional_then_full_same_sign(self):
        h = hist(lic("3861800001", "20180101", "20180601", "漁民麵館"))
        self.assertEqual(H.link(h, lic("2261800002", "20180701", "20200101", "漁民麵館")),
                         ("prov_then_full_same_sign", "inferred", True))

    def test_provisional_then_full_placeholder_sign(self):
        h = hist(lic("3861800001", "20180101", "20180601", "No Record"))
        self.assertEqual(H.link(h, lic("2261800002", "20180701", "20200101", "漁民麵館")),
                         ("prov_then_full_no_sign", "unresolved", True))

    def test_provisional_then_full_signs_differ(self):
        h = hist(lic("3861800001", "20180101", "20180601", "漁民麵館"))
        self.assertEqual(H.link(h, lic("2261800002", "20180701", "20200101", "福岡漢堡扒")),
                         ("prov_then_full_sign_differs", "unresolved", False))

    def test_provisional_then_full_after_nine_months_is_not_linked(self):
        h = hist(lic("3861800001", "20180101", "20180601", "No Record"))
        self.assertIsNone(H.link(h, lic("2261800002", "20190101", "20200101", "漁民麵館")))

    def test_same_sign_new_number_within_a_year(self):
        h = hist(lic("2261800001", "20160101", "20180601", "漁民麵館"))
        self.assertEqual(H.link(h, lic("2261800002", "20190301", "20200101", "漁民麵館")),
                         ("same_sign_new_number", "inferred", True))

    def test_same_sign_after_a_year_stays_separate(self):
        h = hist(lic("2261800001", "20160101", "20180601", "漁民麵館"))
        self.assertIsNone(H.link(h, lic("2261800002", "20190801", "20200101", "漁民麵館")))

    def test_different_sign_stays_separate(self):
        h = hist(lic("2261800001", "20160101", "20180601", "漁民麵館"))
        self.assertIsNone(H.link(h, lic("2261800002", "20180701", "20200101", "福岡漢堡扒")))


class HandCheckedShopfronts(unittest.TestCase):
    def check(self, name):
        expect, lics, hs, changes = run_case(name)
        self.assertEqual(len(lics), expect["licence_numbers"])
        self.assertEqual(len(hs), expect["sign_histories"])
        self.assertEqual(len(changes), expect["store_changes"])
        self.assertEqual([c["year"] for c in changes], expect["change_years"])
        self.assertEqual([[l["from"], l["to"], l["rule"]] for h in hs for l in h["links"]], expect["links"])
        return hs, changes

    def test_100_portland_street(self):
        # 7 licence numbers, 4 sign histories, 3 store changes
        hs, changes = self.check("portland_100_gf")
        self.assertEqual((len(hs), len(changes)), (4, 3))

    def test_11a_hau_fook_street(self):
        # 6 licence numbers, 4 store changes
        hs, changes = self.check("hau_fook_11a_gf")
        self.assertEqual(len(changes), 4)
        self.assertTrue(hs[0]["listed_before_2016"])

    def test_a_shop_listed_since_before_2016_is_not_a_change(self):
        for name in ("portland_100_gf", "hau_fook_11a_gf"):
            _, _, hs, changes = run_case(name)
            first = {h["first_seen"] for h in hs if h["listed_before_2016"]}
            self.assertFalse(first & {c["first_seen"] for c in changes})


if __name__ == "__main__":
    unittest.main()
