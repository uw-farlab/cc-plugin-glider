from __future__ import (absolute_import, division, print_function)

import unittest
from cc_plugin_glider.tests.resources import STATIC_FILES
from netCDF4 import Dataset

from compliance_checker.tests.helpers import MockTimeSeries
from ..glider_dac import GliderCheck
import requests_mock
from six.moves.urllib.parse import urljoin

try:
    basestring
except NameError:
    basestring = str


class TestGliderCheck(unittest.TestCase):
    # @see
    # http://www.saltycrane.com/blog/2012/07/how-prevent-nose-unittest-using-docstring-when-verbosity-2/
    def shortDescription(self):
        return None

    # Override __str__ and __repr__ behavior to show a copy-pastable
    # nosetest name for ion tests.
    #  ion.module:TestClassName.test_function_name
    def __repr__(self):
        name = self.id()
        name = name.split('.')
        if name[0] not in ["ion", "pyon"]:
            return "%s (%s)" % (name[-1], '.'.join(name[:-1]))
        else:
            return "%s ( %s )" % (name[-1], '.'.join(name[:-2]) + ":" + '.'.join(name[-2:]))  # noqa
    __str__ = __repr__

    def get_dataset(self, nc_dataset):
        '''
        Return a pairwise object for the dataset
        '''
        if isinstance(nc_dataset, basestring):
            nc_dataset = Dataset(nc_dataset, 'r')
            self.addCleanup(nc_dataset.close)
        return nc_dataset

    def setUp(self):
        self.check = GliderCheck()

    def test_location(self):
        '''
        Checks that a file with the proper lat and lon do work
        '''
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_locations(dataset)
        self.assertTrue(result.value)

    def test_location_fail(self):
        '''
        Ensures the checks fail for location
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_location'])
        result = self.check.check_locations(dataset)
        self.assertEqual(result.value, (0, 1))

    def test_ctd_fail(self):
        '''
        Ensures the ctd checks fail for temperature
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_qc'])
        result = self.check.check_ctd_variables(dataset)
        self.assertEqual(result.value, (55, 56))

    def test_ctd_vars(self):
        '''
        Ensures the ctd checks for the correct file
        '''
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_ctd_variables(dataset)
        self.assertEqual(result.value, (56, 56))

    def test_global_fail(self):
        '''
        Tests that the global checks fail where appropriate
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_qc'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (41, 64))

    def test_global(self):
        '''
        Tests that the global checks work
        '''
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (64, 64))

    def test_metadata(self):
        '''
        Tests that empty attributes fail
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_metadata'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (40, 64))

    def test_standard_names(self):
        '''
        Tests that the standard names succeed/fail
        '''

        dataset = self.get_dataset(STATIC_FILES['bad_metadata'])
        result = self.check.check_standard_names(dataset)
        self.assertEqual(result.value, (0, 1))

        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_standard_names(dataset)
        self.assertEqual(result.value, (1, 1))

    def test_valid_lon(self):
        dataset = self.get_dataset(STATIC_FILES['bad_metadata'])
        result = self.check.check_valid_lon(dataset)
        assert result.value == (0, 1)

        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_valid_lon(dataset)
        assert result.value == (1, 1)

    def test_ioos_ra(self):
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_ioos_ra(dataset)
        assert result.value == (0, 1)

        dataset = self.get_dataset(STATIC_FILES['glider_std3'])
        result = self.check.check_ioos_ra(dataset)
        assert result.value == (1, 1)

    def test_valid_min_dtype(self):
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_valid_min_dtype(dataset)
        assert result.value == (30, 32)

        dataset = self.get_dataset(STATIC_FILES['glider_std3'])
        result = self.check.check_valid_min_dtype(dataset)
        assert result.value == (58, 58)

    def test_valid_max_dtype(self):
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_valid_max_dtype(dataset)
        assert result.value == (30, 32)

        dataset = self.get_dataset(STATIC_FILES['glider_std3'])
        result = self.check.check_valid_max_dtype(dataset)
        assert result.value == (58, 58)

    def test_qc_variables(self):
        dataset = self.get_dataset(STATIC_FILES['glider_std'])
        result = self.check.check_qc_variables(dataset)
        assert result.value == (96, 96)

        dataset = self.get_dataset(STATIC_FILES['glider_std3'])
        result = self.check.check_qc_variables(dataset)
        assert result.value == (96, 96)

        dataset = self.get_dataset(STATIC_FILES['bad_qc'])
        result = self.check.check_qc_variables(dataset)
        assert result.value == (86, 90)
        assert sorted(result.msgs) == [
            'variable depth_qc must have a flag_meanings attribute',
            'variable depth_qc must have a flag_values attribute',
            'variable pressure_qc must have a long_name attribute',
            'variable pressure_qc must have a standard_name attribute'
        ]

        dataset = self.get_dataset(STATIC_FILES['no_qc'])
        result = self.check.check_qc_variables(dataset)
        assert result is None

    def test_time_series_variables(self):
        dataset = self.get_dataset(STATIC_FILES['bad_qc'])
        result = self.check.check_time_series_variables(dataset)
        assert result.value == (7, 8)
        assert sorted(result.msgs) == [
            'Invalid ancillary_variables attribute for time, notavariable is not a variable'
        ]

        dataset = self.get_dataset(STATIC_FILES['no_qc'])
        result = self.check.check_time_series_variables(dataset)
        assert result.value == (7, 7)

    def test_seanames(self):
        '''
        Tests that sea names error message appears
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_metadata'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (40, 64))
        self.assertIn(('sea_name attribute should be from the NODC sea names list:'
                       '   is not a valid sea name'), result.msgs)

    def test_platform_type(self):
        '''
        Tests that platform_type check is applied
        '''
        dataset = self.get_dataset(STATIC_FILES['bad_metadata'])
        result = self.check.check_global_attributes(dataset)
        self.assertIn(('platform_type Slocum is not one of the NCEI accepted platforms for archiving: {}'
            ).format(",".join(self.check.acceptable_platform_types)), result.msgs)

    def test_ncei_compliance(self):
        """Tests that the NCEI compliance suite works"""


        ncei_base_table_url = 'https://gliders.ioos.us/ncei_authority_tables/'
        # this is only a small subset
        institutions = """MARACOOS
University of Delaware
Woods Hole Oceanographic Institution"""

        projects = """MARACOOS"""

        instrument_makes = """Seabird GCTD
Sea-Bird 41CP
Sea-Bird GCTD
Seabird GPCTD"""
        mock_nc_file = MockTimeSeries()
        mock_nc_file.project = 'MARACOOS'
        mock_nc_file.institution = 'MARACOOS'
        instrument_var = mock_nc_file.createVariable('instrument', 'i', ())
        instrument_var.make_model = 'Sea-Bird GCTD'
        mock_nc_file.variables['depth'].instrument = 'instrument'

        with requests_mock.Mocker() as mock:
            mock.get(urljoin(ncei_base_table_url, 'institutions.txt'),
                     text=institutions)
            mock.get(urljoin(ncei_base_table_url, 'projects.txt'),
                     text=projects)
            mock.get(urljoin(ncei_base_table_url, 'instruments.txt'),
                     text=instrument_makes)
            result = self.check.check_ncei_tables(mock_nc_file)
            # everything should pass here
            self.assertEqual(result.value[0], result.value[1])
            # now change to values that should fail
            mock_nc_file.project = 'N/A'
            mock_nc_file.institution = 'N/A'
            # set instrument_var make_model to something not contained in the
            # list
            instrument_var.make_model = 'Unknown'
            # create a dummy variable which points to an instrument that doesn't
            # exist
            dummy_var = mock_nc_file.createVariable('dummy', 'i', ())
            dummy_var.instrument = 'nonexistent_var_name'
            result_fail = self.check.check_ncei_tables(mock_nc_file)
            expected_msg_set = {
                "Global attribute project value 'N/A' not contained in https://gliders.ioos.us/ncei_authority_tables/projects.txt",
                "Global attribute institution value 'N/A' not contained in https://gliders.ioos.us/ncei_authority_tables/institutions.txt",
                "Instrument make/model 'Unknown' for variable instrument not contained in https://gliders.ioos.us/ncei_authority_tables/instruments.txt",
                "Instrument make/model 'Unknown' for variable instrument not contained in https://gliders.ioos.us/ncei_authority_tables/instruments.txt",
                "Referenced instrument variable nonexistent_var_name does not exist"
            }
            self.assertSetEqual(expected_msg_set, set(result_fail.msgs))
