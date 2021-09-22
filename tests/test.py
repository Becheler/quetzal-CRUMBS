import unittest, math
from pathlib import Path
from crumbs import sequence, bpp, sample, get_successful_simulations_rowids
from crumbs import get_failed_simulations_rowids, simulate_phylip_sequences, phylip2arlequin
from crumbs import retrieve_parameters

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
        success_rowids = get_successful_simulations_rowids.get_successful_simulations_rowids("tests/data/database_with_newicks.db", "quetzal_EGG_1")
        self.assertEqual(success_rowids, list(range(1,31)))
        print(success_rowids)
        failed_rowids = get_failed_simulations_rowids.get_failed_simulations_rowids("tests/data/database_failed_newicks.db", "quetzal_EGG_1")
        self.assertEqual(failed_rowids, list(range(1,31)))

    def test_simulate_phylip(self):
        rowids = get_successful_simulations_rowids.get_successful_simulations_rowids("tests/data/database_with_newicks.db", "quetzal_EGG_1")
        sequence_size = 100
        scale_tree = 0.000025
        print(row[0])
        simulate_phylip_sequences.simulate_phylip_sequences("tests/data/database_with_newicks.db", "quetzal_EGG_1", rowids[0], sequence_size, scale_tree, "sim_test.phyl", "sim_test_temp")
        print(retrieve_parameters.retrieve_parameters("tests/data/database_with_newicks.db", "quetzal_EGG_1", rowids[0]))
        print(retrieve_parameters.retrieve_parameters("tests/data/database_with_newicks.db", "quetzal_EGG_1", rowids[0]), False)

class TestConvertPhylipToArlequin(unittest.TestCase):
    def SetUp(self):
        pass

    def test_phylip_to_alequin(self):
        output = "test.arlequin"
        phylip2arlequin.phylip2arlequin("tests/data/seq.phyl", "tests/data/imap.txt", output)
        with open('test.arlequin', 'r') as f:
            print(f.read())

if __name__=="__main__":
    unittest.main()
