"""HTTP routes for the promotions domain.

The router is defined here so later tasks can hang endpoints off it, but it is
intentionally left empty and is NOT registered in ``app/api/router.py`` yet —
Task 2 adds the internal-creation endpoints and wires it up.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/promotions", tags=["promotions"])
