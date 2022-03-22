#!/usr/bin/env python

from pathlib import Path
import pandas as pd

from factory.config import Config
from factory.factory import Factory
import factory.constants as constants

class Handler:
    def __init__(self, config_path="./config.yaml"):
        self.config = Config(config_path=config_path)
        metadata_path = self._get_metadata_path()
        if not metadata_path.exists() or not metadata_path.is_file():
            self._handle_missing_collection()
        else:
            self._handle_existing_collection(metadata_path.resolve())
    
    def _handle_missing_collection(self):
        (Path(constants.OUTPUT_DIR_NAME) / self.config.get_collection_name() / constants.METADATA_DIR_NAME).mkdir(parents=True, exist_ok=True)
        (Path(constants.OUTPUT_DIR_NAME) / self.config.get_collection_name() / constants.IMAGES_DIR_NAME).mkdir(parents=True, exist_ok=True)
        print("Copy your {} file into the '{}' folder.".format(constants.METADATA_FILE_NAME, constants.METADATA_DIR_NAME))
        while True:
            value = input("Enter \"next\" to continue.\n")
            metadata_file_path = self._get_metadata_path()
            if value == "next":
                if not metadata_file_path.exists():
                    print("no metadata file found at {}. Please copy the metadata file".format(metadata_file_path.resolve()))   
                    continue
                if metadata_file_path.is_dir():
                    print("{} should be a file, not a directory. Please fix", constants.METADATA_FILE_NAME)
                    continue
                if metadata_file_path.is_file():
                    break
                print("invalid metadata file, please try again")
            print("please enter \"next\"")
        self._handle_existing_collection(metadata_file_path)
    
    def _get_metadata_path(self):
        return Path(constants.OUTPUT_DIR_NAME) / self.config.get_collection_name() / constants.METADATA_DIR_NAME / constants.METADATA_FILE_NAME
    
    def _handle_existing_collection(self, metadata_path):
        df: pd.DataFrame = pd.read_csv(metadata_path, keep_default_na=False)
        df = df.drop(labels='filename', axis=1)
        df = df[df.any(1)]
        df = df.reset_index()
        df = df.drop('index', axis=1)
        for trait_name in df:
            unique_vals = list(df[trait_name].unique())
            unique_vals_filtered_none = filter(lambda trait_val: trait_val != "", unique_vals)
            valid_files = self.config.get_live_traits(self.config.get_directory_name(trait_name))
            for val in unique_vals_filtered_none:
                if val not in valid_files:
                    raise RuntimeError("unable to locate trait (value: {}) for (trait: {})".format(val, trait_name))

        factory: Factory = Factory(metadata=df, config=self.config)
        factory.generate_images()
        factory.generate_stats()
        factory.write_to_csv()

if __name__ == '__main__':
    handler = Handler()

