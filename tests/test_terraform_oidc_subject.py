import importlib.util
import unittest
spec=importlib.util.spec_from_file_location('subject','scripts/check-terraform-oidc-subject.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def accepted(condition,claims):
    import re
    return all(claims.get(k)==v for k,v in re.findall(r"assertion\.([a-z_]+)=='([^']*)'",condition))


class TerraformOidcSubject(unittest.TestCase):
    def setUp(self):
        self.settings=dict(use_default=True,use_immutable_subject=True,sub_claim_prefix=m.PREFIX)
        self.before=' && '.join(m.TERMS)
        self.claims=dict(repository=m.REPO,repository_id='1427106572',repository_owner_id='194725286',
            ref='refs/heads/main',workflow_ref=m.REPO+'/.github/workflows/terraform-gke.yml@refs/heads/main',sub=m.NEW_SUB)

    def test_observed_immutable_subject_explains_rejection_and_fix(self):
        self.assertFalse(accepted(self.before,self.claims))
        self.assertTrue(accepted(m.propose(self.before,self.settings),self.claims))

    def test_other_trust_boundaries_are_preserved(self):
        after=m.propose(self.before,self.settings)
        self.assertEqual(self.before.split(' && ')[:-1],after.split(' && ')[:-1])
        for key,value in [('repository','other/repo'),('repository_id','1'),('repository_owner_id','2'),
                          ('ref','refs/heads/feature'),('workflow_ref','other.yml'),
                          ('sub',m.PREFIX+':environment:other'),('sub',m.OLD_SUB)]:
            with self.subTest(key=key,value=value):self.assertFalse(accepted(after,dict(self.claims,**{key:value})))

    def test_unknown_settings_are_not_silently_accepted(self):
        for key,value in [('use_immutable_subject',False),('use_default',False),('sub_claim_prefix','other')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                m.propose(self.before,dict(self.settings,**{key:value}))

    def test_modified_or_weakened_provider_requires_new_review(self):
        with self.assertRaises(ValueError):m.propose(' && '.join(m.TERMS[1:]),self.settings)
