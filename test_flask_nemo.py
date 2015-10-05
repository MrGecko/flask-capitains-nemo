import unittest
from flask.ext.nemo import Nemo
from mock import patch, call
import MyCapytain
from lxml import etree
from flask import Markup


class RequestPatch(object):
    """ Request patch object to deal with patching reply in flask.ext.nemo
    """
    def __init__(self, f):
        self.__text = f.read()

    @property
    def text(self):
        return self.__text


class RequestPatchChained(object):
    """ Request patch object to deal with patching reply in flask.ext.nemo
    """
    def __init__(self, requests):
        self.resource = [other.text for other in requests]

    @property
    def text(self):
        return self.resource.pop(0)


class NemoResource(unittest.TestCase):
    """ Test Suite for Nemo
    """
    endpoint = "http://website.com/cts/api"
    body_xsl = "testing_data/xsl_test.xml"

    def setUp(self):
        with open("testing_data/getcapabilities.xml", "r") as f:
            self.getCapabilities = RequestPatch(f)

        with open("testing_data/getvalidreff.xml", "r") as f:
            self.getValidReff_single = RequestPatch(f)
            self.getValidReff = RequestPatchChained([self.getCapabilities, self.getValidReff_single])

        with open("testing_data/getpassage.xml", "r") as f:
            self.getPassage = RequestPatch(f)
            self.getPassage_Capabilities = RequestPatchChained([self.getCapabilities, self.getPassage])

        with open("testing_data/getprevnext.xml", "r") as f:
            self.getPrevNext = RequestPatch(f)
            self.getPassage_Route = RequestPatchChained([self.getCapabilities, self.getPassage, self.getPrevNext])

        self.nemo = Nemo(
            api_url=NemoTestControllers.endpoint
        )


