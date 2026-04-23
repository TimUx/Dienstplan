"""OR-Tools CP-SAT constraints for TEAM-BASED shift planning.

Implements hard and soft rules. Public API is re-exported for
`from constraints import add_...` compatibility.
"""

from .team_constraints import *  # noqa: F403
from .staffing_constraints import *  # noqa: F403
from .rest_and_sequence_constraints import *  # noqa: F403
from .weekend_and_consecutive_constraints import *  # noqa: F403
from .hours_and_blocks_constraints import *  # noqa: F403
from .fairness_constraints import *  # noqa: F403
