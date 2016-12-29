import os

from django.test import TestCase
import mock

from osgeo_importer.handlers.mapproxy.publish_handler import MapProxyGPKGTilePublishHandler
import osgeo_importer.handlers.mapproxy.publish_handler
from osgeo_importer.tests.test_settings import _TEST_FILES_DIR
from unittest.case import skipUnless
from osgeo_importer.models import MapProxyCacheConfig


class TestMapProxyGPKGTilePublishHandler(TestCase):
    adequate_mapproxy_version = False
    try:
        from mapproxy.version import version
        maj_v, min_v = version.split('.')[:2]
        if int(maj_v) == 1 and int(min_v) >= 10:
            adequate_mapproxy_version = True
        else:
            adequate_mapproxy_version = False
    except ImportError:
        adequate_mapproxy_version = False

    @skipUnless(adequate_mapproxy_version, 'Need mapproxy 1.10 or later to test this')
    def test_handle_non_gpkg(self):
        # Should do nothing but log an info-level message.
        with mock.patch.object(osgeo_importer.handlers.mapproxy.publish_handler, 'logger') as logger:
            layer_name = 'not_really_a_layer'
            layer_config = {'driver': 'anything_but_gpkg'}
            importer = None
            mpph = MapProxyGPKGTilePublishHandler(importer)
            mpph.handle(layer_name, layer_config)
            self.assertEqual(logger.info.call_count, 1)

    @skipUnless(adequate_mapproxy_version, 'Need mapproxy 1.10 or later to test this')
    def test_handle_gpkg(self):
        filenames = ['sde-NE2_HR_LC_SR_W_DR.gpkg']
        testing_config_dir = '/tmp'
        testing_config_filename = 'geonode.yaml'

        # Check that each of these files results in the two expected changes:
        #  - A MapProxyCacheConfig model instance pointing to the copy is created
        #  - The mapproxy geopackage cache config file is updated.
        for filename in filenames:
            filepath = os.path.join(_TEST_FILES_DIR, filename)
            layer_name = 'notareallayer'
            layer_type = 'tile'  # This handler ignores layers except tile layers from gpkg files.
            layer_config = {
                'layer_name': layer_name, 'path': filepath, 'driver': 'gpkg', 'layer_type': layer_type, 'index': 0
            }
            importer = None
            mpph = MapProxyGPKGTilePublishHandler(importer)

            # Call handle() with directories tweaked for testing.
            test_settings = {
                'MAPPROXY_CONFIG_DIR': testing_config_dir,
                'MAPPROXY_CONFIG_FILENAME': testing_config_filename,
            }
            with self.settings(**test_settings):
                mpph.handle(layer_name, layer_config)

            # --- An instance of MapProxyCacheConfig should have been created
            self.assertEqual(MapProxyCacheConfig.objects.count(), 1)
            mpcc = MapProxyCacheConfig.objects.first()
            self.assertEqual(mpcc.gpkg_filepath, filepath)
            mpcc.delete()

            # --- A mapproxy yaml config with name matching testing_config_filename should be
            #    produced in settings.MAPPROXY_CONFIG_DIR
            conf_path = os.path.join(testing_config_dir, testing_config_filename)
            self.assertTrue(os.path.exists(conf_path))
            os.unlink(conf_path)
