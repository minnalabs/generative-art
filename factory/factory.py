#!/usr/bin/env python

from PIL import Image
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import multiprocessing as mp
from tqdm import tqdm
import shutil

import factory.pinata as pinata
import factory.constants as constants
from factory.config import Config

class Factory:
    def __init__(self, config_path="./config.yaml", config=None, metadata=None):
        if config is not None:
            self.config = config
        else:
            self.config = Config(config_path)
        self.metadata = pd.DataFrame(columns=[x[constants.LAYER_NAME_KEY] for x in self.config.get_layers()]) if metadata is None else metadata
        self.pinata_client = pinata.PinataClient()

    def generate(self, count):
        hash_set = set()

        current_count = 0
        with tqdm(total=count) as pbar:
            while current_count < count:
                current_trait_set = pd.DataFrame(columns=list(self.metadata.columns))
                for layer in self.config.get_layers():
                    trait_name = layer[constants.LAYER_NAME_KEY]
                    if self.config.has_rule(trait_name):
                        valid_traits = self.config.get_valid_trait(trait_name, current_trait_set)
                        valid_weights = []
                        for trait_value in valid_traits:
                            valid_weights.append(layer[constants.LAYER_WEIGHTS_KEY][trait_value])
                        valid_weights = list(np.array(valid_weights) / sum(valid_weights) * 100)
                    else:
                        valid_traits, valid_weights = list(layer[constants.LAYER_WEIGHTS_KEY].keys()), list(layer[constants.LAYER_WEIGHTS_KEY].values())
                    
                    trait_value = np.random.default_rng().choice(valid_traits, 1, p=(np.array(valid_weights) / np.sum(valid_weights)).tolist()).tolist()[0]
                    current_trait_set.at[0, trait_name] = trait_value
                    for trait_name_to_update, new_trait_value in self.config.has_equals_rule(trait_name, trait_value):
                        current_trait_set.at[0, trait_name_to_update] = new_trait_value    

                trait_hash = hash(tuple(list(current_trait_set.iloc[0])))
                if trait_hash in hash_set:
                    continue
                hash_set.add(trait_hash)
                current_count += 1
                self.metadata = pd.concat([self.metadata, current_trait_set], ignore_index=True)
                pbar.update(1)
                    
    def write_to_csv(self):
        # Define output path to output/collection_name
        op_path = os.path.join('output', self.config.get_collection_name(), 'metadata')

        # Create output directory if it doesn't exist
        if not os.path.exists(op_path):
            os.makedirs(op_path)
        
        filtered_none = self.metadata.replace("None", "")
        filtered_none.insert(loc=0, column='filename', value=[str(x - 1) + "." + self.config.get_filetype() for x in range(1, len(filtered_none) + 1)])
        filtered_none.to_csv(os.path.join(op_path, "metadata.csv"), index=False)

    def generate_images(self):
        # Create output directory if it doesn't exist

        self.images_path = (Path(constants.OUTPUT_DIR_NAME) / self.config.get_collection_name() / constants.IMAGES_DIR_NAME)
        if self.images_path.exists() or self.images_path.is_file():
            shutil.rmtree(self.images_path)
        os.makedirs(self.images_path)

        df_copy = self.metadata.copy()
        df_copy.replace('', "None", inplace=True)

        assets_path = self.config.get_assets_path()
        for trait in df_copy.columns:
            trait_path = (Path(assets_path) / trait).resolve()
            df_copy.loc[df_copy[trait] != "None", trait] = str(trait_path) + "/" + df_copy[trait] + "." + self.config.get_filetype()
        
        outputs = df_copy.index.map(lambda index: str(self.images_path.resolve()) + "/" + str(index) + "." + self.config.get_filetype())
        df_copy.insert(loc=0, column='file_output', value=outputs)

        with mp.Pool() as pool:
            args = df_copy.values.tolist()
            list(tqdm(pool.imap(save_image, args), total=len(args)))

    def upload(self):
        resp = self.pinata_client.upload_folder(os.path.join(constants.OUTPUT_DIR_NAME, str(self.config.get_collection_name()), constants.IMAGES_DIR_NAME), self.config.get_collection_name())

        images_path = os.path.join(constants.OUTPUT_DIR_NAME, self.config.get_collection_name(), "final")
        if not os.path.exists(images_path):
            os.makedirs(images_path)

        with open(os.path.join(constants.OUTPUT_DIR_NAME, self.config.get_collection_name(), "final", "IPFS CID"), "a+") as f:
            f.write(resp['IpfsHash'])

    def generate_stats(self):
        stats_path = os.path.join(constants.OUTPUT_DIR_NAME, self.config.get_collection_name(), "stats")
        if not os.path.exists(stats_path):
            os.makedirs(stats_path)

        for layer in self.config.get_layers():
            self.metadata[layer[constants.LAYER_NAME_KEY]].value_counts().plot(kind='bar')
            plt.savefig(os.path.join(stats_path, layer[constants.LAYER_NAME_KEY]+".png"), bbox_inches="tight")
    
    def row_count(self):
        return len(self.metadata)

def save_image(args):
    output_path = args[0]

    bg = None
    for arg in args[1:]:
        if arg != "None":
            if bg is None:
                bg = Image.open(arg)
                continue
            img = Image.open(arg)
            bg.paste(img, (0, 0), img)
    bg.save(output_path)