class NemoTestControllers(NemoResource):

    def test_flask_nemo(self):
        """ Testing Flask Nemo is set up"""
        a = Nemo()
        self.assertIsInstance(a, Nemo)
        a = Nemo()

    def test_without_inventory_request(self):
        """ Check that endpoint are derived from nemo.api_endpoint setting
        """
        #  Test without inventory
        with patch('requests.get', return_value=self.getCapabilities) as patched_get:
            self.nemo.get_inventory()
            patched_get.assert_called_once_with(
                NemoTestControllers.endpoint, params={
                    "request": "GetCapabilities"
                }
            )

    def test_with_inventory_request(self):
        """ Check that endpoint are derived from nemo.api_endpoint setting
        """
        with patch('requests.get', return_value=self.getCapabilities) as patched_get:
            #  Test with inventory
            self.nemo.api_inventory = "annotsrc"
            self.nemo.get_inventory()
            patched_get.assert_called_once_with(
                NemoTestControllers.endpoint, params={
                    "request": "GetCapabilities",
                    "inv": "annotsrc"
                }
            )
            self.nemo.api_inventory = None

    def test_inventory_parsing(self):
        """ Check that endpoint request leads to the creation of a TextInventory object
        """
        with patch('requests.get', return_value=self.getCapabilities) as patched_get:
            inventory = self.nemo.get_inventory()
            patched_get.assert_called_once_with(
                NemoTestControllers.endpoint, params={
                    "request": "GetCapabilities"
                }
            )
            self.assertIs(len(inventory.textgroups), 4)

    def test_get_collection(self):
        with patch('requests.get', return_value=self.getCapabilities) as patched_get:
            collections = self.nemo.get_collections()
            patched_get.assert_called_once_with(
                NemoTestControllers.endpoint, params={
                    "request": "GetCapabilities"
                }
            )
            self.assertEqual(collections, {"latinLit", "greekLit"})


    def test_get_authors(self):
        """ Check that authors textgroups are returned with informations
        """
        with patch('requests.get', return_value=self.getCapabilities):
            tgs = self.nemo.get_textgroups()
            self.assertIs(len(tgs), 4)
            self.assertEqual("urn:cts:greekLit:tlg0003" in [str(tg.urn) for tg in tgs], True)

    def test_get_authors_with_collection(self):
        """ Check that authors textgroups are returned when filtered by collection
        """
        with patch('requests.get', return_value=self.getCapabilities):
            tgs_2 = self.nemo.get_textgroups("greekLIT")  # With nice filtering
            self.assertIs(len(tgs_2), 1)
            self.assertEqual("urn:cts:greekLit:tlg0003" in [str(tg.urn) for tg in tgs_2], True)

    def test_get_works_with_collection(self):
        """ Check that works are returned when filtered by collection and textgroup
        """
        with patch('requests.get', return_value=self.getCapabilities):
            works = self.nemo.get_works("greekLIT", "TLG0003")  # With nice filtering
            self.assertIs(len(works), 1)
            self.assertEqual("urn:cts:greekLit:tlg0003.tlg001" in [str(work.urn) for work in works], True)

            #  Check when it fails
            works = self.nemo.get_works("greekLIT", "TLGabc003")  # With nice filtering
            self.assertIs(len(works), 0)

    def test_get_works_without_filters(self):
        """ Check that all works are returned when not filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            #  Check when it fails
            works = self.nemo.get_works()  # With nice filtering
            self.assertIs(len(works), 13)

    def test_get_works_with_one_filter(self):
        """ Check that error are raises
        """
        with self.assertRaises(ValueError):
            works = self.nemo.get_works("a", None)  # With nice filtering

        with self.assertRaises(ValueError):
            works = self.nemo.get_works(None, "a")

    def test_get_texts_with_all_filtered(self):
        """ Check that texts are filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            texts = self.nemo.get_texts("greekLIT", "TLG0003", "tlg001")  # With nice filtering
            self.assertIs(len(texts), 1)
            self.assertEqual("urn:cts:greekLit:tlg0003.tlg001.perseus-grc2" in [str(text.urn) for text in texts], True)

            texts = self.nemo.get_texts("greekLIT", "TLG0003", "tlg002")  # With nice filtering
            self.assertIs(len(texts), 0)

    def test_get_texts_with_none_filtered(self):
        """ Check that texts are filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            texts = self.nemo.get_texts()  # With nice filtering
            self.assertIs(len(texts), 14)
            self.assertEqual("urn:cts:greekLit:tlg0003.tlg001.perseus-grc2" in [str(text.urn) for text in texts], True)
            self.assertEqual("urn:cts:latinLit:phi1294.phi002.perseus-lat2" in [str(text.urn) for text in texts], True)
            self.assertEqual("urn:cts:latinLit:phi1294.phi002.perseus-lat3" in [str(text.urn) for text in texts], False)

    def test_get_texts_with_work_not_filtered(self):
        """ Check that all textgroups texts are returned
        """
        with patch('requests.get', return_value=self.getCapabilities):
            texts = self.nemo.get_texts("latinLit", "phi0959")  # With nice filtering
            self.assertIs(len(texts), 10)
            self.assertEqual("urn:cts:greekLit:tlg0003.tlg001.perseus-grc2" in [str(text.urn) for text in texts], False)
            self.assertEqual("urn:cts:latinLit:phi0959.tlg001.perseus-lat2" in [str(text.urn) for text in texts], False)

    def test_get_texts_raise(self):
        with self.assertRaises(
                ValueError):
            self.nemo.get_texts("latinLit")

    def test_get_single_text(self):
        """ Check that texts are filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            texts = self.nemo.get_text("greekLIT", "TLG0003", "tlg001", "perseus-grc2")  # With nice filtering
            self.assertIsInstance(texts, MyCapytain.resources.inventory.Text)
            self.assertEqual(str(texts.urn), "urn:cts:greekLit:tlg0003.tlg001.perseus-grc2")

    def test_get_single_text_empty_because_no_work(self):
        """ Check that texts are filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            with patch('flask_nemo.abort') as abort:
                texts = self.nemo.get_text("latinLit", "phi0959", "phi011", "perseus-lat2")   # With nice filtering
                abort.assert_called_once_with(404)

    def test_get_single_text_abort(self):
        """ Check that texts are filtered
        """
        with patch('requests.get', return_value=self.getCapabilities):
            with patch('flask_nemo.abort') as abort:
                texts = self.nemo.get_text("greekLIT", "TLG0003", "tlg001", "perseus-grc132")  # With nice filtering
                abort.assert_called_once_with(404)

    def test_get_validreffs_without_specific_callback(self):
        """ Try to get valid reffs
        """
        self.nemo = Nemo(api_url=NemoTestControllers.endpoint, inventory="annotsrc")
        with patch('requests.get', return_value=self.getValidReff) as patched:
            text, callback = self.nemo.get_reffs("latinLit", "phi1294", "phi002", "perseus-lat2")
            self.assertIsInstance(text, MyCapytain.resources.inventory.Text)

            reffs = callback(level=3)
            self.assertIsInstance(reffs, list)
            self.assertEqual(reffs[0], "urn:cts:latinLit:phi1294.phi002.perseus-lat2:1.pr.1")
            self.assertEqual(patched.mock_calls, [
                call(
                    NemoTestControllers.endpoint,
                    params={
                        "inv": "annotsrc",
                        "request": "GetCapabilities"
                    }
                ),
                call(
                    NemoTestControllers.endpoint,
                    params={
                        "inv": "annotsrc",
                        "request": "GetValidReff",
                        "level": "3",
                        "urn": "urn:cts:latinLit:phi1294.phi002.perseus-lat2"
                    }
                )
                ]
            )

    def test_get_passage(self):
        self.nemo = Nemo(api_url=NemoTestControllers.endpoint, inventory="annotsrc")
        with patch('requests.get', return_value=self.getPassage) as patched:
            passage = self.nemo.get_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr")
            self.assertIsInstance(passage, MyCapytain.resources.texts.api.Passage)
            self.assertEqual(len(passage.xml.xpath("//tei:l[@n]", namespaces={"tei":"http://www.tei-c.org/ns/1.0"})), 6)


class NemoTestRoutes(NemoResource):
    """ Test Suite for Nemo
    """
    def test_route_index(self):
        """ Check that index return the template
        """
        self.assertEqual(self.nemo.r_index(), {"template": self.nemo.templates["index"]})

    def test_route_collection(self):
        """ Test return values of route collection (list of textgroups
        """

        with patch('requests.get', return_value=self.getCapabilities) as patched:
            view = self.nemo.r_collection("latinLit")
            self.assertEqual(view["template"], self.nemo.templates["textgroups"])
            self.assertEqual(len(view["textgroups"]), 3)
            self.assertIn("urn:cts:latinLit:phi1294", [str(textgroup.urn) for textgroup in view["textgroups"]])
            self.assertIsInstance(view["textgroups"][0], MyCapytain.resources.inventory.TextGroup)

    def test_route_texts(self):
        """ Test return values of route texts (list of texts for a textgroup
        """

        with patch('requests.get', return_value=self.getCapabilities) as patched:
            view = self.nemo.r_texts("latinLit", "phi1294")
            self.assertEqual(view["template"], self.nemo.templates["texts"])
            self.assertEqual(len(view["texts"]), 2)
            self.assertEqual(
                sorted([str(view["texts"][0].urn), str(view["texts"][1].urn)]),
                sorted(["urn:cts:latinLit:phi1294.phi002.perseus-lat2", "urn:cts:latinLit:phi1294.phi002.perseus-eng2"])
            )
            self.assertIsInstance(view["texts"][0], MyCapytain.resources.inventory.Text)

    def test_route_version_chunker_replacement(self):
        """ Try to get valid reffs
        """

        urn = "urn:cts:latinLit:phi1294.phi002.perseus-lat2"
        def chunker(text, level):
            self.assertIsInstance(text, MyCapytain.resources.inventory.Text)
            self.assertEqual(str(text.urn), "urn:cts:latinLit:phi1294.phi002.perseus-lat2")
            return True

        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc",
            chunker={"default": chunker}
        )

        with patch('requests.get', return_value=self.getValidReff) as patched:
            view = nemo.r_version("latinLit", "phi1294", "phi002", "perseus-lat2")
            self.assertIsInstance(view["version"], MyCapytain.resources.inventory.Text)
            patched.assert_called_once_with(
                NemoTestControllers.endpoint,
                params={
                    "inv": "annotsrc",
                    "request": "GetCapabilities"
                }
            )
            self.assertEqual(view["reffs"], True)

    def test_route_version_default_chunker(self):
        """ Try to get valid reffs
        """
        urn = "urn:cts:latinLit:phi1294.phi002.perseus-lat2"

        with patch('requests.get', return_value=self.getValidReff) as patched:
            view = self.nemo.r_version("latinLit", "phi1294", "phi002", "perseus-lat2")
            self.assertIsInstance(view["version"], MyCapytain.resources.inventory.Text)
            self.assertEqual(view["reffs"][0], ("1.pr.1", "1.pr.1"))

    def test_route_text_without_transform(self):
        """ Try to get valid reffs
        """
        urn = "urn:cts:latinLit:phi1294.phi002.perseus-lat2"

        with patch('requests.get', return_value=self.getValidReff) as patched:
            view = self.nemo.r_version("latinLit", "phi1294", "phi002", "perseus-lat2")
            self.assertIsInstance(view["version"], MyCapytain.resources.inventory.Text)
            self.assertEqual(view["reffs"][0], ("1.pr.1", "1.pr.1"))

    def test_route_passage_without_xslt(self):
        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc"
        )
        with patch('requests.get', return_value=self.getPassage_Route) as patched:
            view = self.nemo.r_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr.1")
            self.assertEqual(view["template"], nemo.templates["text"])
            self.assertIsInstance(view["version"], MyCapytain.resources.inventory.Text)
            self.assertEqual(str(view["version"].urn), "urn:cts:latinLit:phi1294.phi002.perseus-lat2")
            self.assertEqual(view["prev"], "1.1.1")
            self.assertEqual(view["next"], "1.1.3")
            self.assertIsInstance(view["text_passage"], Markup)

            # Reparsing xml
            xml = etree.fromstring(str(view["text_passage"]))
            self.assertEqual(
                len(xml.xpath("//tei:body", namespaces={"tei":"http://www.tei-c.org/ns/1.0"})),
                1
            )
            self.assertEqual(
                len(xml.xpath("//tei:l", namespaces={"tei":"http://www.tei-c.org/ns/1.0"})),
                6
            )

    def test_route_passage_with_transform(self):
        """ Try with a non xslt just to be sure
        """
        urn = "urn:cts:latinLit:phi1294.phi002.perseus-lat2"
        def transformer(version, text):
            self.assertEqual(str(version.urn), "urn:cts:latinLit:phi1294.phi002.perseus-lat2")
            self.assertIsInstance(text, etree._Element)
            return "<a>Hello</a>"
        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc",
            transform={"default": transformer}
        )
        with patch('requests.get', return_value=self.getPassage_Route) as patched:
            view = nemo.r_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr.1")
            self.assertEqual(view["text_passage"], Markup("<a>Hello</a>"))

    def test_route_passage_with_xslt(self):
        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc",
            transform={"default": NemoTestControllers.body_xsl}
        )
        with patch('requests.get', return_value=self.getPassage_Route) as patched:
            view = nemo.r_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr.1")
            self.assertEqual(view["template"], nemo.templates["text"])
            self.assertIsInstance(view["version"], MyCapytain.resources.inventory.Text)
            self.assertEqual(str(view["version"].urn), "urn:cts:latinLit:phi1294.phi002.perseus-lat2")
            self.assertEqual(view["prev"], "1.1.1")
            self.assertEqual(view["next"], "1.1.3")
            self.assertIsInstance(view["text_passage"], Markup)

            # Reparsing xml
            xml = etree.fromstring(str(view["text_passage"]))
            self.assertEqual(
                len(xml.xpath("//tei:notbody", namespaces={"tei":"http://www.tei-c.org/ns/1.0"})),
                1
            )

    def test_route_passage_with_urn_xslt(self):
        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc",
            transform={"urn:cts:latinLit:phi1294.phi002.perseus-lat2": NemoTestControllers.body_xsl}
        )
        with patch('requests.get', return_value=self.getPassage_Route) as patched:
            view = nemo.r_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr.1")
            # Reparsing xml
            xml = etree.fromstring(str(view["text_passage"]))
            self.assertEqual(
                len(xml.xpath("//tei:notbody", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})),
                1
            )

    def test_route_passage_without_urn_xslt(self):
        nemo = Nemo(
            api_url=NemoTestControllers.endpoint,
            inventory="annotsrc",
            transform={"urn:cts:latinLit:phi1294.phi002.perseus-lat3": NemoTestControllers.body_xsl}
        )
        with patch('requests.get', return_value=self.getPassage_Route) as patched:
            view = nemo.r_passage("latinLit", "phi1294", "phi002", "perseus-lat2", "1.pr.1")
            # Reparsing xml
            xml = etree.fromstring(str(view["text_passage"]))
            self.assertEqual(
                len(xml.xpath("//tei:body", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})),
                1
            )

    def test_route_assets(self):
        with patch('flask_nemo.abort') as abort:
            pass