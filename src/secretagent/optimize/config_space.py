"""Define a space of possible configuration changes.
"""

from itertools import product
from pydantic import BaseModel
from typing import Any
import yaml

from secretagent import config

class ConfigSpace(BaseModel):
    variants: dict[str, list[Any]] = {}
    
    def __iter__(self):
        """Iterates over configuration deltas.

        A configuration delta is a dict D that can be passed to config
        via the context manager "config.configuration(**D)" or via
        config.configure(**D)
        """
        # combine the variant values all possible ways
        for value_choices in product(*self.variants.values()):
            # pair the parameters up with the values
            param_bindings = list(zip(self.variants, value_choices))
            # convert from something like (llm.model, 'gpt5') to a nested
            # dict for the hierarchical parameter, like {'llm':{'model':'gpt5'}}
            bindings_as_dicts = [self._expand_hierarchy(p, v) for p, v in param_bindings]
            # deep-merge the parameter bindings into a single dictionary
            result = {}
            for d in bindings_as_dicts:
                self._deep_merge(result, d)
            yield result

    def _deep_merge(self, base, override):
        """Merge override into base, recursing into nested dicts."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def _expand_hierarchy(self, dotted_param, value):
        """Convert a dotted parameter like 'llm.model' into a nested dict like {'llm': {'model': value}}."""
        if '.' not in dotted_param:
            return {dotted_param: value}
        else:
            first, rest = dotted_param.split('.', 1)
            return {first: self._expand_hierarchy(rest, value)}

    @staticmethod
    def load(yaml_file: str):
        """Load a ConfigSpace from a yaml file."""
        with open(yaml_file, 'r') as fp:
            return ConfigSpace(**yaml.safe_load(fp))

    def save(self, yaml_file: str):
        """Save to a yaml file."""
        with open(yaml_file, 'w') as fp:
            yaml.dump(self.model_dump(), fp, default_flow_style=False)

# smoketest
if __name__ == '__main__':
    cs = ConfigSpace(
        variants={
            'name': ['fred'],
            'llm.model': ['big', 'small'],
            'ptool.extract': [
                {'method':'direct','fn':'extract_fn'} ,
                {'method': 'simulate', 'llm.model': 'huge'}]
        })
    config.configure(spacetest=True)
    for i, cfg in enumerate(cs):
        print(f' config {i+1} '.center(60, '-'))
        print(cfg)
        with config.configuration(**cfg):
            print(config.to_dotlist(config.GLOBAL_CONFIG))
    cs.save('/tmp/foo.yaml')
    print(ConfigSpace.load('/tmp/foo.yaml'))
