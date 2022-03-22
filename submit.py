#!/usr/bin/env python

import pandas as pd
import os


def process_remaining_images(edition_name, existing_rt):
    # open directory containing remaining images
    dirpath = os.path.join("output", "edition " + str(edition_name), "images")
    images = [f for f in os.listdir(dirpath) if not f.startswith('.')]
    images = list(map(lambda filename: filename.removesuffix('.png'), images))
    images.sort(key=lambda filename: int(filename))
    
    new_rt = pd.DataFrame([], columns=existing_rt.columns)
    for i in range(len(images)):
        filename = images[i]
        new_rt.loc[i] = existing_rt.iloc[int(filename)]
        os.rename(os.path.join(dirpath, filename+ ".png"), os.path.join(dirpath, str(i) + ".png"))
    
    new_rt = new_rt.drop('filename', axis=1)
    new_rt.insert(0, "filename", new_rt.index.astype(str) + '.png')
    return new_rt

def main():
    print("Which edition would you like to submit?: ")
    edition_name = input()

    print("Starting task...")
    existing_csv = pd.read_csv(os.path.join('output', 'edition ' + str(edition_name), 'metadata.csv'))

    rt = process_remaining_images(edition_name, existing_csv)
    
    print("Saving metadata...")
    rt.to_csv(os.path.join('output', 'edition ' + str(edition_name), 'metadata.csv'), index=False)

    print("Task complete!")


main()