"""Check output ownership in compositions and at module boundaries."""
from pathlib import Path
import tempfile
import unittest

from test_contracts import COMPONENTS, Harness, PARSED, ROOT, interpolate


def assert_unique_prefixes(test, body):
    """Inspect component inputs in our fixtures; GitLab owns include/rule evaluation."""
    owners = {}
    for entry in body.get('include', []):
        if 'component' in entry:
            component = entry['component'].rsplit('/', 1)[-1].split('@', 1)[0]
        elif entry.get('local', '').startswith(('/templates/', '/modules/todo/')):
            component = Path(entry['local']).stem
        else:
            continue
        job_name, job = next((name, job) for name, job in
                            interpolate(COMPONENTS[component], entry.get('inputs')).items()
                            if name != 'include')
        variables = {**job['variables'], **body.get(job_name, {}).get('variables', {})}
        prefix = variables['MODULE_OUTPUT_PREFIX']
        test.assertRegex(prefix, r'^[A-Z][A-Z0-9_]*$')
        test.assertNotIn(prefix, owners,
                         f'Output prefix {prefix} is shared by {owners.get(prefix)} and {job_name}')
        owners[prefix] = job_name
    test.assertTrue(owners)


class OutputNameTests(unittest.TestCase):
    def test_compositions_and_consumer_examples_have_unique_prefixes(self):
        for path in [*ROOT.glob('examples/samples/*.yml'), *ROOT.glob('examples/modules/*.yml'),
                     ROOT / 'examples/full-pipeline/profile.yml']:
            with self.subTest(path=path):
                assert_unique_prefixes(self, interpolate(PARSED[str(path)]))

    def test_prefix_check_rejects_repeated_instances_with_default_or_overridden_prefix(self):
        body = {'include': [
            {'local': '/templates/maven-build.yml', 'inputs': {'job-name': 'api'}},
            {'local': '/templates/maven-build.yml', 'inputs': {'job-name': 'worker'}}]}
        with self.assertRaisesRegex(AssertionError, 'shared by api and worker'):
            assert_unique_prefixes(self, body)
        body['include'][1]['inputs']['output-prefix'] = 'WORKER'
        assert_unique_prefixes(self, body)
        body['worker'] = {'variables': {'MODULE_OUTPUT_PREFIX': 'MAVEN_BUILD'}}
        with self.assertRaises(AssertionError):
            assert_unique_prefixes(self, body)

    def test_imported_prefix_cannot_be_reused_before_the_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory), env={'MAVEN_BUILD_STATUS': 'passed'})
            result = h.run()
            self.assertNotEqual(0, result.returncode)
            self.assertIn('Output prefix MAVEN_BUILD is already in use', result.stderr)
            self.assertEqual([], h.events())
            self.assertFalse(h.output_file.exists())

    def test_conflicting_upstream_producers_are_rejected_even_when_values_match(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory), env={'IMAGE_STATUS': 'passed'})
            for producer in ('api', 'worker'):
                h.write(f'.ci-output/{producer}/outputs.env', 'IMAGE_STATUS=passed\n')
            result = h.run()
            self.assertNotEqual(0, result.returncode)
            self.assertIn('Duplicate upstream output: IMAGE_STATUS', result.stderr)
            self.assertEqual([], h.events())

    def test_shadowed_upstream_output_fails_without_exposing_values(self):
        for actual in (None, 'confidential-override'):
            with self.subTest(actual=actual), tempfile.TemporaryDirectory() as directory:
                h = Harness(Path(directory), env={} if actual is None else {'UPSTREAM_URL': actual})
                h.write('.ci-output/producer/outputs.env', 'UPSTREAM_URL=expected-value\n')
                result = h.run()
                self.assertNotEqual(0, result.returncode)
                self.assertIn('UPSTREAM_URL', result.stderr)
                self.assertNotIn('confidential-override', result.stderr)
                self.assertNotIn('expected-value', result.stderr)
                self.assertEqual([], h.events())

    def test_correct_upstream_outputs_allow_the_consumer_to_run(self):
        with tempfile.TemporaryDirectory() as directory:
            h = Harness(Path(directory), env={'UPSTREAM_URL': 'https://example.invalid/?a=b'})
            h.write('.ci-output/producer/outputs.env', 'UPSTREAM_URL=https://example.invalid/?a=b\n')
            result = h.run()
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('passed', h.outputs()['MAVEN_BUILD_STATUS'])

    def test_existing_environment_names_cannot_be_published_as_outputs(self):
        for key in ('MAVEN_BUILD_ARTIFACT_ROOT', 'MAVEN_BUILD_CUSTOM_LABEL'):
            for value in ('', '.', 'override'):
                with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as directory:
                    h = Harness(Path(directory), env={key: value})
                    h.hook('post', 'echo MAVEN_BUILD_CUSTOM_LABEL=candidate >> "$CI_MODULE_EXTRA_OUTPUTS"')
                    result = h.run()
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn('Output name already exists in the environment: ' + key, result.stderr)
                    self.assertFalse(h.output_file.exists())



if __name__ == '__main__':
    unittest.main()
