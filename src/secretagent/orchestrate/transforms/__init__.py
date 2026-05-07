"""Pipeline transforms: register all built-in transforms.

Importing this package registers all transform classes.
"""

from secretagent.orchestrate.improve import register_transform
from secretagent.orchestrate.transforms.prune import PruneTransform
from secretagent.orchestrate.transforms.downgrade import DowngradeTransform
from secretagent.orchestrate.transforms.induce import InduceTransform
from secretagent.orchestrate.transforms.expand import ExpandTransform
from secretagent.orchestrate.transforms.repair import RepairTransform
from secretagent.orchestrate.transforms.restructure import RestructureTransform
from secretagent.orchestrate.transforms.evolve import EvolveTransform

register_transform('prune', PruneTransform())
register_transform('downgrade', DowngradeTransform())
register_transform('induce', InduceTransform())
register_transform('expand', ExpandTransform())
register_transform('repair', RepairTransform())
register_transform('restructure', RestructureTransform())
register_transform('evolve', EvolveTransform())
