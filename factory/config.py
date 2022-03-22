from pathlib import Path
from jsonschema import validate
import yaml

import factory.constants as constants

schema = """
type: object
properties:
    count:
        type: number
        minimum: 1
    filetype:
        type: string
        enum: 
            - png
            - jpeg
    assets:
        type: object
        properties:
            path:
                type: string
            layers:
                type: array
                items:
                    type: object
                    properties:
                        name:
                            type: string
                        required: 
                            type: boolean
                        rarity_weights:
                            type: object
                            items:
                                type: object
                                patternProperties:
                                    ^(?!\s*$).+:
                                        type: integer
                    required: 
                        - name
    rules:
        type: array
        items:
            type: object
            properties:
                filter:
                    type: string
                trait_1:
                    type: object
                    properties:
                        name:
                            type: string
                        value:
                            type: string
                trait_2:
                    type: object
                    properties:
                        name:
                            type: string
                        value:
                            type: string
"""

class Config:
    def __init__(self, config_path):
        cfg_file = Path(config_path)
        if not cfg_file.exists() or not cfg_file.is_file():
            raise RuntimeError("config file not found at {}".format(cfg_file.resolve()))

        with open(cfg_file.resolve(), 'r') as f:
            raw_cfg = yaml.safe_load(f)
            validate(raw_cfg, yaml.safe_load(schema))

            self.processed_cfg = {constants.ASSETS_KEY: {constants.ASSETS_PATH_KEY: '', constants.LAYERS_KEY: []}}

            self.processed_cfg[constants.COLLECTION_NAME_KEY] = input("What is the name of this collection? Your images will be generated in your collection folder in the ‘outputs’ folder.\n")

            if constants.COLLECTION_COUNT_KEY not in raw_cfg:
                self.processed_cfg[constants.COLLECTION_COUNT_KEY] = input("How many images would you like to generate?\n")
            else:
                self.processed_cfg[constants.COLLECTION_COUNT_KEY] = raw_cfg[constants.COLLECTION_COUNT_KEY]

            if constants.COLLECTION_FILETYPE_KEY not in raw_cfg:
                self.processed_cfg[constants.COLLECTION_FILETYPE_KEY] = input("What is your collection's asset filetype?\n")
            else:
                self.processed_cfg[constants.COLLECTION_FILETYPE_KEY] = raw_cfg[constants.COLLECTION_FILETYPE_KEY]

            if constants.ASSETS_KEY not in raw_cfg:
                raise RuntimeError("no assets specified")

            if constants.ASSETS_PATH_KEY not in raw_cfg[constants.ASSETS_KEY]:
                self.processed_cfg[constants.ASSETS_KEY][constants.ASSETS_PATH_KEY] = input("What is the path of your assets folder?\n")
            else:
                self.processed_cfg[constants.ASSETS_KEY][constants.ASSETS_PATH_KEY] = raw_cfg[constants.ASSETS_KEY][constants.ASSETS_PATH_KEY]

            if constants.LAYERS_KEY not in raw_cfg[constants.ASSETS_KEY]:
                raise RuntimeError("no layers specified")

            for index, layer in enumerate(raw_cfg[constants.ASSETS_KEY][constants.LAYERS_KEY]):
                if constants.LAYER_NAME_KEY not in layer:
                    raise RuntimeError("no layer name specified for layer at index {}".format(index))
                
                
                assets_path: Path = self.get_assets_path() / layer[constants.LAYER_NAME_KEY]
                if not assets_path.exists():
                    raise RuntimeError("{} not found in 'assets' folder. Please double check that the layer directory name in the config matches the folder name in the 'assets' folder exactly".format(layer[constants.LAYER_NAME_KEY]))
                if not assets_path.is_dir():
                    raise RuntimeError("File found at the specified layer folder: {}. Please provide a valid folder with assets".format(layer[constants.LAYER_NAME_KEY]))
                                        
                if constants.LAYER_REQUIRED_KEY not in layer:
                    layer[constants.LAYER_REQUIRED_KEY] = False
                
                valid_traits = self.get_live_traits(layer[constants.LAYER_NAME_KEY])
                # If required is false, then the user can skip trait generation for this layer at some specified probability
                if layer[constants.LAYER_REQUIRED_KEY] == False:
                    valid_traits.append("None")
                if constants.LAYER_WEIGHTS_KEY not in layer:
                    weights = {}
                    weight = 1 / len(valid_traits)
                    for trait in valid_traits:
                        weights[trait] = weight
                    layer[constants.LAYER_WEIGHTS_KEY] = weights
                elif isinstance(layer[constants.LAYER_WEIGHTS_KEY], dict):
                    if sum(layer[constants.LAYER_WEIGHTS_KEY].values()) != 100:
                        raise ValueError("rarity_weights do not sum to 100 for layer {}".format(layer['name']))
                    for image_name in layer[constants.LAYER_WEIGHTS_KEY]:
                        if image_name not in valid_traits:
                            raise ValueError("invalid image name: {} provided for rarity_weights in layer: {}".format(image_name, layer['name']))
                else:
                    raise ValueError("invalid rarity_weights type: {} provided".format(type(layer[constants.LAYER_WEIGHTS_KEY])))
                self.processed_cfg[constants.ASSETS_KEY][constants.LAYERS_KEY].append(layer)
            
            self.rules = {}
            
            if constants.RULES_KEY in raw_cfg:
                for rule in raw_cfg[constants.RULES_KEY]:
                    filter_type = rule[constants.RULES_FILTER_KEY]
                    if filter_type != constants.RULES_EQUALS_KEY and filter_type != constants.RULES_NOT_EQUALS_KEY:
                        raise RuntimeError("invalid filter type {}".format(filter_type))
                    
                    if rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME] not in self.rules:
                        self.rules[rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME]] = []
                    self.rules[rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME]].append(rule)

                    if rule[constants.TRAIT_2_KEY][constants.RULE_TRAIT_NAME] not in self.rules:
                        self.rules[rule[constants.TRAIT_2_KEY][constants.RULE_TRAIT_NAME]] = []
                    self.rules[rule[constants.TRAIT_2_KEY][constants.RULE_TRAIT_NAME]].append(rule)


    def get_live_traits(self, dir_name):
        trait_folder: Path = self.get_assets_path() / dir_name
        if not trait_folder.exists() or not trait_folder.is_dir():
            raise RuntimeError("no valid assets folder found at path: {}".format(trait_folder.resolve()))
        all_trait_files = trait_folder.glob('**/*')
        return [x.stem for x in all_trait_files if x.is_file() and not x.stem.startswith(".")]

    def get_filetype(self):
        return self.processed_cfg[constants.COLLECTION_FILETYPE_KEY]

    def get_layers(self):
        return self.processed_cfg[constants.ASSETS_KEY][constants.LAYERS_KEY]

    def get_assets_path(self) -> Path:
        return Path(self.processed_cfg[constants.ASSETS_KEY][constants.ASSETS_PATH_KEY])
    
    def get_collection_name(self):
        return self.processed_cfg[constants.COLLECTION_NAME_KEY]

    def get_directory_name(self, trait_name):
        for layer in self.get_layers():
            if layer[constants.LAYER_NAME_KEY] == trait_name:
                return layer[constants.LAYER_NAME_KEY]
        raise RuntimeError("finding directory for trait: {}".format(trait_name))
    
    def get_count(self):
        return self.processed_cfg[constants.COLLECTION_COUNT_KEY]
    
    def get_index(self, dir_name):
        for index, layer in enumerate(self.processed_cfg[constants.ASSETS_KEY][constants.LAYERS_KEY]):
            if layer[constants.LAYER_NAME_KEY] == dir_name:
                return index

    def has_rule(self, trait_name):
        if trait_name  in self.rules:
            for rule in self.rules[trait_name]:
                if trait_name == rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME]:
                    this_trait = constants.TRAIT_1_KEY
                    other_trait = constants.TRAIT_2_KEY
                else:
                    this_trait = constants.TRAIT_2_KEY
                    other_trait = constants.TRAIT_1_KEY
                if self.get_index(rule[other_trait][constants.RULE_TRAIT_NAME]) < self.get_index(rule[this_trait][constants.RULE_TRAIT_NAME]):
                    return True
        return False

    # return trait_name, trait_value
    def has_equals_rule(self, trait_name, trait_value):
        if trait_name in self.rules:
            for rule in self.rules[trait_name]:
                if rule[constants.RULES_FILTER_KEY] == constants.RULES_EQUALS_KEY:
                    if trait_name == rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME]:
                        this_trait = constants.TRAIT_1_KEY
                        other_trait = constants.TRAIT_2_KEY
                    else:
                        this_trait = constants.TRAIT_2_KEY
                        other_trait = constants.TRAIT_1_KEY
                    
                    if rule[this_trait][constants.RULES_VALUE_KEY] == trait_value:
                        yield rule[other_trait][constants.RULE_TRAIT_NAME], rule[other_trait][constants.RULES_VALUE_KEY]

                

    # trait_name, trait_value
    def get_valid_trait(self, trait_name, current_trait_set):
        all_traits = self.get_live_traits(trait_name)
        for rule in self.rules[trait_name]:
            if trait_name == rule[constants.TRAIT_1_KEY][constants.RULE_TRAIT_NAME]:
                this_trait = constants.TRAIT_1_KEY
                other_trait = constants.TRAIT_2_KEY
            else:
                this_trait = constants.TRAIT_2_KEY
                other_trait = constants.TRAIT_1_KEY
            # check if other rule 'lower' in stack
            if self.get_index(rule[other_trait][constants.RULE_TRAIT_NAME]) < self.get_index(rule[this_trait][constants.RULE_TRAIT_NAME]):
                if rule[constants.RULES_FILTER_KEY] == constants.RULES_EQUALS_KEY:
                    if rule[other_trait][constants.RULES_VALUE_KEY] == current_trait_set[rule[other_trait][constants.RULE_TRAIT_NAME]][0]:
                        return [rule[this_trait][constants.RULES_VALUE_KEY]]
                if rule[constants.RULES_FILTER_KEY] == constants.RULES_NOT_EQUALS_KEY:
                        if isinstance(rule[other_trait][constants.RULES_VALUE_KEY], list):
                            if current_trait_set[other_trait][0] in rule[other_trait][constants.RULES_VALUE_KEY]:
                                all_traits.remove(rule[this_trait][constants.RULES_VALUE_KEY])
                        if isinstance(rule[other_trait][constants.RULES_VALUE_KEY], str):
                            if current_trait_set[rule[other_trait][constants.RULE_TRAIT_NAME]][0] == rule[other_trait][constants.RULES_VALUE_KEY]:
                                all_traits.remove(rule[this_trait][constants.RULES_VALUE_KEY])
        return all_traits