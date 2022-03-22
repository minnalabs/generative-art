#!/usr/bin/env python
import factory.factory as factory

if __name__ == '__main__':
    image_factory = factory.Factory()
    
    print("Generating trait sets...")
    image_factory.generate(image_factory.config.get_count())

    print("Writing metadata CSV file...")
    image_factory.write_to_csv()
    
    print("Generating images...")
    image_factory.generate_images()
    print("{} total images generated".format(image_factory.row_count()))
