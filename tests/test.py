import unittest, math
from pathlib import Path
from crumbs import sequence, bpp, sample, get_simulations_rowids
from osgeo import gdal

class TestSequence(unittest.TestCase):
    def SetUp(self):
        pass

    def test_new(self):
        s = sequence.Sequence(">HEADER","--ACGT")
        self.assertEqual(s.header,"HEADER")
        self.assertEqual(s.sequence,"--ACGT")

    def test_parse(self):
        generator = sequence.fasta_parse("tests/data/sequences.fasta")
        sequences = list(generator)
        self.assertEqual(sequences[0].header, "QWER1")
        self.assertEqual(sequences[0].sequence, "GGCAGATTCCCCCTA")
        self.assertEqual(sequences[1].header, "AZER2")
        self.assertEqual(sequences[1].sequence, "---CTGCACTCACCG")

class TestBPP(unittest.TestCase):
    def SetUp(self):
        pass

    def test_nb_species_posterior_probabilities(self):
        string = Path('tests/data/bpp_output.txt').read_text()
        posterior = bpp.nb_species_posterior_probabilities(string)
        assert math.isclose(posterior[1], 0.0)
        assert math.isclose(posterior[2], 0.985)

class TestTiff(unittest.TestCase):
    def SetUp(self):
        pass

    def test_rasterIO(self):
        # Open the file:
        raster = gdal.Open(r'tests/data/suitability.tif')
        # Check type of the variable 'raster'
        type(raster)
        # Projection
        raster.GetProjection()
        # Dimensions
        self.assertEqual(raster.RasterXSize, 240)
        self.assertEqual(raster.RasterYSize, 168)
        # Number of bands
        self.assertEqual(raster.RasterCount, 1)
        # Read the raster band as separate variable
        band = raster.GetRasterBand(1)
        # Compute statistics if needed
        if band.GetMinimum() is None or band.GetMaximum()is None:
            band.ComputeStatistics(0)
        # Fetch metadata for the band
        band.GetMetadata()
        # Print only selected metadata:
        self.assertEqual(band.GetNoDataValue(), -3.4e+38)
        self.assertEqual(band.GetMinimum(), 0.15809911489487)
        self.assertEqual(band.GetMaximum(), 0.78696364164352)

    def test_sample_latlon(self):
        latlon = sample.uniform_latlon("tests/data/suitability.tif")

class TestGetSimulation(unittest.TestCase):
    def SetUp(self):
        pass

    def test_database_IDS(self):
        # Open the file:
        print(get_simulations_rowids("tests/data/out.db", "quetzal_EGG_1", failed=False))
        print(get_simulations_rowids("tests/data/out.db", "quetzal_EGG_1", failed=True))


if __name__=="__main__":
    unittest.main()
