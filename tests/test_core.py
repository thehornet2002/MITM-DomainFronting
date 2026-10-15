import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_builder import build_xray_config
from core.asn_extractor import get_all_catalog_asns, sample_ips_from_cidrs
from core.scanner import test_tcp_ping


class TestMITMServerlessCore(unittest.TestCase):
    def test_catalog_loaded(self):
        asns = get_all_catalog_asns()
        self.assertGreater(len(asns), 30, "Catalog should have at least 30 ASNs")
        
        # Verify Cloudflare AS13335 is present
        cf = [a for a in asns if a["asn"] == 13335]
        self.assertEqual(len(cf), 1)
        self.assertGreater(len(cf[0]["cidrs_v4"]), 0)

        # Verify Iranian MCI AS197207 is present
        mci = [a for a in asns if a["asn"] == 197207]
        self.assertEqual(len(mci), 1)
        self.assertGreater(len(mci[0]["cidrs_v4"]), 0)

    def test_sample_ips_from_cidrs(self):
        cidrs = ["104.16.0.0/16", "151.101.0.0/16"]
        sampled = sample_ips_from_cidrs(cidrs, max_ips=10)
        self.assertEqual(len(sampled), 10)
        for ip in sampled:
            self.assertRegex(ip, r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

    def test_config_builder_hybrid(self):
        settings = {
            "mode": "hybrid",
            "local_port": 10808,
            "cdn_ips": {
                "fastly": "151.101.65.140",
                "google": "142.250.180.206"
            },
            "enable_warp": True
        }
        cfg = build_xray_config(settings)
        self.assertIn("inbounds", cfg)
        self.assertIn("outbounds", cfg)
        self.assertIn("routing", cfg)

        # Verify Mixed inbound port
        mixed_in = [i for i in cfg["inbounds"] if i.get("tag") == "mixed-in"][0]
        self.assertEqual(mixed_in["port"], 10808)

        # Verify Fastly custom IP redirect
        fastly_ob = [o for o in cfg["outbounds"] if o.get("tag") == "tls-repack-fastly"][0]
        self.assertEqual(fastly_ob.get("settings", {}).get("redirect"), "151.101.65.140:443")

        # Verify WARP outbound exists
        warp_ob = [o for o in cfg["outbounds"] if o.get("tag") == "warp-out"]
        self.assertEqual(len(warp_ob), 1)

    def test_config_builder_serverless(self):
        settings = {"mode": "serverless_a", "local_port": 10808}
        cfg = build_xray_config(settings)
        tags = [o.get("tag") for o in cfg["outbounds"]]
        self.assertIn("tcp-fragment-tls", tags)
        self.assertIn("tcp-fragment", tags)
        # MITM tunnels should NOT be in inbounds for pure serverless
        inbound_tags = [i.get("tag") for i in cfg["inbounds"]]
        self.assertNotIn("tls-decrypt-h11", inbound_tags)

    def test_scanner_tcp_ping(self):
        # Test localhost or known DNS (non-blocking / fast timeout)
        ok, lat, msg = test_tcp_ping("1.1.1.1", port=53, timeout=1.0)
        # Should return boolean and either latency or error message without throwing
        self.assertIsInstance(ok, bool)


if __name__ == "__main__":
    unittest.main()
