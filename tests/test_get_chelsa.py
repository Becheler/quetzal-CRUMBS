# avoid Module not found, see https://gideonbrimleaf.github.io/2021/01/26/relative-imports-python.html
import unittest
import sys
sys.path.append("..")

from src.crumbs import get_chelsa

class TestGetChelsa(unittest.TestCase):

    output_filename = "chelsa-stacked"
    world_file_dir = "chelsa-world"
    cropped_file_dir = "chelsa-cropped"

    def SetUp(self):
        pass

    def test_get_chelsa_with_input_file(self):
        get_chelsa.get_chelsa(inputFile = "data/chelsa_url_test.txt",
                              points = "data/test_points/test_points.shp")

    def test_get_chelsa_with_no_input_file(self):
        get_chelsa.get_chelsa(points = "data/test_points/test_points.shp",
                              variables = ['dem'],
                              timesID = [20])

    def test_get_chelsa_with_time_range(self):
        get_chelsa.get_chelsa(points = "data/test_points/test_points.shp",
                              variables = ['bio01'],
                              timesID = [0, -1])

    def tearDown(self):
        from pathlib import Path
        import glob

        # Remove all chelsa stacked files generated
        for p in Path(".").glob( self.output_filename + "*.*"):
            p.unlink()

        # Remove all chelsa world files generated
        for p in Path(self.world_file_dir).glob("*.tif"):
            p.unlink()
        Path(self.world_file_dir).rmdir()

        # Remove all chelsa cropped files generated
        for p in Path(self.cropped_file_dir).glob("*.tif"):
            p.unlink()
        Path(self.cropped_file_dir).rmdir()

if __name__=="__main__":
    unittest.main()
