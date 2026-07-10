"""
Thin entrypoint: adds the project to sys.path then delegates to MarketplaceServer.

This file lives in nemo_gym_lib so NeMo Gym's server-discovery logic can find it.
All real logic lives in project_deal_approach_1/resources_server/app.py.
"""

import sys
import os

# project_deal root, resolved relative to this vendored shim:
#   nemo_gym_lib/resources_servers/marketplace/app.py  →  ../../../  = project_deal/
_PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from resources_server.app import MarketplaceServer  # noqa: E402

if __name__ == "__main__":
    MarketplaceServer.run_webserver()
