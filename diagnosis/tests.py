from unittest import TestCase

from logger import get_logger

logger = get_logger(__name__, log_level=("TEST", "LOGLEVEL"))


class AppAnalyzerTest(TestCase):
    def testAnalyzerUsingRawMetrics(self):
        """ Assert that the analyzer receives raw data for the app
        metric and input variables from MetricsConsumer. """
        pass

    def testAnalyzerUsingDerivedMetrics(self):
        """ Same as above, but for derived metrics. """
        pass

    def testAnalyzerUsingAreaThresholdType(self):
        """ Assert that the derived metrics are computed based on
        the area calculation when fed the corresponding config value.
        """
        pass

    def testAnalyzerUsingFrequencyThresholdType(self):
        """ Same as above but for frequency calculation type. """
        pass

    def testAllMetricsFiltered(self):
        """ Assert that AppAnalyzer logs the appropriate information
        and continues without throwing an error. """
        pass

    def testWriteDiagnosisResults(self):
        """ Assert that AppAnalyzer can write diagnosis results
        to influx. """
        pass

    def testDiagnosisResultQuality(self):
        """ Assert that all diagnosis result values are not NaN's.
        (Could add more tests for diagnosis quality)"""
        pass


class MetricsConsumerTest(TestCase):
    def testGetRawMetrics(self):
        """ Test that MetricsConsumer gets raw data. """
        pass

    def testGetDerivedMetrics(self):
        """ Same as above for derived data. """
        pass

    def testWriteDerivedMetrics(self):
        """ Assert that MetricsConsumer can write derived metrics
        to influx. """
        pass


# class DiagnosisGeneratorTest(TestCase):
# (many DiagnosisGenerator functions will be covered by AppAnalyzer.)    

class FeaturesSelectorTest(TestCase):
    def testDataPointGroupingbyTime(self):
        """ Assert that the result of
        features_selector.match_timestamps() is Dataframe with
        data bucketed by the analyzer sample interval. """
        pass

    def testFilterFeaturesCorrelation(self):
        """ Assert that if features are above the threshold for
        filtering that they are filtered (correlation). """
        pass

    def testFilterFeaturesAverage(self):
        """ Assert that if features are above the threshold for
        filtering that they are filtered (average). """
        pass

