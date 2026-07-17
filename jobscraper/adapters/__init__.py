from .greenhouse import GreenhouseAdapter
from .linkedin import LinkedInAdapter
from .generic import GenericAdapter

ADAPTERS = {
    "greenhouse": GreenhouseAdapter(),
    "linkedin": LinkedInAdapter(),
    "generic": GenericAdapter(),
}
