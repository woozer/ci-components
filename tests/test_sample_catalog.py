"""Keep the executable catalog complete as modules and examples evolve."""
import unittest
from test_contracts import PARSED, ROOT


class SampleCatalogTests(unittest.TestCase):
    def test_every_active_example_has_a_selectable_executable_child(self):
        launcher = PARSED[str(ROOT / 'tests/samples/launcher.yml')][1]
        options = PARSED[str(ROOT / 'tests/samples/options.yml')][0]['spec']['inputs']['sample']['options']
        examples = {'module-' + path.stem: path for path in (ROOT / 'examples/modules').glob('*.yml')}
        examples.update({path.stem: path for path in (ROOT / 'examples/samples').glob('*.yml')})
        self.assertEqual({'all', *examples}, set(options))
        self.assertEqual({p.stem for p in (ROOT / 'templates').glob('*.yml')},
                         {p.stem for p in (ROOT / 'examples/modules').glob('*.yml')})
        for selection, example in examples.items():
            with self.subTest(selection=selection):
                job = launcher[selection]
                self.assertEqual('mirror', job['trigger']['strategy'])
                self.assertIn('/' + str(example.relative_to(ROOT)), [item['file'] for item in job['trigger']['include']])
                self.assertIn('"all"', job['rules'][0]['if'])
                self.assertIn('"' + selection + '"', job['rules'][0]['if'])

    def test_protected_examples_and_shared_deployments_are_isolated(self):
        launcher = PARSED[str(ROOT / 'tests/samples/launcher.yml')][1]
        for name in ('sonar', 'release-reserve', 'release-check', 'gitlab-release'):
            condition = launcher['module-' + name]['rules'][0]['if']
            self.assertIn('$CI_COMMIT_REF_PROTECTED == "true"', condition)
            self.assertIn('$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH', condition)
        for name in ('deploy-and-test', 'two-deployables', 'module-helm-deploy'):
            self.assertEqual('samples-deployment', launcher[name]['resource_group'])
        for name in ('release-reserve', 'release-check', 'gitlab-release'):
            self.assertEqual('samples-release', launcher['module-' + name]['resource_group'])

    def test_example_changes_trigger_real_validation(self):
        config = PARSED[str(ROOT / 'tests/samples/component-validation.yml')][1]
        self.assertIn('examples/modules/**/*', config['validate-samples']['rules'][1]['changes'])


if __name__ == '__main__':
    unittest.main()
