from django.test import SimpleTestCase

from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases
from bcap.util.aliases.site_visit import SiteVisitAliases
from bcap.util.bcap_aliases import AbstractAliases


class AliasesTests(SimpleTestCase):
    def test_archaeological_site_alias_value_matches_attribute_name(self):
        self.assertEqual(ArchaeologicalSiteAliases.ACCURACY_REMARKS, "accuracy_remarks")

    def test_site_visit_alias_value_matches_attribute_name(self):
        self.assertEqual(SiteVisitAliases.ACCURACY_REMARKS, "accuracy_remarks")

    def test_source_notes_removed_from_archaeological_site(self):
        self.assertFalse(hasattr(ArchaeologicalSiteAliases, "SOURCE_NOTES"))

    def test_source_notes_removed_from_site_visit(self):
        self.assertFalse(hasattr(SiteVisitAliases, "SOURCE_NOTES"))

    def test_get_dict_excludes_dunders(self):
        result = AbstractAliases.get_dict(ArchaeologicalSiteAliases)
        for key in result:
            self.assertFalse(key.startswith("_"))
