"""
Data Agents for SF Open Data (Socrata) acquisition

Each agent is responsible for:
- Querying a specific dataset via SoQL
- Returning structured signals with evidence refs
- Tracking data freshness and gaps
"""

from .business_registry_agent import BusinessRegistryAgent
from .permits_agent import PermitsAgent
from .complaints_311_agent import Complaints311Agent
from .dbi_complaints_agent import DBIComplaintsAgent
from .sfpd_incidents_agent import SFPDIncidentsAgent
from .evictions_agent import EvictionsAgent
from .vacancy_corridor_agent import VacancyCorridorAgent

__all__ = [
    "BusinessRegistryAgent",
    "PermitsAgent",
    "Complaints311Agent",
    "DBIComplaintsAgent",
    "SFPDIncidentsAgent",
    "EvictionsAgent",
    "VacancyCorridorAgent",
]
